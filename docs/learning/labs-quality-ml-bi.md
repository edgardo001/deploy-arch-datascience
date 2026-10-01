# Laboratorios `L-09`…`L-14` — Modelado, Calidad, ML y BI

> Segunda parte de los laboratorios ([parte 1](exercises-labs.md): `L-01`…`L-08`, entorno, lake, ingesta y dbt).
> Mismos criterios: **evidencia reproducible** (comando + salida). Módulos en [curriculum.md](curriculum.md) ·
> Evaluación en [assessment.md](assessment.md).

## Encadenamiento

| Lab | Requiere antes | Módulo |
|---|---|---|
| `L-09` | `L-05` (hay datos en Gold) | `M4` |
| `L-10` | `L-07` (mart construido) | `M4` |
| `L-11` | `L-07` | `M5` |
| `L-12` | `L-07` | `M5` |
| `L-13` | `L-07` (features en Gold) | `M6` |
| `L-14` | `L-09` (SQL del KPI) | `M7` |

## `L-09` · KPI de negocio con SQL correcto

**Objetivo**: escribir una consulta de ingresos por categoría y mes sin doble conteo.

```bash
docker compose exec clickhouse clickhouse-client --database marts --query \
"SELECT toYYYYMM(d.date_day) AS mes, f.category, round(sum(f.line_total),2) AS ingreso
 FROM marts.fct_orders f JOIN marts.dim_date d ON d.date_key = f.date_key
 GROUP BY mes, f.category ORDER BY 1,2"
```

**Aceptación**: la suma coincide con la del total sin agrupar y el alumno explica la granularidad usada.
**Pista**: `dim_date` guarda `date_key` (YYYYMMDD) y `date_day`; si dudas de las columnas, usa `DESCRIBE TABLE marts.dim_date`.

## `L-10` · Ver el SCD2 en acción

```bash
docker compose exec clickhouse clickhouse-client --database marts --query \
"SELECT count() AS filas, uniqExact(customer_id) AS clientes,
        countIf(is_current) AS vigentes FROM marts.dim_customer"
```

**Aceptación**: explicar por qué `filas ≥ clientes`, qué significa `valid_from`/`valid_to` y por qué los hechos
se unen por `customer_sk` y no por `customer_id`.

## `L-11` · Provocar el *quality gate*

**Objetivo**: comprobar que un test crítico bloquea la publicación de Gold.

```bash
# 1) endurecer temporalmente infra/dbt/tests/anomaly_volume.sql para que falle
# 2) ejecutar solo el gate
docker compose --profile transform run --rm dbt test --select tag:critical
# 3) revertir el cambio
```

**Aceptación**: el alumno muestra el fallo, explica qué se habría publicado sin el gate y cómo queda registrado
en `meta.quality_gates`.

## `L-12` · Contratos de datos y validación automatizada

```bash
docker compose exec airflow python /opt/airflow/qa/contract_check.py --help
docker compose exec airflow python /opt/airflow/qa/contract_check.py
```

**Aceptación**: identificar en `infra/contracts/marts.yml` la tabla, el dueño, la granularidad y los tests
críticos; y explicar qué diferencia hay entre un test de dbt y una regla del contrato (`D-18`).

## `L-13` · Entrenar, registrar y decidir

```bash
docker compose exec airflow python /opt/airflow/pipelines/train_churn.py --run-id lab-L13
# abrir MLflow en http://localhost:5000 y localizar el run
```

**Aceptación**: el run aparece con parámetros, métricas (`roc_auc`, `pr_auc`, `brier`), etiquetas `run_id` y
`dbt_manifest`, y el alumno **argumenta** si promovería el modelo y con qué evidencia.

## `L-14` · Publicar un KPI certificado

**Objetivo**: cerrar el ciclo de valor en BI.

1. Conectar Metabase (3000) con `jdbc:clickhouse://clickhouse:8123/marts`.
2. Construir una pregunta con el SQL de `L-09`.
3. Publicarla en un dashboard con título, dueño y definición.

**Aceptación**: cualquier persona puede reproducir el número pegando el SQL documentado; el alumno explica qué
haría falta para *certificar* ese KPI ([orchestration-rules.md](../agents/orchestration-rules.md) §6).

## Variantes para subir de nivel

| Nivel | Variante del lab |
|---|---|
| `N1` | Repetir `L-09` cambiando la dimensión de agrupación (canal, vendedor) |
| `N2` | Detectar y corregir un doble conteo provocado por un `JOIN` mal planteado |
| `N3` | Proponer un test nuevo que impida que ese error vuelva a publicarse |

## Navegación

| Documento | Contenido |
|---|---|
| [exercises-labs.md](exercises-labs.md) | Parte 1: `L-01`…`L-08` (entorno, lake, ingesta, dbt) |
| [curriculum.md](curriculum.md) | Módulos `M0`…`M8` y rutas por perfil |
| [assessment.md](assessment.md) | Rúbrica `N0`-`N3` y banco de preguntas |
| [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) | Detalle del ciclo de modelo usado en `L-13` |
