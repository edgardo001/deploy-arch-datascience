# Decisiones `D-08`…`D-12` — Orquestación, Transformación e Ingesta

> Módulo de [decisiones](README.md). Cubre quién mueve los datos, quién los transforma y con qué garantías.
> Siglas: [glossary.md](../glossary.md) · Implementación: `infra/airflow/` e `infra/dbt/`.

## `D-08` · Apache Airflow para orquestar

| Campo | Detalle |
|---|---|
| **Decisión** | Airflow 2.9 con `LocalExecutor` y tres DAGs: `ingest_oltp_to_bronze`, `transform_dbt_marts`, `train_churn_model` |
| **Contexto** | Hay dependencias reales entre extracción, transformación, *quality gate* y entrenamiento, con reintentos y ventanas diarias |
| **Por qué** | Es el estándar de facto del sector (paridad con producción); reintentos con *backoff* exponencial declarativos; `depends_on: service_healthy` conecta el orquestador con el estado real del stack; UI con logs por tarea y `dags test` para validar sin esperar la ventana; TaskFlow permite pasar resultados tipados entre tareas |
| **Cuándo NO** | *Streaming* o latencia sub-minuto (Airflow no es un motor de eventos); pipelines puramente de datos con un solo paso (un *cron* basta); equipos pequeños que priorizan simplicidad extrema |
| **Señal de migración** | Necesidad de *backfills* masivos con particionado por *asset*, o de *streaming* con estado; también si el 80 % del trabajo es transformación SQL (dbt Cloud/Dagster lo expresan mejor) |
| **Reversibilidad** | **Media**: los DAGs son Python portable, pero el *scheduler*, la metadata y las conexiones hay que recrearlos |

| Alternativa | Pros | Contras |
|---|---|---|
| Dagster | Modelo por *assets*, tipado, excelente DX local | Comunidad menor; menos ofertas de trabajo y menos ejemplos corporativos |
| Prefect | API moderna, despliegue ligero | Ecosistema más joven; menos *providers* maduros que Airflow |
| Mage / Kestra | Muy rápidos de arrancar, UI atractiva | Menor madurez y menos operables a escala |
| `cron` + scripts | Cero infraestructura | Sin reintentos, sin linaje, sin UI, sin dependencias entre pasos |
| dbt Cloud | Transformación gestionada | No cubre ingesta ni entrenamiento; coste por asiento |

## `D-09` · dbt Core para transformar

| Campo | Detalle |
|---|---|
| **Decisión** | dbt Core con capas `staging` → `intermediate` → `marts`, tests y `manifest.json` para linaje |
| **Contexto** | Transformaciones SQL sobre Parquet (lake S3) y ClickHouse, con necesidad de tests y de trazabilidad columna a columna |
| **Por qué** | El SQL versionado en Git sustituye a las "consultas sueltas"; `ref()`/`source()` construyen el DAG de linaje automáticamente; los tests (`unique`, `not_null`, `relationships`, `accepted_range`) son el *quality gate* del pipeline; `dbt docs` publica el grafo; es agnóstico del motor (ClickHouse hoy, DuckDB o Postgres mañana) |
| **Cuándo NO** | Lógica procedural fila a fila o *streaming*; cuando se necesita un lenguaje de propósito general (aquí entran PySpark o Python); equipos que no van a mantener modelos ni tests |
| **Señal de migración** | Transformaciones que requieren bucles, UDFs complejas o estado entre filas que el SQL no expresa con claridad |
| **Reversibilidad** | **Media**: los modelos son SQL, pero se pierde el linaje, los tests y la documentación generada |

| Alternativa | Pros | Contras |
|---|---|---|
| SQL a mano en DAGs | Sin capa extra | Sin linaje ni tests centralizados; el orden de ejecución se rompe con facilidad |
| PySpark / pandas | Máxima flexibilidad | Sin linaje, sin tests declarativos, más difícil de revisar y de reutilizar |
| SQLMesh | Planificación por *intervals*, *virtual environments* | Ecosistema y comunidad menores; menos materiales de estudio |
| Dataform | Integrado con BigQuery | Atado a GCP; sin soporte nativo de ClickHouse |
| Procedimientos almacenados | Cerca del motor | Sin versionado, sin tests, sin linaje y difíciles de testear |

## `D-10` · Ingesta incremental por *watermark* (sin CDC)

| Campo | Detalle |
|---|---|
| **Decisión** | Extracción por lotes con `updated_at > último_watermark`, partición diaria, cuadre de conteos y auditoría en `meta.ingest_audit` |
| **Contexto** | OLTP sin privilegios de replicación lógica; volúmenes modestos; se prioriza simplicidad y capacidad de repetición |
| **Por qué** | No requiere tocar la configuración del motor ni permisos especiales; cada partición se reemplaza (*overwrite*) y el `run_id` la hace idempotente; el cuadre origen/destino detecta pérdidas; el `checksum` da evidencia; el *backfill* es trivial (mover la fecha) |
| **Cuándo NO** | Borrados físicos (no hay `updated_at` que los capture); latencia sub-minuto; tablas sin columna de auditoría fiable; alto volumen de cambios con ventanas muy estrechas |
| **Señal de migración** | Necesidad de capturar *hard deletes* o de refrescar cada pocos minutos, o lecturas que castigan al OLTP (entonces CDC con Debezium) |
| **Reversibilidad** | **Media**: el destino Bronze no cambia; se sustituye el extractor por un *connector* CDC |

| Alternativa | Pros | Contras |
|---|---|---|
| CDC con Debezium + Kafka | Captura borrados, latencia de segundos, sin castigar el OLTP | Requiere `wal_level=logical`, Kafka y Connect: +3 servicios y mucha operación |
| *Full refresh* diario | Imposible perder cambios | Coste de lectura y de red; no escala con el histórico |
| *Triggers* + tabla de cambios | Basado en el propio motor | Penaliza la escritura del OLTP y ensucia el modelo operativo |
| Snapshots por `SELECT *` con hashes | Detecta cualquier cambio | Duplica almacenamiento y complica el *merge* |

## `D-11` · Materialización por capa (view / table / incremental)

| Campo | Detalle |
|---|---|
| **Decisión** | `staging` e `intermediate` como vistas; `marts` como tabla; `fct_*` y `customer_features` incrementales `delete+insert`; `dim_customer` se reconstruye completa (SCD2) |
| **Contexto** | Datos de e-commerce con histórico creciente y necesidad de *joins* rápidos en BI |
| **Por qué** | Las vistas evitan duplicar almacenamiento en capas de paso; las dimensiones son pequeñas y estables (tabla completa es más simple de razonar); los hechos crecen y se benefician de `delete+insert` por clave, que es idempotente y evita duplicados; el SCD2 necesita recalcular `valid_from`/`valid_to` sobre toda la historia |
| **Cuándo NO** | Hechos con cientos de millones de filas donde el `delete+insert` por clave se vuelve caro; dimensiones enormes con cambios frecuentes; cuando se necesitan *snapshots* históricos por día (ahí toca `dbt snapshot`) |
| **Señal de migración** | El incremental tarda más que un *full rebuild*, o aparecen filas huérfanas por claves que ya no llegan en el lote |
| **Reversibilidad** | **Baja**: es una línea de `config()` en cada modelo |

| Alternativa | Pros | Contras |
|---|---|---|
| Todo incremental | Cargas mínimas | Complejidad de claves y estrategias; riesgo de estados inconsistentes |
| Todo vista | Cero duplicación y siempre fresco | BI lento: recalcula agregaciones en cada consulta |
| Todo tabla | Simple y rápido de leer | Coste de reconstrucción diaria creciente |
| Motor `ReplacingMergeTree` de ClickHouse | Fusiona versiones en segundo plano | Semanticas de deduplicación eventuales; más difícil de razonar que `delete+insert` |

## `D-12` · Imagen de Airflow propia construida en local

| Campo | Detalle |
|---|---|
| **Decisión** | `infra/airflow/Dockerfile` (`FROM apache/airflow:2.9.3-python3.11`) + `requirements.txt` con *providers* y librerías |
| **Contexto** | La imagen oficial "slim" no trae `PostgresHook`, `boto3`, `pandas`, `pyarrow`, `dbt-clickhouse` ni `mlflow` |
| **Por qué** | Reproducibilidad exacta: la imagen se construye igual en cualquier máquina y las versiones quedan fijadas por escrito; el arranque no depende de la red; es el patrón oficial recomendado por Airflow para dependencias adicionales |
| **Cuándo NO** | Entornos efímeros de una sola sesión donde se prefiera no construir nada; equipos que ya tengan una imagen corporativa con todas las dependencias |
| **Señal de migración** | Necesidad de paridad con una imagen corporativa o de *builds* multi-arquitectura en CI |
| **Reversibilidad** | **Baja**: se cambia `build:` por `image:` en el Compose |

| Alternativa | Pros | Contras |
|---|---|---|
| `_PIP_ADDITIONAL_REQUIREMENTS` | Cero Dockerfile | Instala en cada arranque (lento y no reproducible); Airflow lo marca como solo para desarrollo |
| Imagen oficial + `pip install` manual | Rápido de improvisar | Se pierde al recrear el contenedor; nada documentado |
| Imagen "all-in-one" con Spark y todo | Un contenedor para todo | Multi-GB, arranque lento y conflictos de dependencias |
| Astronomer Runtime | Imagen mantenida por el proveedor | Añade dependencia y capa de abstracción |

## Navegación

| Documento | Contenido |
|---|---|
| [README.md](README.md) | Índice de las 18 decisiones, criterios y disparadores |
| [storage-and-runtime.md](storage-and-runtime.md) | `D-01`…`D-07`: almacenamiento y runtime |
| [ml-bi-and-memory.md](ml-bi-and-memory.md) | `D-13`…`D-18`: MLOps, BI y memoria |
| [orchestration-rules.md](../agents/orchestration-rules.md) | Reglas de ruteo sobre estas herramientas |
