# Docker Setup — Especificación del Stack Local

> Módulo de infraestructura del [README.md](../../README.md). Detalla cada servicio, puerto, volumen,
> variable de entorno y *healthcheck* del entorno, más los comandos de operación diaria.
> Definición ejecutable: [docker-compose.yml](../../docker-compose.yml) · Plantilla: [.env.example](../../.env.example).
> Consumo de estos servicios: [data-pipeline.md](../architecture/data-pipeline.md).

## 1. Requisitos previos

| Requisito | Mínimo | Recomendado |
|---|---|---|
| Docker Engine | 24.x | 26.x |
| Docker Compose | v2.20 (`docker compose`) | v2.29 |
| RAM asignada | 8 GB | 16 GB |
| Disco libre | 20 GB | 60 GB (SSD) |
| SO | Linux / WSL2 / macOS (Apple Silicon OK) | WSL2 con Docker Desktop y los `ulimits` de ClickHouse aplicados por Compose |

En Windows: usar WSL2 con los repositorios dentro del sistema de archivos Linux (`\\wsl$`) para evitar
penalizaciones de I/O y problemas de permisos en los volúmenes de Airflow.

## 2. Servicios, puertos y volúmenes

| Servicio | Contenedor | Imagen | Puerto host → contenedor | Volumen | Healthcheck |
|---|---|---|---|---|---|
| PostgreSQL OLTP | `oltp-postgres` | `postgres:16-alpine` | 5432 → 5432 | `pgdata` | `pg_isready -U ${POSTGRES_USER}` |
| MinIO | `minio` | `minio/minio:RELEASE.2024-06-13T22-53-53Z` | 9000/9001 → 9000/9001 | `minio_data` | `mc ready local` |
| ClickHouse | `clickhouse` | `clickhouse/clickhouse-server:24.3` | 8123 → 8123, 9100 → 9000 | `clickhouse_data` | `wget --spider -q localhost:8123/ping` |
| Airflow | `airflow` | build de `infra/airflow` (base `apache/airflow:2.9.3-python3.11`) | 8080 → 8080 | `airflow_logs` | `curl -fsS http://localhost:8080/health` |
| dbt | `dbt` (perfil `transform`) | build local de `infra/dbt` | — | `dbt_artifacts` | `dbt build` exit 0 |
| MLflow | `mlflow` | build de `infra/mlflow` (base `ghcr.io/mlflow/mlflow:v2.14.1`) | 5000 → 5000 | `mlflow_artifacts` | `python -c urlopen('/health')` |
| JupyterLab | `jupyter` | `quay.io/jupyter/pyspark-notebook:2024-06-01` | 8888 → 8888 | `./infra/jupyter/work` (bind) | `python -c urlopen('/api/status')` |
| Metabase | `metabase` | `metabase/metabase:v0.50.13` | 3000 → 3000 | `metabase_data` | Sonda TCP `:3000` |
| Superset | `superset` | `apache/superset:3.1.3` | 8088 → 8088 | `superset_data` | Sonda TCP `:8088` |
| Qdrant | `qdrant` | `qdrant/qdrant:v1.9.2` | 6333 → 6333 | `qdrant_data` | Sonda TCP `:6333` |

Además existe el *one-shot* `minio-init` (`minio/mc`), que crea los buckets y termina; no cuenta como servicio
permanente. Los nueve servicios permanentes declaran `healthcheck` con `interval: 15s`, `timeout: 5s`,
`retries: 5` y `start_period` diferenciado (ClickHouse, Airflow y el *front-end* de BI: 60 s; el resto: 20–30 s);
`dbt` es efímero (perfil `transform`) y se valida con `dbt build` exit 0, no con sonda de puerto.

## 3. Estructura del repositorio

```text
deploy-arch-datascience/
├── README.md              AGENTS.md              MEMORY.md
├── docker-compose.yml     .env.example
├── docs/
│   ├── architecture/data-pipeline.md
│   ├── infrastructure/docker-setup.md
│   ├── agents/orchestration-rules.md
│   ├── agents/specialists-deep-dive.md
│   ├── mlops/mlflow-dbt-pipeline.md
│   └── memory/memory-persistence.md
└── infra/
    ├── postgres/init/{01_databases,02_oltp_schema,03_oltp_seed}.sql   # bases, OLTP y semilla
    ├── minio/                                # los buckets se crean con el one-shot `minio-init`
    ├── clickhouse/init/01_marts.sql        # base `marts` y usuario de dbt
    ├── airflow/{Dockerfile,requirements.txt,dags,plugins}/  # DAGs ingest_*, transform_*, train_*
    ├── dbt/{models,macros,seeds,tests}/    # staging → intermediate → marts
    ├── jupyter/work/01_eda_orders.ipynb    # notebook semilla de EDA (bind mount)
    ├── agents/{catalog.yaml,handoff.schema.json}   contracts/marts.yml
    ├── pipelines/{train_churn,register,score}.py   qa/{contract_check,drift_report,bias_audit}.py
    └── mlflow/Dockerfile                   # mlflow + boto3 + psycopg2-binary
```

## 4. Variables de entorno (`.env`)

| Variable | Propósito | Valor de ejemplo |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Superusuario de la instancia PostgreSQL | `datalab` / `datalab_dev_pwd` |
| `POSTGRES_OLTP_DB` | Base transaccional | `ecommerce_oltp` |
| `POSTGRES_META_DB` | Metadata store de agentes y runs | `datalab_meta` |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | Credenciales S3 locales | `minioadmin` / `minioadmin` |
| `MINIO_BUCKET` | Bucket raíz del lake | `datalake` |
| `CLICKHOUSE_USER` / `CLICKHOUSE_PASSWORD` | Usuario analítico del DW | `dbt` / `dbt_dev_pwd` |
| `AIRFLOW_UID` | UID del host para permisos de logs | `1000` (`id -u`) |
| `AIRFLOW_ADMIN_USER` / `AIRFLOW_ADMIN_PASSWORD` | Acceso a la UI de Airflow | `admin` / `admin` |
| `MLFLOW_TRACKING_URI` | Backend de tracking | `http://mlflow:5000` |
| `MLFLOW_S3_ENDPOINT_URL` | Endpoint S3 para artefactos | `http://minio:9000` |
| `JUPYTER_TOKEN` | Token de acceso a JupyterLab | `datalab` |
| `DBT_PROFILES_DIR` / `DBT_TARGET` | Perfil y destino de dbt | `/usr/app/dbt` / `dev` |

## 5. Fragmentos clave de `docker-compose.yml`

El archivo [docker-compose.yml](../../docker-compose.yml) es la fuente de verdad. Detalles no evidentes:
`oltp-postgres` monta `./infra/postgres/init` como `docker-entrypoint-initdb.d` (crea `datalab_meta` y
`airflow_meta` en el primer arranque) y `minio` publica 9000/9001 con `minio_data:/data`.

```yaml
services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.3
    ports: ["8123:8123", "9100:9000"]
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    ulimits:
      nofile: { soft: 262144, hard: 262144 }
    networks: [datalab_net]

  airflow:
    build: ./infra/airflow      # base apache/airflow:2.9.3-python3.11 + providers y librerías
    image: datalab/airflow:2.9.3
    user: "${AIRFLOW_UID:-50000}:0"
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@oltp-postgres:5432/${POSTGRES_META_DB}
      AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    ports: ["8080:8080"]
    volumes:
      - ./infra/airflow/dags:/opt/airflow/dags
      - ./infra/pipelines:/opt/airflow/pipelines:ro
      - ./infra/dbt:/usr/app/dbt
      - airflow_logs:/opt/airflow/logs
    depends_on:
      oltp-postgres: { condition: service_healthy }
    networks: [datalab_net]
```

## 6. Redes y volúmenes

- **Red**: `datalab_net` (bridge, subred `172.28.0.0/16`). Los servicios se resuelven por **nombre de servicio**
  (`minio:9000`, `clickhouse:8123`, `oltp-postgres:5432`); usar `localhost` dentro de un contenedor es un error frecuente.
- **Volúmenes nombrados**: `pgdata`, `minio_data`, `clickhouse_data`, `mlflow_artifacts`, `airflow_logs`,
  `metabase_data`, `superset_data`, `qdrant_data`. Retención por volumen en [MEMORY.md §6](../../MEMORY.md).
- **Bind mounts versionados en Git**: `./infra/airflow/dags`, `./infra/dbt` (proyecto y modelos),
  `./infra/pipelines`, `./infra/qa`, `./infra/contracts` y `./infra/jupyter/work` (notebooks), para que el
  trabajo del equipo quede auditable y accesible dentro de los contenedores.
- **Puertos expuestos al host**: solo los de la §2; el resto del tráfico es interno a la red.

## 7. Perfiles de arranque

| Perfil | Servicios | Caso de uso |
|---|---|---|
| `core` | postgres, minio, clickhouse | Solo almacenamiento y DW |
| `orchestration` | + airflow | Ejecutar y programar DAGs |
| `transform` | + dbt (efímero) | Construir marts a demanda |
| `ml` | + mlflow, jupyter | Experimentación y *tracking* |
| `bi` | + metabase, superset | Dashboards |
| *(sin perfil)* | Todos | Stack completo |

Todos los servicios llevan `profiles:`; `.env` fija `COMPOSE_PROFILES=core,orchestration,ml,bi`, de modo que
`docker compose up -d` levanta el stack completo. Pasar `--profile` explícito restringe la selección.

```bash
docker compose --profile core --profile ml up -d
docker compose --profile transform run --rm dbt build --select marts
docker compose up -d minio-init          # one-shot de creación de buckets
```

## 8. Operación diaria y troubleshooting

Los comandos del día a día (`ps`, `logs`, `restart`, `psql`, `mc`, `down -v`), el diagnóstico de fallos
consolidado y los *playbooks* de recuperación viven en **[runbook.md](../operations/runbook.md)**.

## 9. Navegación

| Documento | Contenido |
|---|---|
| [data-pipeline.md](../architecture/data-pipeline.md) | Qué se ejecuta sobre estos servicios |
| [memory-persistence.md](../memory/memory-persistence.md) | Volúmenes, backups y retención de metadatos |
| [runbook.md](../operations/runbook.md) | Operación diaria, troubleshooting y playbooks |
| [.env.example](../../.env.example) | Todas las variables con valores de relleno |
| [README.md](../../README.md) | Verificación de servicios por puerto |
| [glossary.md](../glossary.md) | Qué es cada servicio y qué significan sus siglas |
| [decisions/storage-and-runtime.md](../decisions/storage-and-runtime.md) | `D-03`…`D-07`: por qué este lake, este DW y este runtime |
