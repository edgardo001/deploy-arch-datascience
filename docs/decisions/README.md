# Decisiones de Herramientas (ADR) — Índice, Criterios y Plantilla

> Registro de **por qué** se eligió cada pieza del stack, **en qué casos no se recomienda**, qué **alternativas**
> existen con sus pros y contras, y qué señal obliga a revisar la decisión.
> Siglas usadas aquí: [glossary.md](../glossary.md) · Petición que lo originó: [prompt-log.md](../prompts/prompt-log.md) `P-004`.

## 1. Propósito y alcance

1. Toda herramienta del [docker-compose.yml](../../docker-compose.yml) tiene una decisión `D-00N` con su justificación.
2. Una decisión se documenta **una sola vez** y se enlaza desde todos los documentos que la asumen.
3. El registro es honesto: cada decisión declara **cuándo deja de ser buena idea** y su coste de reversión.
4. Se revisa cuando aparece un **disparador** (§5), no por preferencia estética.

## 2. Formato de una decisión

| Campo | Qué responde |
|---|---|
| **Decisión** | Qué se eligió, en una frase |
| **Contexto** | Restricciones reales del entorno (local, sin nube, un equipo, datos de e-commerce) |
| **Por qué** | Razones técnicas y operativas concretas de este repositorio |
| **Cuándo NO** | Escenarios donde esta elección es un error (anti-patrones) |
| **Señal de migración** | Hecho observable que obliga a cambiar de herramienta |
| **Reversibilidad** | Coste e impacto de sustituirla (bajo/medio/alto) |
| **Alternativas** | Tabla con pros y contras frente a lo elegido |

## 3. Criterios de evaluación y peso

| Criterio | Peso | Qué se mide |
|---|---|---|
| Paridad con producción | 25 % | ¿Es la misma herramienta que se usa en empresas reales? |
| Coste local (RAM/disco/CPU) | 20 % | ¿Cabe en una laptop de 16 GB junto al resto del stack? |
| Curva de aprendizaje | 15 % | ¿Un perfil junior puede operarlo en días? |
| Madurez y comunidad | 15 % | Estabilidad, documentación, respuestas ante incidencias |
| Encaje en el pipeline | 15 % | ¿Habla SQL/Parquet/S3 sin glue code? |
| Licencia y portabilidad | 10 % | Open source y salida sin *vendor lock-in* |

## 4. Índice de decisiones

| ID | Decisión | Documento | Reversibilidad |
|---|---|---|---|
| `D-01` | PostgreSQL como fuente transaccional (OLTP) | [storage-and-runtime.md](storage-and-runtime.md) | Alta (coste bajo) |
| `D-02` | Una instancia PostgreSQL con 3 bases y no 3 instancias | [storage-and-runtime.md](storage-and-runtime.md) | Alta |
| `D-03` | MinIO como Data Lake compatible con S3 | [storage-and-runtime.md](storage-and-runtime.md) | Alta |
| `D-04` | Parquet particionado (`dt=`) como formato de Bronze | [storage-and-runtime.md](storage-and-runtime.md) | Media (reescribir Bronze) |
| `D-05` | ClickHouse como Data Warehouse OLAP | [storage-and-runtime.md](storage-and-runtime.md) | Alta (dbt abstrae el SQL) |
| `D-06` | DuckDB como réplica analítica *ad-hoc* | [storage-and-runtime.md](storage-and-runtime.md) | Alta |
| `D-07` | Docker Compose como runtime local | [storage-and-runtime.md](storage-and-runtime.md) | Media |
| `D-08` | Apache Airflow para orquestar | [orchestration-and-transform.md](orchestration-and-transform.md) | Media |
| `D-09` | dbt Core para transformar | [orchestration-and-transform.md](orchestration-and-transform.md) | Media |
| `D-10` | Ingesta incremental por *watermark* (sin CDC) | [orchestration-and-transform.md](orchestration-and-transform.md) | Media |
| `D-11` | Materialización por capa (view/table/incremental) | [orchestration-and-transform.md](orchestration-and-transform.md) | Baja (es config) |
| `D-12` | Imagen Airflow propia construida en local | [orchestration-and-transform.md](orchestration-and-transform.md) | Baja |
| `D-13` | MLflow para *tracking* y registro de modelos | [ml-bi-and-memory.md](ml-bi-and-memory.md) | Media (pierde historial) |
| `D-14` | JupyterLab como entorno de experimentación | [ml-bi-and-memory.md](ml-bi-and-memory.md) | Baja |
| `D-15` | Scikit-Learn/XGBoost en CPU para el *baseline* | [ml-bi-and-memory.md](ml-bi-and-memory.md) | Media |
| `D-16` | Qdrant como base de datos vectorial | [ml-bi-and-memory.md](ml-bi-and-memory.md) | Media |
| `D-17` | Metabase **y** Superset (dos capas de BI) | [ml-bi-and-memory.md](ml-bi-and-memory.md) | Media |
| `D-18` | Contratos en YAML + metadata de agentes en PostgreSQL/JSONB | [ml-bi-and-memory.md](ml-bi-and-memory.md) | Baja |

## 5. Disparadores de revisión

| Disparador | Decisiones afectadas | Acción mínima |
|---|---|---|
| El volumen deja de caber en una laptop (>50 GB o >8 GB RAM por servicio) | `D-03`, `D-05`, `D-07` | Mover a nube gestionada o añadir nodo |
| Aparecen requisitos de alta disponibilidad o multiusuario real | `D-02`, `D-07` | Kubernetes + Postgres gestionado |
| Latencia requerida < 1 minuto (streaming) | `D-08`, `D-10` | Kafka/Flink o CDC con Debezium |
| Necesidad de *time travel*, MERGE masivo o ACID sobre el lake | `D-04` | Migrar Bronze a Iceberg/Delta |
| Más de ~10^8 filas en un hechos o *joins* de alta cardinalidad | `D-05` | Repensar modelo o motor (Snowflake/BigQuery/Spark) |
| Regulación que exija *lineage* auditable y *feature store* | `D-13`, `D-18` | Añadir OpenLineage + Feast |
| El equipo de BI crece y exige gobierno fino de permisos | `D-17` | Consolidar en Superset (o Looker/Power BI) |
| Deriva semántica en la memoria de agentes | `D-16` | Reindexado y evaluación de *retrieval* |

## 6. Cómo añadir una decisión

1. Añadir la fila al índice (§4) con ID correlativo `D-00N` y el archivo que la contiene.
2. Documentarla en el archivo de su dominio con la plantilla de la §2, **incluyendo siempre «Cuándo NO»**.
3. Enlazarla desde los documentos que la asumen y registrar la petición en [prompt-log.md](../prompts/prompt-log.md).
4. Si el archivo supera 180 líneas, se parte por dominio (nunca se comprime la justificación).

## 7. Navegación

| Documento | Contenido |
|---|---|
| [storage-and-runtime.md](storage-and-runtime.md) | `D-01`…`D-07`: datos, almacenamiento y runtime |
| [orchestration-and-transform.md](orchestration-and-transform.md) | `D-08`…`D-12`: orquestación, dbt e ingesta |
| [ml-bi-and-memory.md](ml-bi-and-memory.md) | `D-13`…`D-18`: MLOps, BI, memoria y contratos |
| [glossary.md](../glossary.md) | Siglas de todas las decisiones |
| [docker-setup.md](../infrastructure/docker-setup.md) | Cómo se materializa cada decisión en Compose |
