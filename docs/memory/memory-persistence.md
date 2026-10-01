# Memory Persistence — Metadata Store, Vector DB y Retención

> Módulo de memoria del [MEMORY.md](../../MEMORY.md). Define el **esquema físico** donde los agentes
> persisten estado, linaje y conocimiento reutilizable, y cómo se respalda y purga.
> Quién escribe cada tabla: [orchestration-rules.md](../agents/orchestration-rules.md).

## 1. Topología de almacenamiento

| Almacén | Motor | Host:puerto (interno) | Contenido | Backup |
|---|---|---|---|---|
| `datalab_meta` | PostgreSQL 16 | `oltp-postgres:5432` | Runs, handoffs, quality gates, routing | `pg_dump` diario |
| `airflow_meta` | PostgreSQL 16 | `oltp-postgres:5432` | Estado de DAGs y tareas | `pg_dump` diario |
| `datalab_knowledge` | Qdrant | `qdrant:6333` | Embeddings de docs, model cards, incidentes | Snapshot semanal |
| `mlruns` | MLflow (backend PostgreSQL + artefactos S3) | `mlflow:5000` | Runs, métricas, artefactos, registro de modelos | Réplica a `s3://datalake/mlflow` |
| `dbt_artifacts` | Volumen + MinIO | — | `manifest.json`, `catalog.json`, `run_results.json` | Por commit de Git |

Las tres bases PostgreSQL conviven en una sola instancia local (`ecommerce_oltp`, `datalab_meta`,
`airflow_meta`) para simplificar el entorno de pruebas; en producción se separan por criticidad.

## 2. DDL del metadata store

```sql
CREATE SCHEMA IF NOT EXISTS meta;

CREATE TABLE meta.pipeline_runs (
    run_id        TEXT PRIMARY KEY,
    intent        TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('planificado','en_ejecucion','validado',
                                                  'publicado','fallido','archivado')),
    current_step  TEXT,
    current_agent TEXT,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    budget_s      INTEGER,
    cost_s        INTEGER,
    user_id       TEXT,
    objective     TEXT
);

CREATE TABLE meta.handoffs (
    id           BIGSERIAL PRIMARY KEY,
    run_id       TEXT NOT NULL REFERENCES meta.pipeline_runs(run_id),
    from_agent   TEXT NOT NULL,
    to_agent     TEXT NOT NULL,
    status       TEXT NOT NULL,
    artifacts    JSONB NOT NULL DEFAULT '[]'::jsonb,
    contracts    JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics      JSONB NOT NULL DEFAULT '{}'::jsonb,
    ts           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE meta.session_events (
    id        BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    run_id    TEXT,
    kind      TEXT NOT NULL,          -- decision | observacion | error | resumen
    payload   JSONB NOT NULL,
    ts        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE meta.quality_gates (
    id           BIGSERIAL PRIMARY KEY,
    run_id       TEXT NOT NULL REFERENCES meta.pipeline_runs(run_id),
    scope        TEXT NOT NULL,       -- marts | model | dashboard
    status       TEXT NOT NULL CHECK (status IN ('aprobado','rechazado','pendiente')),
    tests_total  INTEGER,
    tests_failed INTEGER,
    drift_psi    NUMERIC(6,4),
    bias_score   NUMERIC(6,4),
    signed_by    TEXT DEFAULT 'governance',
    ts           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE meta.ingest_audit (
    id         BIGSERIAL PRIMARY KEY,
    run_id     TEXT NOT NULL,
    entity     TEXT NOT NULL,
    dt         DATE NOT NULL,
    rows_read  BIGINT NOT NULL,
    watermark  TIMESTAMPTZ NOT NULL,
    checksum   TEXT,
    ts         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, entity, dt)
);

CREATE TABLE meta.routing_decisions (
    id          BIGSERIAL PRIMARY KEY,
    intent      TEXT NOT NULL,
    agent       TEXT NOT NULL,
    score       NUMERIC(4,3),
    rationale   TEXT,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 3. Colecciones vectoriales (Qdrant)

| Colección | Documentos indexados | Vector | Payload de filtrado |
|---|---|---|---|
| `datalab_docs` | README, AGENTS, MEMORY y módulos `/docs` | 768 d (embedding local) | `path`, `module`, `version` |
| `datalab_models` | Model cards, métricas y supuestos de cada versión | 768 d | `model_name`, `stage`, `run_id` |
| `datalab_incidents` | Postmortems, causa raíz y remediación | 768 d | `severity`, `agent`, `ts` |
| `datalab_kpis` | Definiciones certificadas de KPI y su SQL | 768 d | `domain`, `owner`, `certified` |

```python
# Recuperación antes de actuar (patrón obligatorio de los agentes)
hits = qdrant.search(
    collection_name="datalab_knowledge",
    query_vector=embed(intent + " " + context_summary),
    limit=5,
    query_filter=Filter(must=[FieldCondition(key="module", match=MatchValue(value="mlops"))]),
)
```

## 4. Ciclo de indexado

1. **Trigger**: cierre de run en estado `publicado` o creación de un artefacto de conocimiento.
2. **Chunking**: 800 tokens con 15 % de solape, conservando encabezado de sección y ruta del archivo.
3. **Upsert idempotente**: la clave es `hash(ruta + versión + contenido)`; el mismo contenido no se reindexa.
4. **Invalidación**: al cambiar un documento, los puntos antiguos se marcan `deprecated: true` (no se borran).
5. **Validación**: un test de retrieval comprueba que las 3 preguntas canónicas devuelven la fuente esperada.

## 5. Backup y restauración

```bash
# Metadata store
docker compose exec oltp-postgres pg_dump -U "$POSTGRES_USER" -Fc datalab_meta > backup/meta_$(date +%F).dump
docker compose exec -T oltp-postgres pg_restore -U "$POSTGRES_USER" -d datalab_meta --clean < backup/meta_2026-02-14.dump

# Data Lake (Bronze/Silver/Gold + artefactos MLflow)
docker compose run --rm minio-init mc mirror --overwrite local/datalake /backup/datalake

# Vector DB
curl -X POST http://localhost:6333/snapshots -H 'Content-Type: application/json' \
     -d '{"collection_name": "datalab_knowledge"}'
```

## 6. Retención y purga

| Dato | Retención | Mecanismo de purga |
|---|---|---|
| `session_events` | 30 d | `DELETE ... WHERE ts < now() - interval '30 days'` (job diario) |
| `routing_decisions` | 90 d | Purga programada |
| `ingest_audit` | 365 d | Particionado por mes y `DROP PARTITION` |
| Bronze Parquet | 90 d | Ciclo de vida `mc ilm` sobre la ruta `bronze/` |
| Silver/Gold Parquet | 365 d | Ciclo de vida sobre `silver/`, `gold/` |
| Artefactos MLflow | 730 d | Exportación a almacenamiento frío antes de borrar |
| Embeddings | Reindexado trimestral | Reemplazo por colección nueva y alias swap |

## 7. Seguridad y secretos

- Las credenciales **nunca** se persisten en `datalab_meta`; se referencian por nombre (`secret_ref`).
- Los datos personales solo existen enmascarados a partir de Silver (`email_hash`, `phone_masked`).
- Acceso a Qdrant y PostgreSQL restringido a la red `datalab_net`; puertos de administración no expuestos.
- Toda escritura exige `run_id` + `ts`: sin trazabilidad no hay persistencia.

## 8. Navegación

| Documento | Contenido |
|---|---|
| [MEMORY.md](../../MEMORY.md) | Modelo conceptual corto/largo plazo y estado global |
| [docker-setup.md](../infrastructure/docker-setup.md) | Servicios y volúmenes que respaldan estos almacenes |
| [orchestration-rules.md](../agents/orchestration-rules.md) | Qué agente escribe cada tabla |
| [mlflow-dbt-pipeline.md](../mlops/mlflow-dbt-pipeline.md) | Metadatos de experimentos y promoción de modelos |
| [glossary.md](../glossary.md) | Siglas de persistencia (Vector DB, embedding, DSN, `run_id`) |
