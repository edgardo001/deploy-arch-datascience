# Glosario — Siglas, Términos y Servicios del Stack

> Referencia autoritativa de **todas las siglas y términos** que aparecen en el repositorio.
> Si un documento usa una abreviatura, aquí está su significado y qué implica en este entorno.
> Mapa de servicios al que da soporte: [README.md](../README.md) §2 · Registro de cambios del glosario: [prompt-log.md](prompts/prompt-log.md) `P-003`.

## 1. Cómo usar este glosario

1. Las siglas se agrupan **por dominio**; una misma sigla puede tener otro sentido en la industria y aquí se documenta **el que se usa en este repositorio**.
2. En las tablas, «Qué implica aquí» explica la consecuencia práctica, no la definición de diccionario.
3. El glosario es **vivo**: toda sigla nueva que se introduzca en un documento debe añadirse aquí en el mismo cambio (regla de indexación estricta).
4. Los nombres de archivos, carpetas y objetos se documentan en la §6 (convenciones de nomenclatura).

## 2. Datos, modelado y linaje

| Sigla / término | Significado | Qué implica aquí |
|---|---|---|
| **OLTP** | Online Transaction Processing | PostgreSQL `ecommerce_oltp`: pedidos, clientes, productos; solo lectura para el pipeline |
| **OLAP** | Online Analytical Processing | ClickHouse `marts`: consultas agregadas sobre el modelo en estrella |
| **DW / DWH** | Data Warehouse | Capa Gold servida por ClickHouse (y DuckDB como réplica local) |
| **Data Lake** | Repositorio de datos crudos en objetos | MinIO con Parquet inmutable en `bronze/` |
| **Lakehouse** | Lake + capacidades de warehouse | Bronze en S3 + transformación SQL con dbt, sin mover los datos a otro motor |
| **Medallion** | Arquitectura por capas de calidad | `bronze` (crudo) → `silver` (conformado) → `gold` (modelado) |
| **S3** | Simple Storage Service (API de AWS) | MinIO la emula en local; rutas `s3://datalake/...` |
| **Parquet** | Formato columnar comprimido | Formato de todo el lake; compresión `snappy` |
| **ELT / ETL** | Extract-Load-Transform / Extract-Transform-Load | Aquí **ELT**: se carga crudo y se transforma dentro del DW con dbt |
| **CDC** | Change Data Capture | Patrón alternativo a la extracción por *watermark* (no implementado) |
| **Watermark** | Marca de agua incremental | Columna `updated_at` que acota cada extracción: `> último_valor` |
| **Partición Hive** | Convención `clave=valor` en la ruta | `dt=YYYY-MM-DD/part-000.parquet`; ClickHouse la lee con `s3()` |
| **Esquema en estrella** | Modelo dimensional hecho + dimensiones | `fct_orders`, `fct_payments` + `dim_customer/product/seller/date` |
| **Hecho / Fact** | Tabla de eventos medibles | Granularidad declarada (p. ej. una fila por línea de pedido) |
| **Dimensión** | Contexto descriptivo del hecho | Atributos de cliente, producto, vendedor y calendario |
| **SCD2** | Slowly Changing Dimension tipo 2 | `dim_customer` guarda versiones con `valid_from`/`valid_to`/`is_current` |
| **SK** | Surrogate Key | Clave sustituta: `customer_sk = md5(customer_id)`, independiente del OLTP |
| **BK** | Business Key | Clave natural del negocio: `customer_id`, `order_id` |
| **DAG** | Directed Acyclic Graph | Grafo de tareas de Airflow: `ingest_oltp_to_bronze`, `transform_dbt_marts`, `train_churn_model` |
| **SQL** | Structured Query Language | Lenguaje de los modelos dbt y de las consultas de BI |
| **Linaje** | Trazabilidad origen → destino | `manifest.json` de dbt + OpenLineage; cada columna se puede rastrear hasta Bronze |
| **Contrato de datos** | Acuerdo explícito de esquema y calidad | [contracts/marts.yml](../infra/contracts/marts.yml), validado por `governance` |

## 3. Plataforma, runtime y conexiones

| Sigla / término | Significado | Qué implica aquí |
|---|---|---|
| **Docker** | Motor de contenedores | Cada componente del stack corre en su propio contenedor |
| **Docker Compose** | Orquestador local de contenedores | [docker-compose.yml](../docker-compose.yml); perfiles `core`, `orchestration`, `ml`, `bi`, `transform` |
| **Volumen** | Almacenamiento persistente de Docker | `pgdata`, `minio_data`, `clickhouse_data`… sobreviven a `down` |
| **Bind mount** | Montaje de una carpeta del host | `./infra/dbt`, `./infra/pipelines`, `./infra/jupyter/work` (código versionado en Git) |
| **Healthcheck** | Sonda de salud del contenedor | 9 servicios con sonda; `dbt` es efímero y `minio-init` es *one-shot* |
| **DSN** | Data Source Name | Cadena de conexión que recibe cada agente por `run_id`, de vida corta |
| **JDBC / ODBC** | Drivers de conexión a bases de datos | Metabase/Superset → ClickHouse (`jdbc:clickhouse://clickhouse:8123/marts`) |
| **PySpark** | API de Spark para Python | Disponible en JupyterLab para volúmenes que no quepan en pandas |
| **API** | Application Programming Interface | Metabase/Superset se automatizan por HTTP; Qdrant y MLflow exponen API REST |

## 4. Negocio, BI y visualización

| Sigla / término | Significado | Qué implica aquí |
|---|---|---|
| **BI** | Business Intelligence | Capa de consumo: Metabase y Superset |
| **KPI** | Key Performance Indicator | Métrica certificada con definición, dueño y fuente SQL |
| **DAX** | Data Analysis Expressions | Lenguaje de métricas de Power BI; aquí se traduce a SQL certificado |
| **Self-service** | Analítica delegada al usuario | Metabase permite crear preguntas sin escribir SQL |
| **Dashboard** | Cuadro de mando | Publicado solo tras *quality gate* firmado por `governance` |
| **Churn** | Tasa de abandono de clientes | Etiqueta `churn_label`: sin compras en 180 días |

## 5. Ciencia de datos y MLOps

| Sigla / término | Significado | Qué implica aquí |
|---|---|---|
| **ML** | Machine Learning | Modelo `churn_classifier` (XGBoost/Scikit-Learn) |
| **MLOps** | Operación de ML (ML + DevOps) | Versionado, *tracking*, promoción y *scoring* automatizados |
| **EDA** | Exploratory Data Analysis | Notebook [01_eda_orders.ipynb](../infra/jupyter/work/01_eda_orders.ipynb) |
| **Feature** | Variable de entrada del modelo | `recency_days`, `orders_last_30d`, `monetary_365d`, `avg_ticket`, `tickets_support_90d` |
| **Baseline** | Referencia a superar | El candidato solo se promueve si mejora la métrica vigente |
| **ROC-AUC** | Area Under the ROC Curve | Métrica principal de discriminación del clasificador |
| **PR-AUC** | Area Under the Precision-Recall curve | Métrica útil con clases desbalanceadas (churn) |
| **Brier** | Brier score | Error cuadrático de las probabilidades predichas (calibración) |
| **IC 95 %** | Intervalo de confianza al 95 % | Exigido para declarar mejora sobre el *baseline* |
| **Training/serving skew** | Sesgo entre entrenar y servir | Se evita usando **solo** marts Gold como fuente de features |
| **Model card** | Ficha del modelo | Supuestos, datos de referencia, métricas y limitaciones |
| **Model Registry** | Registro de modelos versionados | MLflow: etapas `None` → `Staging` → `Production` → `Archived` |
| **Scoring** | Puntuación con el modelo | Batch diario a `s3://datalake/silver/scoring/scoring_dt=...` |
| **Embedding** | Vector denso de significado | Documentos y model cards indexados en Qdrant |
| **Vector DB** | Base de datos vectorial | Qdrant (`datalab_knowledge`): memoria de largo plazo de los agentes |

## 6. Calidad, gobierno y estadística

| Sigla / término | Significado | Qué implica aquí |
|---|---|---|
| **DoD** | Definition of Done | Criterio de aceptación por agente (columna en [AGENTS.md](../AGENTS.md) §2) |
| **Handoff** | Transferencia tipada entre agentes | JSON con `run_id`, artefactos, contratos y `next_agent` |
| **Quality gate** | Puerta de calidad | Si un test crítico falla, Gold no se publica |
| **Guardrail** | Regla dura de negocio | Ver [orchestration-rules.md](agents/orchestration-rules.md) §6 |
| **Fallback** | Plan alternativo ante fallo | Reintentos, degradación o escalado al usuario |
| **Backoff exponencial** | Espera creciente entre reintentos | 2 s → 8 s → 32 s con *jitter*; máximo 3 intentos |
| **Circuit breaker** | Cortacircuitos | Tras 3 fallos del mismo agente en 30 min se desvía al `orchestrator` |
| **Data drift** | Deriva de la distribución de entrada | Se vigila por feature; PSI > 0.2 congela el *scoring* |
| **Concept drift** | Cambio en la relación entrada→salida | Exige reentrenar con etiquetas nuevas |
| **PSI** | Population Stability Index | `0.1`–`0.2` vigilar; `> 0.2` congelar (umbral en `DRIFT_PSI_THRESHOLD`) |
| **Sesgo / Bias** | Trato desigual por atributo sensible | Auditado sobre `gender` y `age_band` |
| **Paridad demográfica** | Demographic parity | Igual tasa de predicción positiva entre grupos |
| **Disparate impact** | Impacto desproporcionado | Se reporta con severidad por grupo sensible |
| **SLA / SLO** | Service Level Agreement / Objective | Frescura ≤ 24 h y volumen ±20 % vs. media de 7 días |
| **Auditoría** | Revisión trazable | Cada run deja `quality_gates`, `ingest_audit` y `handoffs` en `datalab_meta` |

## 7. Proyecto, agentes y gobierno documental

| Sigla / término | Significado | Qué implica aquí |
|---|---|---|
| **`P-00N`** | Identificador de petición | Registro vivo en [prompt-log.md](prompts/prompt-log.md) |
| **`R-00N`** | Identificador de requisito | Trazabilidad en [initial-prompt.md](prompts/initial-prompt.md) §3 |
| **`run_id`** | Identificador único de ejecución | Une Airflow → dbt → MLflow → *scoring* → dashboard |
| **`run_state`** | Estado global del pipeline | JSON documentado en [MEMORY.md](../MEMORY.md) §5 |
| **`plan.json`** | Plan de ejecución del orquestador | Pasos, dueños, dependencias y criterios de aceptación |
| **`session_events`** | Bitácora de la sesión | Decisiones y errores persistidos en `datalab_meta` |
| **`M-0N`** | Módulo del currículo de aprendizaje | Ruta formativa, p. ej. `M3` (dbt); ver [learning/curriculum.md](learning/curriculum.md) |
| **`L-0N`** | Laboratorio verificable | Ejercicio con comandos reales y criterio de aceptación binario |
| **`Q-0N`** | Pregunta del banco de autoevaluación | Se usa en el repaso espiral al cerrar cada módulo |
| **`T-0N`** | Tarea diaria del backlog laboral | Solicitud real del área; ver [learning/daily-tasks.md](learning/daily-tasks.md) |
| **`professor` / `student`** | Agentes docentes (Profesor y Alumno) | Diseñan la ruta y aprenden con evidencia; ver [learning/](learning/README.md) |

## 8. Los servicios del stack, uno por uno

| Servicio (contenedor) | Siglas | Qué es y para qué está aquí |
|---|---|---|
| PostgreSQL OLTP (`oltp-postgres`) | OLTP, SQL | Base transaccional del e-commerce simulado + `datalab_meta` (metadata) + `airflow_meta` |
| MinIO (`minio`) | S3, API | Emulador de S3: guarda el Parquet crudo (Bronze), el conformado y los artefactos de MLflow |
| ClickHouse (`clickhouse`) | OLAP, DW | Motor columnar del Data Warehouse: materializa los marts en estrella |
| Apache Airflow (`airflow`) | DAG, ELT | Orquesta la ingesta, la transformación con dbt y el entrenamiento/publicación del modelo |
| dbt (`dbt`, efímero) | SQL, ELT, SK/BK | Transforma Bronze en Silver/Gold y ejecuta los tests de calidad y el linaje |
| MLflow (`mlflow`) | MLOps, Model Registry | Registra experimentos, métricas, artefactos y versiones promovibles del modelo |
| JupyterLab (`jupyter`) | EDA, PySpark | Entorno de experimentación con pandas, scikit-learn, XGBoost y PySpark |
| Metabase (`metabase`) | BI, KPI | BI *self-service* para explorar los marts sin escribir SQL |
| Apache Superset (`superset`) | BI, API | Dashboards avanzados y alertas con control fino de permisos |
| Qdrant (`qdrant`) | Vector DB, Embedding | Memoria de largo plazo de los agentes (documentación, model cards, incidentes) |
| *(auxiliares)* | one-shot | `minio-init` crea los buckets y termina; `dbt` se ejecuta bajo demanda con `--profile transform` |

## 9. Convenciones de nomenclatura del repositorio

| Patrón | Significado | Ejemplo |
|---|---|---|
| `dt=YYYY-MM-DD/` | Partición Hive por día de extracción | `bronze/orders/dt=2026-02-14/part-000.parquet` |
| `stg_` | Modelo de *staging* (Silver, tipado y limpio) | `stg_orders`, `stg_payments` |
| `int_` | Modelo *intermediate* (integración sin agregación final) | `int_orders_enriched` |
| `dim_` | Dimensión del esquema en estrella | `dim_customer`, `dim_date` |
| `fct_` | Tabla de hechos | `fct_orders`, `fct_payments` |
| `_sources.yml` | Declaración de fuentes y frescura | `models/staging/_sources.yml` |
| `_marts.yml` | Tests y descripciones de los marts | `models/marts/_marts.yml` |
| `tag: critical` | Etiqueta que activa el *quality gate* | `dbt test --select tag:critical` |
| `customer_sk` / `customer_id` | Clave sustituta (SK) / clave de negocio (BK) | Unión de hechos con dimensiones |
| `run_<ts>_<hash>` | Formato de `run_id` | `run_2026-02-14T09-30-12Z_a13f` |

## 10. Navegación

| Documento | Contenido |
|---|---|
| [README.md](../README.md) | Mapa de servicios y puertos (usa las siglas de la §3 y la §8) |
| [docs/infrastructure/docker-setup.md](infrastructure/docker-setup.md) | Puertos, variables y volúmenes de cada servicio |
| [docs/architecture/data-pipeline.md](architecture/data-pipeline.md) | Términos de Medallion, particiones y contratos en contexto |
| [docs/prompts/prompt-log.md](prompts/prompt-log.md) | Peticiones `P-003` y `P-004` que crearon el glosario y las decisiones |
| [decisions/README.md](decisions/README.md) | Por qué se eligió cada herramienta citada aquí y cuándo deja de recomendarse |
