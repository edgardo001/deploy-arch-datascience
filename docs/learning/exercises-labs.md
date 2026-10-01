# Laboratorios `L-01`…`L-08` — Entorno, Lake, Ingesta y dbt

> Primera parte de los laboratorios; la segunda ([`L-09`…`L-14`](labs-quality-ml-bi.md)) cubre modelado, calidad,
> ML y BI. Cada lab se aprueba con **evidencia reproducible**: comando ejecutado + salida observada.
> Módulos en [curriculum.md](curriculum.md) · Evaluación en [assessment.md](assessment.md).

## Reglas de los labs

1. Se ejecutan sobre el stack levantado (`docker compose up -d`) salvo indicación contraria.
2. La evidencia es la **salida real** del comando, no una descripción de lo que debería salir.
3. Si un lab falla por el entorno, se diagnostica con [runbook.md](../operations/runbook.md) §4 antes de pedir ayuda.
4. Al terminar cada lab, el alumno anota en su `learning-log` la evidencia y **una** duda nueva.

## `L-01` · Levantar y verificar el stack

**Objetivo**: arrancar el entorno y comprobar la salud de los 9 servicios permanentes.

```bash
cp .env.example .env
docker compose up -d
docker compose up -d minio-init          # crea bronze/silver/gold/mlflow
docker compose ps                        # esperar 9/9 healthy
```

**Aceptación**: `docker compose ps` muestra los 9 servicios permanentes *healthy* y existe el bucket `datalake`.
**Pista**: si Airflow no arranca → `AIRFLOW_UID` en `.env` ([runbook.md](../operations/runbook.md) §4).

## `L-02` · Mapa de servicios y puertos

**Objetivo**: asociar cada puerto con su servicio y su rol, sin mirar la tabla.

```bash
curl -sI http://localhost:9000/health | head -1
curl -s 'http://localhost:8123/?query=SELECT%201'
curl -s http://localhost:6333/healthz
```

**Aceptación**: identificar 8123, 9000, 9001, 8080, 5000, 8888, 3000, 8088, 6333 y 5432 con su servicio y función.
**Referencia**: [README.md](../../README.md) §2 · [glossary.md](../glossary.md) §8.

## `L-03` · Leer Bronze (Parquet) sin copiar datos

**Objetivo**: consultar el lake directamente con la función `s3()` de ClickHouse.

```bash
docker compose exec clickhouse clickhouse-client --query \
"SELECT count() AS filas, min(_path) AS ejemplo
 FROM s3('http://minio:9000/datalake/bronze/orders/dt=*/part-*.parquet',
         '<MINIO_ROOT_USER>','<MINIO_ROOT_PASSWORD>','Parquet')"
```

**Aceptación**: el conteo coincide con lo registrado en `meta.ingest_audit` para esas particiones.
**Requiere**: haber ejecutado `L-05` al menos una vez.

## `L-04` · Bronze vs Gold: la misma entidad, dos verdades

**Objetivo**: comparar el dato crudo con el modelado y explicar las diferencias.

```bash
docker compose exec clickhouse clickhouse-client --database marts --query \
"SELECT count() AS lineas, sum(total_amount) AS ingreso FROM marts.fct_orders"
```

**Aceptación**: explicar por escrito por qué el conteo de Bronze (una fila por pedido) y el de Gold
(una fila por **línea** de pedido) no coinciden, y qué implicaría sumar el importe sin cuidado.

## `L-05` · Ejecutar la ingesta incremental

```bash
docker compose exec airflow airflow dags list | grep ingest_
docker compose exec airflow airflow dags test ingest_oltp_to_bronze 2026-02-14
```

**Aceptación**: el DAG termina en verde y aparecen las particiones `dt=2026-02-14` en Bronze.

## `L-06` · Auditar la ingesta y verificar el cuadre

```bash
docker compose exec oltp-postgres psql -U datalab -d datalab_meta -c \
"SELECT entity, dt, rows_read, watermark FROM meta.ingest_audit ORDER BY ts DESC LIMIT 5;"
```

**Aceptación**: una fila por entidad y partición con `rows_read` coherente con `L-03`, y explicación de para qué
sirve el `checksum`.

## `L-07` · Construir con dbt por capas

```bash
docker compose --profile transform run --rm dbt build --select staging
docker compose --profile transform run --rm dbt build --select intermediate marts
```

**Aceptación**: ambas ejecuciones sin `error` y tabla `marts.customer_features` consultable.
**Observa**: qué modelos son vistas y cuáles tablas; relaciónalo con `D-11`.

## `L-08` · Escribir un test que falle y luego pase

**Objetivo**: entender qué es un test singular y cómo se lee su fallo.

```bash
# 1) crear infra/dbt/tests/lab_ordenes_no_negativas.sql con una condición imposible
# 2) ejecutar y leer el fallo
docker compose --profile transform run --rm dbt test --select lab_ordenes_no_negativas
# 3) corregir la condición y volver a ejecutar
```

**Aceptación**: la primera ejecución falla con el número de filas que incumplen, y la segunda pasa.

## Progresión sugerida

| Si vienes de… | Empieza por | Evita de momento |
|---|---|---|
| SQL y BI | `L-01`, `L-02`, `L-09`, `L-14` | Spark y orquestación |
| Python y ML | `L-01`, `L-07`, `L-13` | Configuración de Compose |
| Infraestructura | `L-01`, `L-02`, `L-05`, `L-06`, `L-11` | Modelado dimensional |
| Cero experiencia | `L-01` → `L-14` en orden | Todo lo que no entiendas: pregúntalo al `professor` |

## Navegación

| Documento | Contenido |
|---|---|
| [labs-quality-ml-bi.md](labs-quality-ml-bi.md) | Parte 2: `L-09`…`L-14` (modelado, calidad, ML y BI) |
| [curriculum.md](curriculum.md) | Módulos `M0`…`M8` y rutas por perfil |
| [assessment.md](assessment.md) | Rúbrica y banco de preguntas |
| [runbook.md](../operations/runbook.md) | Comandos de operación y diagnóstico de fallos |
