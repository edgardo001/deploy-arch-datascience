"""DAG ``transform_dbt_marts`` — capa analítica dbt: ``staging → intermediate → marts``.

Cadena de ejecución con *quality gate* duro (docs/architecture/data-pipeline.md §3,
AGENTS.md §2.4):

1. ``dbt_deps``          — resuelve paquetes del proyecto.
2. ``dbt_build_staging`` — materializa la capa Silver.
3. ``dbt_build_marts``   — construye ``intermediate`` + ``marts`` (Gold) en ClickHouse.
4. ``dbt_test_critical`` — **quality gate**: ``dbt test --select tag:critical --store-failures``;
   si algún test crítico falla, se bloquea la publicación del linaje y de Gold.
5. ``publish_lineage``   — publica el ``manifest_hash`` (sha256 de ``target/manifest.json``)
   en ``meta.handoffs`` para que ``governance`` audite el linaje del run.

El proyecto dbt vive en ``infra/dbt`` y ``docker-compose.yml`` lo monta en el contenedor
Airflow como ``/usr/app/dbt``; por eso todos los comandos se ejecutan con
``cd /usr/app/dbt &&`` y usan ``$DBT_TARGET`` del entorno.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

logger = logging.getLogger(__name__)

# ── Configuración (rutas del contenedor y conexiones por ``conn_id``) ──────────
DBT_DIR = os.getenv("DBT_PROJECT_DIR", "/usr/app/dbt")
MANIFEST = os.path.join(DBT_DIR, "target", "manifest.json")
CONN_OLTP = "oltp_postgres"
META_DB = os.getenv("POSTGRES_META_DB", "datalab_meta")

DEFAULT_ARGS = {
    "owner": "analytics_engineer",
    "retries": 2,
    "retry_delay": timedelta(seconds=30),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
}


def _hash_manifest() -> tuple[str, int]:
    """Devuelve ``(sha256 del manifest.json, número de nodos)`` del proyecto dbt."""
    if not os.path.exists(MANIFEST):
        raise AirflowException(
            f"No existe {MANIFEST}: ejecuta 'dbt build' antes de publicar el linaje"
        )
    with open(MANIFEST, "rb") as fh:
        crudo = fh.read()
    try:
        manifiesto = json.loads(crudo)
    except json.JSONDecodeError as exc:
        raise AirflowException(f"manifest.json ilegible en {MANIFEST}: {exc}") from exc
    return hashlib.sha256(crudo).hexdigest(), len(manifiesto.get("nodes", {}))


@task(retries=1)
def publish_lineage(*, run_id: str, ds: str) -> dict:
    """Registra el linaje de dbt del run en ``meta.handoffs`` (analytics_engineer → governance)."""
    manifest_hash, nodos = _hash_manifest()
    hook = PostgresHook(postgres_conn_id=CONN_OLTP, schema=META_DB)
    try:
        # El handoff referencia meta.pipeline_runs(run_id): se asegura el run (idempotente).
        hook.run(
            """
            INSERT INTO meta.pipeline_runs (run_id, intent, status, current_step, current_agent)
            VALUES (%s, 'modeling', 'en_ejecucion', 'transform_dbt_marts', 'analytics_engineer')
            ON CONFLICT (run_id) DO NOTHING
            """,
            parameters=(run_id,),
        )
        hook.run(
            """
            INSERT INTO meta.handoffs
                (run_id, from_agent, to_agent, status, artifacts, contracts, metrics)
            VALUES (%s, 'analytics_engineer', 'governance', 'ok', %s::jsonb, %s::jsonb, %s::jsonb)
            """,
            parameters=(
                run_id,
                json.dumps([f"file://{MANIFEST}"]),
                json.dumps({"manifest_hash": manifest_hash, "nodos": nodos}),
                json.dumps({"ds": ds, "dag_id": "transform_dbt_marts"}),
            ),
        )
    except Exception as exc:
        raise AirflowException(f"[run_id={run_id}] no se pudo publicar el linaje: {exc}") from exc
    logger.info("[run_id=%s] linaje publicado: manifest_hash=%s nodos=%s", run_id, manifest_hash, nodos)
    return {"manifest_hash": manifest_hash, "nodos": nodos}


# ── Definición del DAG ─────────────────────────────────────────────────────────
@dag(
    dag_id="transform_dbt_marts",
    description="dbt build staging → intermediate/marts con quality gate crítico y linaje",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["dbt", "gold"],
    doc_md=__doc__,
)
def transform_dbt_marts() -> None:
    """Ejecuta dbt por capas y bloquea la publicación si un test crítico falla."""
    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {DBT_DIR} && dbt deps",
    )
    dbt_build_staging = BashOperator(
        task_id="dbt_build_staging",
        bash_command=f"cd {DBT_DIR} && dbt build --select staging --target $DBT_TARGET",
    )
    dbt_build_marts = BashOperator(
        task_id="dbt_build_marts",
        bash_command=f"cd {DBT_DIR} && dbt build --select intermediate marts --target $DBT_TARGET",
    )
    # Quality gate: sin tests críticos en verde no se publica linaje (ni se certifica Gold).
    dbt_test_critical = BashOperator(
        task_id="dbt_test_critical",
        bash_command=f"cd {DBT_DIR} && dbt test --select tag:critical --store-failures",
    )

    # ``run_id``/``ds`` se pasan explícitos y templateados: ningún parámetro queda sin argumento.
    dbt_deps >> dbt_build_staging >> dbt_build_marts >> dbt_test_critical >> publish_lineage(
        run_id="{{ run_id }}", ds="{{ ds }}"
    )


transform_dbt_marts()
