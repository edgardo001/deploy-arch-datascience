# Data Pipeline — El Viaje del Dato (OLTP → Lakehouse → ML/BI)

> Módulo de arquitectura del [README.md](../../README.md). Describe **etapa por etapa** cómo un registro
> transaccional se convierte en un KPI certificado y en una predicción trazable.
> Infraestructura que lo soporta: [docker-setup.md](../infrastructure/docker-setup.md).
> Puente hacia MLOps: [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md).

## 1. Principios de diseño

| Principio | Implementación local |
|---|---|
| Arquitectura Medallion | `bronze` (crudo inmutable) → `silver` (limpio/conformado) → `gold` (modelado para consumo) |
| *ELT* antes que *ETL* | Se carga crudo en MinIO y se transforma con SQL en dbt (motor ClickHouse/DuckDB) |
| Idempotencia | Particiones `dt=YYYY-MM-DD` con *overwrite* controlado por `run_id` |
| Contratos primero | Esquema, granularidad, dueño y tests definidos antes de escribir el modelo |
| Linaje verificable | `manifest.json` de dbt + OpenLineage alimentan el grafo de dependencias |
| Reproducibilidad | Misma imagen, mismo `run_id`, mismo resultado (semillas fijas en ML) |

## 2. Etapas del pipeline

| # | Etapa | Origen | Destino | Herramienta | Granularidad | Partición |
|---|---|---|---|---|---|---|
| 1 | Extracción incremental | PostgreSQL OLTP | Memoria del worker | `psycopg2` / Airflow | Fila | `watermark` (`updated_at`) |
| 2 | Aterrizaje Bronze | Worker | `s3://datalake/bronze` | `pyarrow` + `boto3` | Fila | `dt=YYYY-MM-DD` |
| 3 | Conformado Silver | Bronze Parquet | `s3://datalake/silver` | dbt (`staging`) + tests | Fila limpia | `dt=YYYY-MM-DD` |
| 4 | Integración | Silver | Modelos `intermediate` | dbt (vistas) | Entidad | — |
| 5 | Modelado Gold | intermediate | ClickHouse `marts` | dbt (`table`/`incremental`) | Hecho/Dimensión | `order_date` |
| 6 | Features y modelos | `marts.fct_*` | MLflow + Silver `scoring` | pandas/scikit-learn/XGBoost | Cliente-día | `scoring_dt` |
| 7 | Consumo | Marts + scoring | Metabase / Superset | SQL analítico | KPI | Temporal |

## 3. Paso a paso

> Los bloques SQL de esta sección son **extractos didácticos**: el código ejecutable completo vive en
> `infra/dbt/` (modelos y tests) y `infra/pipelines/` (entrenamiento y scoring).

### Paso 1 · Extracción desde el OLTP

Se usa una clave incremental para no releer toda la tabla y no castigar al sistema transaccional.

```sql
-- watermark almacenado en datalab_meta.ingest_watermarks
SELECT order_id, customer_id, order_ts, status, total_amount, updated_at
FROM   public.orders
WHERE  updated_at > :last_watermark
  AND  updated_at <= :window_end
ORDER BY updated_at;
```

Buenas prácticas aplicadas: lectura por *réplica* lógica (rol de solo lectura), `LIMIT` por lote,
ventana máxima de 24 h y registro de `rows_read` en `ingest_audit`.

### Paso 2 · Aterrizaje en el Data Lake (Bronze)

```python
# dags/ingest_oltp_to_bronze.py (extracto)
df = extract_orders(watermark, window_end)
write_parquet_partitioned(
    df,
    path=f"s3://datalake/bronze/orders/dt={run_date}/",
    compression="snappy",
    schema_mode="append",
)
audit(run_id=run_id, entity="orders", rows=len(df), watermark=window_end)
```

Bronze es **inmutable**: si la lógica de negocio cambia, se reprocesa Silver/Gold, nunca se reescribe Bronze.

### Paso 3 · Conformado en Silver (dbt staging)

```sql
-- models/staging/stg_orders.sql
{{ config(materialized='view', tags=['silver']) }}

SELECT
    CAST(order_id AS String)                     AS order_id,
    CAST(customer_id AS String)                  AS customer_id,
    toDateTime(order_ts)                         AS ordered_at,
    lower(trim(status))                          AS status,
    toDecimal64(total_amount, 2)                 AS total_amount,
    toDate(ordered_at)                           AS order_date
FROM {{ source('bronze', 'orders') }}
WHERE order_id IS NOT NULL
```

### Paso 4 · Integración (intermediate)

Se resuelven *joins*, deduplicaciones y reglas de negocio reutilizables. Sin agregaciones finales:
los `intermediate` son el "contrato interno" entre staging y marts.

### Paso 5 · Modelado dimensional Gold (esquema en estrella)

```sql
-- models/marts/fct_orders.sql
{{ config(materialized='incremental', unique_key='order_id',
          incremental_strategy='delete+insert', tags=['gold']) }}

SELECT
    o.order_id,
    o.customer_id,
    o.product_id,
    d.date_key,
    o.status,
    o.total_amount,
    o.total_amount - p.cost_amount AS gross_margin
FROM {{ ref('int_orders_enriched') }} o
JOIN {{ ref('dim_date') }} d    ON d.date_day = o.order_date
JOIN {{ ref('dim_product') }} p ON p.product_id = o.product_id
{% if is_incremental() %}
WHERE o.ordered_at > (SELECT max(ordered_at) FROM {{ this }})
{% endif %}
```

### Paso 6 · Features, entrenamiento y scoring

Los marts Gold son la **única** fuente de features (evita el sesgo de *training/serving skew*).
El `run_id` de Airflow se propaga a MLflow como etiqueta para unir linaje y métricas.

### Paso 7 · Consumo analítico

Metabase y Superset consultan exclusivamente `marts.*`; ningún dashboard golpea el OLTP ni Bronze.

## 4. Modelo dimensional resultante

| Tabla | Tipo | Granularidad | Clave | Métricas / Atributos |
|---|---|---|---|---|
| `marts.fct_orders` | Hecho | 1 fila por línea de pedido | `order_id`, `product_id` | `total_amount`, `gross_margin`, `quantity` |
| `marts.fct_payments` | Hecho | 1 fila por pago | `payment_id` | `paid_amount`, `payment_method` |
| `marts.dim_customer` | Dimensión | 1 fila por cliente (SCD2) | `customer_sk` | Segmento, ciudad, `valid_from/valid_to` |
| `marts.dim_product` | Dimensión | 1 fila por producto | `product_sk` | Categoría, marca, coste |
| `marts.dim_date` | Dimensión | 1 fila por día | `date_key` | Año, trimestre, mes, día de semana |
| `marts.dim_seller` | Dimensión | 1 fila por vendedor | `seller_sk` | Región, canal, antigüedad |

## 5. Contratos de datos y SLOs

| Contrato | Regla | Test dbt | Acción si falla |
|---|---|---|---|
| Unicidad | `fct_orders.order_id + product_id` único | `unique_combination` | Bloquea Gold |
| Integridad referencial | Todo `customer_id` existe en `dim_customer` | `relationships` | Bloquea Gold |
| Frescura | `max(ordered_at)` ≤ 24 h | `freshness` (`warn_after`) | Alerta a `governance` |
| Rango | `total_amount >= 0` | `accepted_range` | Cuarentena del lote |
| Completitud | Nulos en claves < 0.1 % | `not_null` + test singular | Reproceso de la partición |
| Volumen | ±20 % vs. media de 7 días | test singular `anomaly_volume` | Revisión manual |

## 6. Anti-patrones prohibidos

1. Transformar datos directamente en el OLTP (faltan permisos y afecta producción).
2. Escribir *features* en notebooks sin registrarlas en dbt (rompe el linaje).
3. Consumir Bronze desde BI (datos sin limpiar ni documentar).
4. Repartir `total_amount` sin declarar la granularidad del hecho.
5. Reparar datos *a mano* en el DW: siempre se corrige aguas arriba y se reprocesa.

## 7. Navegación

| Documento | Contenido |
|---|---|
| [docker-setup.md](../infrastructure/docker-setup.md) | Servicios, puertos y volúmenes de cada etapa |
| [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) | Del mart Gold al modelo registrado y al *drift* |
| [specialists-deep-dive.md](../agents/specialists-deep-dive.md) | Qué agente ejecuta cada paso y con qué comando |
| [README.md](../../README.md) | Arquitectura completa y verificación de servicios |
| [glossary.md](../glossary.md) | Siglas de modelado y almacenamiento (OLTP, OLAP, SCD2, SK/BK, Parquet) |
| [decisions/storage-and-runtime.md](../decisions/storage-and-runtime.md) | `D-04`, `D-05`, `D-11`: formato de Bronze, motor del DW y materialización |
