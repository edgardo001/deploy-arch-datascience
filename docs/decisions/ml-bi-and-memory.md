# Decisiones `D-13`…`D-18` — MLOps, BI, Memoria y Contratos

> Módulo de [decisiones](README.md). Cubre el ciclo de vida del modelo, la capa de consumo y la memoria
> de los agentes. Siglas: [glossary.md](../glossary.md) · Implementación: `infra/pipelines/`, `infra/qa/`.

## `D-13` · MLflow para *tracking* y registro de modelos

| Campo | Detalle |
|---|---|
| **Decisión** | MLflow 2.14 con *backend* PostgreSQL (`datalab_meta`) y artefactos en `s3://datalake/mlflow` |
| **Contexto** | Se comparan variantes de un clasificador de churn y hay que poder volver a una versión anterior y servirla |
| **Por qué** | Open source y autoalojado (sin coste por experimento); une parámetros, métricas, firma del modelo y artefactos en un mismo `run_id` que es la clave de trazabilidad del pipeline; el Model Registry con etapas (`Staging`/`Production`) hace explícita la promoción; `mlflow models serve` sirve el modelo sin escribir un API |
| **Cuándo NO** | Cuando se necesita un *feature store* o linaje de features a nivel de columna (MLflow no lo es); despliegues de inferencia en tiempo real con *autoscaling*; equipos que requieren colaboración visual avanzada y *sweeps* integrados tipo W&B |
| **Señal de migración** | Necesidad de *feature store* (Feast), de linaje por columna (OpenLineage) o de servir con SLA y autoescalado (KServe/Seldon) |
| **Reversibilidad** | **Media**: los modelos son serializables, pero se pierde el historial de experimentos si no se exporta |

| Alternativa | Pros | Contras |
|---|---|---|
| Weights & Biases | UI excelente, *sweeps* y colaboración | SaaS de pago; los datos salen del entorno local |
| ClearML / Neptune | Alternativas completas de MLOps | Más peso operativo; *lock-in* de plataforma |
| SageMaker / Vertex AI | Servicio gestionado y escalado | Coste, atadura a la nube y credenciales |
| DVC + Git | Versiona datos y modelos junto al código | No registra métricas ni etapas; pensado para artefactos, no para experimentos |
| Hojas de cálculo / nombres de archivo | Cero infraestructura | Sin reproducibilidad ni auditoría; el primer error no se detecta |

## `D-14` · JupyterLab como entorno de experimentación

| Campo | Detalle |
|---|---|
| **Decisión** | JupyterLab con `pandas`, `scikit-learn`, `XGBoost`, `PySpark` y `clickhouse-connect`, montado sobre `./infra/jupyter/work` |
| **Contexto** | Fase exploratoria (EDA) y construcción de *features* antes de fijarlas en dbt o en `pipelines/` |
| **Por qué** | Estándar de facto en ciencia de datos; ejecución por celdas con visualización inmediata; el *bind mount* deja los notebooks versionados en Git y auditables; el mismo contenedor tiene acceso a ClickHouse, el lake S3 y MLflow por la red interna |
| **Cuándo NO** | Cuando el código ya es un *pipeline*: los notebooks no se testean ni se revisan bien en un *diff*; tampoco para procesos programados o con estado compartido entre usuarios |
| **Señal de migración** | La lógica del notebook se usa más de una vez: debe convertirse en modelo dbt o script de `pipelines/` |
| **Reversibilidad** | **Baja**: la imagen se cambia en una línea del Compose |

| Alternativa | Pros | Contras |
|---|---|---|
| VS Code Server | Mejor IDE, *debugger*, Git integrado | Peor para informes con gráficos y narrativa; más configuración |
| Scripts `.py` + `papermill` | Versionables, testeables, automatizables | Sin exploración interactiva ni visualización inmediata |
| Apache Zeppelin | Multi-lenguaje (SQL, Scala) | Comunidad pequeña y UI menos pulida |
| Databricks Notebooks | Colaboración y clúster gestionado | Coste y dependencia de nube |

## `D-15` · Scikit-Learn / XGBoost en CPU para el *baseline*

| Campo | Detalle |
|---|---|
| **Decisión** | Clasificador XGBoost (con respaldo en `sklearn`) entrenado en CPU sobre `marts.customer_features` |
| **Contexto** | Datos tabulares, desbalance de clases, objetivo de *baseline* reproducible y rápido en una laptop |
| **Por qué** | Los modelos de árboles con *gradient boosting* siguen siendo el mejor punto de partida en tabular; entrenamiento en segundos; `scale_pos_weight` maneja el desbalance; la integración con MLflow es directa; no exige GPU ni *framework* profundo |
| **Cuándo NO** | Datos no estructurados (texto, imagen, audio), secuencias temporales largas o interacciones de muy alto orden: ahí una red neuronal o un modelo secuencial es mejor; tampoco si se necesita explicabilidad regulatoria estricta y lineal (mejor regresión regularizada) |
| **Señal de migración** | El techo de métrica se estanca con *feature engineering* y el problema pide representaciones aprendidas |
| **Reversibilidad** | **Media**: el registro de MLflow conserva el modelo anterior, pero las features de entrada condicionan el cambio |

| Alternativa | Pros | Contras |
|---|---|---|
| LightGBM / CatBoost | Más rápidos; CatBoost maneja categóricas nativamente | Otra dependencia; resultados muy similares en este rango de datos |
| PyTorch / TensorFlow | Representaciones complejas | Necesita GPU para brillar; más coste de mantenimiento y *tuning* |
| Regresión logística | Interpretable y explicable | Menor capacidad predictiva en interacciones no lineales |
| AutoML (H2O, auto-sklearn) | Explora *pipelines* automáticamente | Caja negra, lento y difícil de auditar en el *quality gate* |

## `D-16` · Qdrant como base de datos vectorial

| Campo | Detalle |
|---|---|
| **Decisión** | Qdrant (`datalab_knowledge`) como memoria semántica de largo plazo de los agentes |
| **Contexto** | Los agentes deben recuperar documentación, *model cards* e incidentes por similitud, con filtros por metadatos |
| **Por qué** | Servicio ligero con API REST/gRPC; filtrado por *payload* de alta calidad (necesario para acotar por `module`, `stage` o `severity`); *snapshots* para respaldo; colecciones versionables y reindexado por *alias swap* |
| **Cuándo NO** | Si ya existe PostgreSQL y el volumen es pequeño: `pgvector` evita un servicio más; tampoco para datos que requieren transacciones ACID o consultas relacionales |
| **Señal de migración** | El coste de mantener dos motores supera el beneficio, o el *retrieval* necesita *hybrid search* con BM25 avanzado |
| **Reversibilidad** | **Media**: los *embeddings* se regeneran, pero hay que reindexar y reevaluar el *retrieval* |

| Alternativa | Pros | Contras |
|---|---|---|
| `pgvector` en PostgreSQL | Un servicio menos; SQL y transacciones | Índices y filtrado menos eficientes a gran escala; memoria del motor compartida con OLTP |
| Chroma | Trivial de arrancar | Menos orientado a producción; filtrado y escalado limitados |
| FAISS | Librería ultrarrápida | Sin servidor, sin metadatos ni persistencia gestionada: hay que envolverlo todo |
| Weaviate / Milvus | Funciones avanzadas e híbridas | Mucho más peso operativo para este caso |
| Búsqueda por palabras clave (Postgres FTS) | Cero infraestructura | No captura sinónimos ni paráfrasis: peor *retrieval* para la memoria de agentes |

## `D-17` · Metabase **y** Superset (dos capas de BI)

| Campo | Detalle |
|---|---|
| **Decisión** | Metabase para *self-service* y Superset para dashboards gobernados, ambos sobre los marts de ClickHouse |
| **Contexto** | Dos públicos: analistas de negocio que exploran sin SQL y perfiles técnicos que necesitan control fino y alertas |
| **Por qué** | Metabase se explica solo y da valor en la primera hora; Superset ofrece SQL Lab, *datasets* versionables, permisos por rol y CLI de importación (útil para automatizar dashboards desde el agente `bi_viz`); mantener ambos cubre las dos necesidades sin elegir por el usuario |
| **Cuándo NO** | Mantener dos herramientas duplica catálogo, permisos y formación: si el equipo es pequeño o hay que certificar KPIs en un solo sitio, sobra una. Ninguna de las dos sirve para métricas de infraestructura en tiempo real (eso es Grafana) |
| **Señal de migración** | Divergencia de definiciones de KPI entre herramientas, o exigencia de gobierno corporativo (entonces Looker/Power BI) |
| **Reversibilidad** | **Media**: los dashboards se reexportan, pero el catálogo y los permisos se rehacen |

| Alternativa | Pros | Contras |
|---|---|---|
| Solo Metabase | Una herramienta, curva mínima | Menos control de permisos, alertas y SQL avanzado |
| Solo Superset | Gobierno, SQL Lab, CLI | Más friccion para el analista de negocio; el primer uso es más lento |
| Grafana | Excelente para series temporales y *alerting* | Orientado a operación, no a modelado dimensional de negocio |
| Looker / Power BI | Gobierno y capa semántica madura | Licencias por usuario y dependencia de proveedor |
| Streamlit / Dash | Libertad total para apps a medida | Cada dashboard es software que hay que mantener y testear |

## `D-18` · Contratos en YAML y metadata de agentes en PostgreSQL/JSONB

| Campo | Detalle |
|---|---|
| **Decisión** | Contratos legibles en `infra/contracts/marts.yml` + estado de runs en `datalab_meta` (tablas con columnas `JSONB`) |
| **Contexto** | Los contratos los revisan personas en un *pull request*; el estado de los runs lo consultan agentes y DAGs en caliente |
| **Por qué** | El YAML versionado en Git es *reviewable* y diffeable, y `qa/contract_check.py` lo ejecuta contra el DW; el JSONB en PostgreSQL permite evolucionar el esquema de `handoffs`/`metrics` sin migraciones y consultar por clave con índices; separar ambos formatos da lo mejor de cada uno (legibilidad vs. consulta) |
| **Cuándo NO** | Contratos que deben validarse en el momento de la escritura (ahí conviene `dbt contracts` nativos o JSON Schema en el productor); estado de runs con altísima frecuencia de escritura (mejor un *event store* dedicado) |
| **Señal de migración** | Los contratos dejan de ser revisados por humanos (entonces automatizar con esquemas) o el volumen de `session_events` crece sin control |
| **Reversibilidad** | **Baja**: se añaden claves sin migración; los contratos son texto plano |

| Alternativa | Pros | Contras |
|---|---|---|
| `dbt contracts` nativos | Validación en el propio `dbt build` | Atado al modelo dbt; no cubre KPIs ni tablas de *scoring* |
| Great Expectations / `pandera` | Suite de validaciones muy rica | Más pesado de configurar y de leer; solapamiento con los tests de dbt |
| OpenLineage + Marquez | Linaje estándar y UI propia | Servicio extra; hoy el linaje se cubre con `manifest.json` |
| Avro / Protobuf | Esquemas binarios estrictos y compatibilidad garantizada | Ilegibles para negocio; friccion en revisiones |
| Tablas relacionales puras (sin JSONB) | Esquema estricto y tipos | Cada nueva métrica obliga a migración; peor para datos heterogéneos de agentes |

## Navegación

| Documento | Contenido |
|---|---|
| [README.md](README.md) | Índice de las 18 decisiones, criterios y disparadores |
| [storage-and-runtime.md](storage-and-runtime.md) | `D-01`…`D-07`: almacenamiento y runtime |
| [orchestration-and-transform.md](orchestration-and-transform.md) | `D-08`…`D-12`: Airflow, dbt e ingesta |
| [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) | Cómo se usan MLflow y los contratos en la práctica |
| [memory-persistence.md](../memory/memory-persistence.md) | DDL del metadata store en PostgreSQL |
