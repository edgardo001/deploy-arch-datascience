# Decisiones `D-01`…`D-07` — Datos, Almacenamiento y Runtime

> Módulo de [decisiones](README.md). Cubre la fuente transaccional, el Data Lake, el motor analítico y el
> runtime que los empaqueta. Siglas: [glossary.md](../glossary.md) · Materialización: [docker-setup.md](../infrastructure/docker-setup.md).

## `D-01` · PostgreSQL como fuente transaccional (OLTP)

| Campo | Detalle |
|---|---|
| **Decisión** | PostgreSQL 16 como base operativa del e-commerce simulado |
| **Contexto** | Se necesita un OLTP realista (transacciones, FK, `CHECK`, `updated_at` fiable) que quepa en un contenedor y sirva de origen a la extracción incremental |
| **Por qué** | SQL completo + JSONB; misma imagen cubre OLTP, metadata store y *backend* de Airflow/MLflow; `\gexec` y `ON CONFLICT` permiten un bootstrap idempotente; es el OLTP dominante en pymes y startups |
| **Cuándo NO** | Escritura distribuida multi-región o >50 k TPS; dominio documental con esquema cambiante; analítica pesada *in-situ* (para eso está el DW) |
| **Señal de migración** | Necesidad de particionado nativo por rango a escala de TB, replicación multi-maestro o *sharding* |
| **Reversibilidad** | **Alta**: el pipeline solo usa SQL estándar y dbt no depende del motor |

| Alternativa | Pros | Contras |
|---|---|---|
| MySQL / MariaDB | Muy extendido, replicación sencilla | Tipos y SQL más pobres (sin JSONB, sin `\gexec`); menos funciones analíticas |
| MongoDB | Esquema flexible, escala horizontal | Sin FK ni *joins* nativos; la extracción tabular incremental se complica |
| SQL Server | Ecosistema corporativo y BI integrado | Licencia y peso; rompe el stack 100 % open source |
| SQLite | Cero operación | Sin concurrencia real ni roles; no sirve como OLTP compartido |

## `D-02` · Una instancia PostgreSQL con 3 bases (no 3 instancias)

| Campo | Detalle |
|---|---|
| **Decisión** | `ecommerce_oltp`, `datalab_meta` y `airflow_meta` conviven en `oltp-postgres` |
| **Contexto** | Entorno local de pruebas con RAM limitada y un solo operador |
| **Por qué** | Ahorra ~300 MB de RAM y tres healthchecks; un único `pgdata` simplifica *backup* y `down -v`; el aislamiento se logra por base y por usuario, no por proceso |
| **Cuándo NO** | Producción con distintas criticidades, ventanas de mantenimiento o requisitos de cifrado por dominio; si un fallo de OLTP no debe tumbar la metadata de Airflow |
| **Señal de migración** | El OLTP entra en mantenimiento y el orquestador se queda sin metadata; o se exige *compliance* separado por base |
| **Reversibilidad** | **Alta**: cambiar el DSN en `.env` y en las conexiones de Airflow |

| Alternativa | Pros | Contras |
|---|---|---|
| 3 contenedores Postgres | Aislamiento y *blast radius* mínimo | +3× RAM, más puertos, más *backups* que coordinar |
| Metadata de Airflow en SQLite | Cero configuración | No soporta `LocalExecutor` con paralelismo real |
| Todo en una sola base | Máxima simplicidad | Mezcla OLTP y metadata: riesgo de permisos y de bloqueos cruzados |

## `D-03` · RustFS como Data Lake compatible con S3 (antes MinIO)

| Campo | Detalle |
|---|---|
| **Decisión** | RustFS 1.0 (`s3://datalake`) para Bronze, Silver/Gold Parquet y artefactos de MLflow |
| **Contexto** | Se quiere ensayar el patrón S3 + Parquet sin coste de nube ni credenciales reales, solo con licencias permisivas |
| **Por qué** | API S3 real (el mismo `boto3`, el mismo `s3()` de ClickHouse y el mismo *artifact root* de MLflow que en producción); ligero, con consola web; la ruta `s3://…` es portabilidad pura; **Apache-2.0**, sin copyleft |
| **Cuándo NO** | Cuando se exijan 11 nueves de durabilidad, replicación multi-región, *versioning* con *object lock* o auditoría de acceso; o si el volumen supera el disco local disponible |
| **Señal de migración** | Necesidad de durabilidad/geo-redundancia o de compartir el lake con otros equipos |
| **Reversibilidad** | **Alta**: cambiar `endpoint_url` y credenciales; las rutas `s3://` no cambian |
| **Historial** | Hasta oct-2026 fue MinIO; se migró por `TD-01` (licencia AGPLv3 + imágenes eliminadas de Docker Hub). Se conserva el nombre de servicio `minio` para no tocar endpoints |

| Alternativa | Pros | Contras |
|---|---|---|
| AWS S3 real | Durabilidad y servicios asociados | Coste, latencia y dependencia de credenciales/red |
| LocalStack | Emula muchos servicios AWS, no solo S3 | Más pesado y con más superficie de emulación imperfecta |
| SeaweedFS / Ceph | Escala y control total | Operación compleja para un entorno de estudio |
| Sistema de archivos plano | Cero dependencias | Se pierde la semántica de objetos, el particionado y el acceso por API |

## `D-04` · Parquet particionado (`dt=`) como formato de Bronze

| Campo | Detalle |
|---|---|
| **Decisión** | Parquet con compresión `snappy` y partición Hive `dt=YYYY-MM-DD/part-000.parquet` |
| **Contexto** | El lake es la fuente de dbt y será leído con la función `s3()` de ClickHouse |
| **Por qué** | Columnar y comprimido (10× menos que CSV); conserva tipos; `s3()` lo lee directo sin *glue*; la partición por día da idempotencia (*overwrite* de una partición) y poda de lectura; es el formato por defecto del ecosistema |
| **Cuándo NO** | Escrituras de fila suelta o *streaming* continuo; necesidad de MERGE/UPDATE sobre el lake o de *time travel*; datos muy pequeños (cientos de filas) donde el CSV es más simple |
| **Señal de migración** | Aparecen borrados/actualizaciones retroactivas que obligan a reescribir particiones enteras, o exigencias de ACID sobre el lake |
| **Reversibilidad** | **Media**: Bronze es inmutable; cambiar de formato implica reprocesar Silver/Gold |

| Alternativa | Pros | Contras |
|---|---|---|
| CSV / JSON | Legibles y universales | Sin tipos, 5-10× más grandes, sin estadísticas de columna |
| Avro / ORC | Excelente para *streaming* / Hive | Menos soporte directo en `s3()` y en herramientas Python |
| Delta Lake / Iceberg / Hudi | ACID, MERGE, *time travel*, evolución de esquema | Añade motor y catálogo: mucho peso para un entorno local |
| Tablas de staging en el DW | Consultas inmediatas | Duplica almacenamiento y rompe la separación lake/warehouse |

## `D-05` · ClickHouse como Data Warehouse OLAP

| Campo | Detalle |
|---|---|
| **Decisión** | ClickHouse como motor de los marts `dim_*`/`fct_*` y de `customer_features` |
| **Contexto** | Modelo en estrella servido a BI y a *feature engineering*, con dbt como capa de transformación |
| **Por qué** | Motor columnar con agregaciones muy rápidas sobre millones de filas; lee S3/Parquet sin cargar en tablas intermedias (`s3()`); dbt-clickhouse maduro; permite `MATERIALIZED VIEW` y motores incrementales; encaja con Metabase/Superset por JDBC |
| **Cuándo NO** | OLTP o muchas actualizaciones fila a fila; `JOIN` de alta cardinalidad (>10⁸) o consultas muy concurrentes con *point lookups*; si el equipo ya domina otro DW y el volumen es pequeño |
| **Señal de migración** | Consultas analíticas que no caben en RAM por `JOIN`s masivos, o necesidad de transacciones distribuidas y *row-level security* fina |
| **Reversibilidad** | **Alta**: los modelos son SQL de dbt; el `profiles.yml` se cambia por `dbt-duckdb` o Postgres |

| Alternativa | Pros | Contras |
|---|---|---|
| PostgreSQL analítico | Un solo motor para todo, transacciones | Se degrada con agregaciones grandes y sin almacenamiento columnar |
| DuckDB | Cero servidor, rapidísimo en local | Monousuario y sin servicio concurrente para BI |
| Snowflake / BigQuery | Escala y gestión nula | Coste, *vendor lock-in* y dependencia de red |
| Spark SQL | Ecosistema *big data* | Cluster, latencia de arranque y mucha operación para estos volúmenes |
| Apache Druid / Doris | Analítica en tiempo real | Complejidad operativa alta para un entorno de estudio |

## `D-06` · DuckDB como réplica analítica *ad-hoc*

| Campo | Detalle |
|---|---|
| **Decisión** | Salida `duckdb` opcional en el perfil de dbt, para analítica local sin servidor |
| **Contexto** | Científicos de datos que quieren consultar sin depender del contenedor de ClickHouse |
| **Por qué** | Un solo archivo, cero operación, SQL analítico completo y lectura directa de Parquet (`read_parquet`); mismo dialecto dbt, así que los modelos se reutilizan |
| **Cuándo NO** | Uso concurrente por varias personas o servicios; datasets que no quepan en disco/RAM local; cuando se necesita la misma tabla servida a BI |
| **Señal de migración** | Varios usuarios consultando a la vez o necesidad de actualización continua |
| **Reversibilidad** | **Alta**: es un *output* alternativo del perfil, no una dependencia |

| Alternativa | Pros | Contras |
|---|---|---|
| SQLite | Universal y embebido | Sin motor columnar ni funciones analíticas modernas |
| Solo ClickHouse | Una única fuente de verdad | Obliga a tener el contenedor levantado para explorar |
| pandas puro | Cero instalación | Se agota la memoria con unos pocos cientos de MB |

## `D-07` · Docker Compose como runtime local

| Campo | Detalle |
|---|---|
| **Decisión** | Docker Compose v2 con 10 servicios, perfiles y red `datalab_net` |
| **Contexto** | Un entorno reproducible en una laptop, para estudio y pruebas de integración |
| **Por qué** | Un comando levanta el stack completo; los perfiles (`core`, `orchestration`, `ml`, `bi`, `transform`) permiten trabajar por partes; imágenes oficiales sin instalación nativa; volumenes y healthchecks declaran el estado; es lo que usa la mayoría de repos de ejemplo del sector |
| **Cuándo NO** | Alta disponibilidad, multiusuario, autoescalado, secretos gestionados o despliegues frecuentes; tampoco si hay más de ~10 servicios o despliegue multi-nodo |
| **Señal de migración** | Se necesita réplica de servicios, *rolling update*, gestión de secretos o entorno compartido por varios equipos |
| **Reversibilidad** | **Media**: los Dockerfile y las imágenes son portables a k3s/Kubernetes, pero los volúmenes y perfiles hay que reescribirlos como manifiestos |

| Alternativa | Pros | Contras |
|---|---|---|
| Kubernetes / k3s | Escala, auto-reparación, estándar de producción | Sobrecarga enorme para una laptop; *overkill* didáctico |
| Podman + Compose | Sin demonio, *rootless* | Compatibilidad desigual con `depends_on`/healthchecks |
| Instalación nativa (apt/pip) | Rendimiento máximo | Infierno de dependencias y de versiones; nada reproducible |
| Nube gestionada (MWAA + RDS + S3) | Paridad total con producción | Coste por hora y credenciales; no es un entorno local |

## 8. Deuda técnica — `TD-01` · Sustituir MinIO (AGPLv3) por S3 compatible con licencia permisiva

| Campo | Detalle |
|---|---|
| **Estado** | ✅ Resuelta (oct-2026): migrado a RustFS 1.0 en `docker-compose.yml` |
| **Deuda** | MinIO Community es [AGPLv3](https://github.com/minio/minio/blob/master/LICENSE) (copyleft restrictivo): quien lo modifique y lo ofrezca como servicio de red debe publicar su código. Además pasó a distribución *source-only* y sus imágenes `minio/minio` / `minio/mc` fueron eliminadas de Docker Hub (sep-2026), lo que rompió `docker compose pull` en este repo |
| **Política objetivo** | Solo licencias permisivas: Apache-2.0, MIT, BSD (o equivalentes como PostgreSQL License). Sin copyleft (sin AGPL/GPL) en el stack |
| **Candidatas** | [RustFS](https://github.com/rustfs/rustfs) (Apache-2.0, S3-compatible, migración *in-place* desde MinIO, v1.0 GA sep-2026 — favorita) · [SeaweedFS](https://github.com/seaweedfs/seaweedfs) (Apache-2.0, alternativa madura) · [lakeFS](https://github.com/treeverse/lakeFS) (Apache-2.0, si se necesita versionado). Descartado [Garage](https://garagehq.deuxfleurs.fr/): es AGPLv3, no cumple la política |
| **Plan** | *Spike* de compatibilidad (boto3, `s3()` de ClickHouse, *artifact root* de MLflow, consola, CLI `mc`→equivalente) y luego cambio de imagen en `docker-compose.yml` + `docker-setup.md` + glosario §8 |
| **DoD** | Ingesta, `dbt build`, tracking de MLflow y consola S3 verificados contra el sustituto; `docker compose up -d` en frío en verde; sin referencias a imágenes MinIO |
| **Cierre** | Servicio `minio` = `rustfs/rustfs:1.0.0`, init con `amazon/aws-cli`, healthcheck sobre `/health` + consola; servicio `minio` conservado como nombre para no tocar endpoints |
| **Observación** | Metabase Community también es AGPLv3; queda fuera de esta deuda y se evaluará aparte (ver `D-17`) |

## Navegación

| Documento | Contenido |
|---|---|
| [README.md](README.md) | Índice de las 18 decisiones, criterios y disparadores |
| [orchestration-and-transform.md](orchestration-and-transform.md) | `D-08`…`D-12`: Airflow, dbt e ingesta |
| [ml-bi-and-memory.md](ml-bi-and-memory.md) | `D-13`…`D-18`: MLOps, BI y memoria |
| [data-pipeline.md](../architecture/data-pipeline.md) | Cómo encajan estas piezas en el viaje del dato |
