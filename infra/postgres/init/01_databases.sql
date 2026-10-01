-- =====================================================================
-- DataLab Productivo Local — Bootstrap de bases y metadata store
-- Documentos: docs/infrastructure/docker-setup.md (servicios y volúmenes)
--             docs/memory/memory-persistence.md (metadata store, §2 y §6)
-- Script 01 de 03: bases + schema `meta`. Ver 02 (OLTP) y 03 (semilla).
--
-- Se ejecuta UNA sola vez, dentro del entrypoint de `oltp-postgres`
-- (docker-entrypoint-initdb.d). El primer script del directorio siempre
-- corre conectado a POSTGRES_DB = ecommerce_oltp.
--
-- Bases creadas (misma instancia oltp-postgres:5432):
--   ecommerce_oltp  OLTP transaccional (ver 02_oltp_schema.sql)
--   datalab_meta    metadata store de agentes (schema `meta`)
--   airflow_meta    estado de DAGs de Airflow
--
-- Idempotente: CREATE ... IF NOT EXISTS + ON CONFLICT DO NOTHING.
-- Sin secretos hardcodeados: el nombre del rol se inyecta con la variable
-- de psql que publica la imagen postgres (POSTGRES_USER).
-- =====================================================================

\set ON_ERROR_STOP on

-- ─────────────────────────────────────────────────────────────────────
-- 1. Creación idempotente de bases (CREATE DATABASE no admite IF NOT
--    EXISTS en transacción: se usa \gexec con consulta a pg_database).
-- ─────────────────────────────────────────────────────────────────────
SELECT format('CREATE DATABASE %I', d)
FROM (VALUES ('datalab_meta'), ('airflow_meta')) AS t(d)
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = t.d)
\gexec

-- Propiedad explícita del rol configurado (POSTGRES_USER, vía variable psql).
SELECT format('ALTER DATABASE %I OWNER TO %I', d, :'POSTGRES_USER')
FROM (VALUES ('datalab_meta'), ('airflow_meta')) AS t(d)
WHERE EXISTS (SELECT 1 FROM pg_database WHERE datname = t.d)
  AND pg_get_userbyid((SELECT datdba FROM pg_database WHERE datname = t.d)) <> :'POSTGRES_USER'
\gexec

-- ─────────────────────────────────────────────────────────────────────
-- 2. Metadata store de agentes: datalab_meta.meta
--    Esquema espejo EXACTO de docs/memory/memory-persistence.md §2.
--      pipeline_runs     un registro por run del orquestador
--      handoffs          transferencias tipadas entre agentes
--      session_events    decisiones, observaciones, errores y resúmenes
--      quality_gates     firmas de governance (tests, drift PSI, sesgo)
--      ingest_audit      auditoría de ingesta por entidad y partición dt
--      routing_decisions scoring de intención del router
-- ─────────────────────────────────────────────────────────────────────
\connect datalab_meta

CREATE SCHEMA IF NOT EXISTS meta;

CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
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

CREATE TABLE IF NOT EXISTS meta.handoffs (
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

CREATE TABLE IF NOT EXISTS meta.session_events (
    id         BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    run_id     TEXT,
    kind       TEXT NOT NULL,          -- decision | observacion | error | resumen
    payload    JSONB NOT NULL,
    ts         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS meta.quality_gates (
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

CREATE TABLE IF NOT EXISTS meta.ingest_audit (
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

CREATE TABLE IF NOT EXISTS meta.routing_decisions (
    id          BIGSERIAL PRIMARY KEY,
    intent      TEXT NOT NULL,
    agent       TEXT NOT NULL,
    score       NUMERIC(4,3),
    rationale   TEXT,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices de acceso: trazabilidad por run y ventanas de retención por ts
-- (docs/memory/memory-persistence.md §6: purga por ts y por run_id).
CREATE INDEX IF NOT EXISTS idx_handoffs_run_id        ON meta.handoffs (run_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_ts            ON meta.handoffs (ts DESC);
CREATE INDEX IF NOT EXISTS idx_session_events_run_id  ON meta.session_events (run_id);
CREATE INDEX IF NOT EXISTS idx_session_events_ts      ON meta.session_events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_quality_gates_run_id   ON meta.quality_gates (run_id);
CREATE INDEX IF NOT EXISTS idx_quality_gates_ts       ON meta.quality_gates (ts DESC);
CREATE INDEX IF NOT EXISTS idx_ingest_audit_run_id    ON meta.ingest_audit (run_id);
CREATE INDEX IF NOT EXISTS idx_ingest_audit_ts        ON meta.ingest_audit (ts DESC);
CREATE INDEX IF NOT EXISTS idx_routing_decisions_ts   ON meta.routing_decisions (ts DESC);

-- Continúa en 02_oltp_schema.sql (esquema del e-commerce en ecommerce_oltp).
