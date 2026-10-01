"""DAG ``train_churn_model`` — de los marts Gold al modelo registrado y al *scoring*.

Cadena (docs/mlops/mlflow-dbt-pipeline.md §5, AGENTS.md §2.5):

1. ``build_features``  — ``dbt build --select marts.customer_features`` (única fuente de features).
2. ``quality_gate``    — ``dbt test --select tag:critical`` (gate duro de datos; sin reintento lógico).
3. ``train``           — entrena y registra en MLflow (``churn_classifier``).
4. ``register_model``  — promueve a ``Staging``/``Production`` solo si supera ``--min-roc-auc``.
5. ``batch_scoring``   — puntúa las features y publica ``silver/scoring/scoring_dt=...``.
6. ``record_gate``     — inserta el resultado en ``meta.quality_gates`` con ``drift_psi`` y estado;
   si el gate queda ``rechazado`` la tarea falla **después** de persistir el resultado
   (*fail loud*), con ``retries=0`` para no duplicar filas.

Rutas de los scripts: viven en ``infra/pipelines/`` del repositorio y se esperan montados
en el contenedor Airflow como ``/opt/airflow/pipelines/``; por eso los comandos invocan
``python /opt/airflow/pipelines/<script>.py``. El proyecto dbt está en ``/usr/app/dbt``
(``infra/dbt`` montado por ``docker-compose.yml``).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

logger = logging.getLogger(__name__)

# ── Configuración por entorno (sin secretos y sin DSN embebidos) ───────────────
DBT_DIR = os.getenv("DBT_PROJECT_DIR", "/usr/app/dbt")
PIPELINES_DIR = os.getenv("PIPELINES_DIR", "/opt/airflow/pipelines")
RUN_RESULTS = os.path.join(DBT_DIR, "target", "run_results.json")
CONN_OLTP = "oltp_postgres"
META_DB = os.getenv("POSTGRES_META_DB", "datalab_meta")
MODELO = "churn_classifier"
DRIFT_UMBRAL = float(os.getenv("DRIFT_PSI_THRESHOLD", "0.2"))

DEFAULT_ARGS = {
    "owner": "ds_mlops",
    "retries": 2,
    "retry_delay": timedelta(seconds=60),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
}


def _resultado_tests() -> tuple[int, int]:
    """Lee ``run_results.json`` de dbt y devuelve ``(tests_total, tests_fallidos)``."""
    if not os.path.exists(RUN_RESULTS):
        logger.warning("No existe %s; se asume 0 tests ejecutados", RUN_RESULTS)
        return 0, 0
    with open(RUN_RESULTS, encoding="utf-8") as fh:
        resultados = json.load(fh).get("results", [])
    fallidos = sum(1 for r in resultados if str(r.get("status", "")).lower() in {"fail", "error"})
    return len(resultados), fallidos


@task(retries=0)
def record_gate(*, run_id: str) -> dict:
    """Persiste el *quality gate* del modelo en ``meta.quality_gates`` (drift + estado)."""
    tests_total, tests_fallidos = _resultado_tests()
    # ``DRIFT_PSI`` lo inyecta governance tras ejecutar ``infra/qa/drift_report.py``;
    # si no está definido, el gate se decide solo con los tests críticos de dbt.
    drift_crudo = os.getenv("DRIFT_PSI")
    drift_psi = float(drift_crudo) if drift_crudo else None
    congelado = drift_psi is not None and drift_psi > DRIFT_UMBRAL
    estado = "rechazado" if (tests_fallidos > 0 or congelado) else "aprobado"

    hook = PostgresHook(postgres_conn_id=CONN_OLTP, schema=META_DB)
    try:
        hook.run(
            """
            INSERT INTO meta.pipeline_runs (run_id, intent, status, current_step, current_agent)
            VALUES (%s, 'science', 'en_ejecucion', 'train_churn_model', 'ds_mlops')
            ON CONFLICT (run_id) DO NOTHING
            """,
            parameters=(run_id,),
        )
        hook.run(
            """
            INSERT INTO meta.quality_gates
                (run_id, scope, status, tests_total, tests_failed, drift_psi, signed_by)
            VALUES (%s, 'model', %s, %s, %s, %s, 'governance')
            """,
            parameters=(run_id, estado, tests_total, tests_fallidos, drift_psi),
        )
    except Exception as exc:
        raise AirflowException(f"[run_id={run_id}] no se pudo registrar el gate: {exc}") from exc

    logger.info(
        "[run_id=%s] quality_gate %s",
        run_id,
        json.dumps({"estado": estado, "tests_total": tests_total, "tests_fallidos": tests_fallidos,
                    "drift_psi": drift_psi, "umbral_psi": DRIFT_UMBRAL}),
    )
    if estado == "rechazado":
        raise AirflowException(
            f"[run_id={run_id}] quality gate RECHAZADO: tests_fallidos={tests_fallidos} "
            f"drift_psi={drift_psi} (umbral {DRIFT_UMBRAL}); el modelo no se publica"
        )
    return {"estado": estado, "tests_total": tests_total, "tests_fallidos": tests_fallidos,
            "drift_psi": drift_psi, "modelo": MODELO}


# ── Definición del DAG ─────────────────────────────────────────────────────────
@dag(
    dag_id="train_churn_model",
    description="Features Gold → entrenamiento → registro en MLflow → scoring batch → gate",
    schedule="0 4 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["mlops", "gold"],
    doc_md=__doc__,
)
def train_churn_model() -> None:
    """Entrena el clasificador de churn y publica el *scoring*, con gate de calidad."""
    build_features = BashOperator(
        task_id="build_features",
        bash_command=f"cd {DBT_DIR} && dbt build --select marts.customer_features --target $DBT_TARGET",
    )
    quality_gate = BashOperator(
        task_id="quality_gate",
        bash_command=f"cd {DBT_DIR} && dbt test --select tag:critical",
    )
    train = BashOperator(
        task_id="train",
        bash_command=f"python {PIPELINES_DIR}/train_churn.py --run-id {{{{ run_id }}}}",
    )
    register_model = BashOperator(
        task_id="register_model",
        # La etapa destino la decide el default de register.py (--stage); el umbral es el gate.
        bash_command=f"python {PIPELINES_DIR}/register.py --run-id {{{{ run_id }}}} --min-roc-auc 0.72",
    )
    batch_scoring = BashOperator(
        task_id="batch_scoring",
        bash_command=f"python {PIPELINES_DIR}/score.py --model {MODELO} --stage Production",
    )

    # ``run_id`` se pasa explícito y templateado para que la firma no dependa del contexto.
    build_features >> quality_gate >> train >> register_model >> batch_scoring >> record_gate(
        run_id="{{ run_id }}"
    )


train_churn_model()
