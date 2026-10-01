#!/usr/bin/env python3
"""Promoción auditable del modelo ``churn_classifier`` en el MLflow Model Registry.

Reglas (docs/mlops/mlflow-dbt-pipeline.md §4):

* Solo se promueve una versión cuyo **run supere el umbral** ``--min-roc-auc``.
* Si el umbral no se cumple, **no se toca el registro**: se imprime la causa, se conserva
  la versión anterior en ``Production`` y el proceso sale con código ≠ 0.
* La versión promovida debe pertenecer al ``--run-id`` indicado (trazabilidad Airflow → MLflow).

Uso:
    python infra/pipelines/register.py --run-id "$RUN_ID" --min-roc-auc 0.72 --stage Production

Etapas admitidas: ``Staging`` (promoción técnica previa) y ``Production`` (default, porque el
``batch_scoring`` del DAG ``train_churn_model`` sirve desde ``Production``). Sin secretos: todo
por variables de entorno.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

MODELO_REGISTRADO = "churn_classifier"
ETAPAS_VALIDAS = ("Staging", "Production")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("register_model")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argumentos de la promoción: run, umbral y etapa destino."""
    parser = argparse.ArgumentParser(description="Promueve churn_classifier si supera el umbral")
    parser.add_argument("--run-id", default=os.getenv("RUN_ID", ""),
                        help="run_id de Airflow que entrenó el modelo (obligatorio)")
    parser.add_argument("--min-roc-auc", type=float, default=0.72,
                        help="ROC-AUC mínimo exigido al run para promover")
    parser.add_argument("--stage", default="Production", choices=list(ETAPAS_VALIDAS),
                        help="etapa destino: Staging o Production")
    return parser.parse_args(argv)


def _cliente_mlflow():
    """Cliente del Model Registry apuntando a ``MLFLOW_TRACKING_URI``."""
    from mlflow.tracking import MlflowClient

    return MlflowClient(tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))


def _ultima_version(cliente) -> object:
    """Devuelve la versión más alta registrada de ``churn_classifier``."""
    versiones = cliente.search_model_versions(f"name='{MODELO_REGISTRADO}'")
    if not versiones:
        raise LookupError(f"No hay versiones registradas de {MODELO_REGISTRADO}")
    return max(versiones, key=lambda v: int(v.version))


def _promover(cliente, version: str, etapa: str) -> None:
    """Transiciona la versión a la etapa pedida (con *fallback* a alias si la API cambió)."""
    try:
        cliente.transition_model_version_stage(
            name=MODELO_REGISTRADO, version=version, stage=etapa, archive_existing_versions=False
        )
    except AttributeError:  # MLflow ≥ 3 eliminó las etapas: se usa un alias equivalente
        logger.warning("transition_model_version_stage no disponible; se usa un alias '%s'", etapa)
        cliente.set_registered_model_alias(MODELO_REGISTRADO, etapa.lower(), version)


def main(argv: list[str] | None = None) -> int:
    """Comprueba el umbral y promueve; devuelve 0 si promueve, 1 si no supera, 2 si hay error."""
    args = parse_args(argv)
    if not args.run_id:
        logger.error("Falta --run-id (o RUN_ID): sin run_id no se puede auditar la promoción")
        return 2

    try:
        cliente = _cliente_mlflow()
        run = cliente.get_run(args.run_id)
        ultima = _ultima_version(cliente)
    except Exception as exc:
        logger.error("No se pudo consultar MLflow (%s): %s", os.getenv("MLFLOW_TRACKING_URI"), exc)
        return 2

    roc_auc = run.data.metrics.get("roc_auc")
    if roc_auc is None:
        logger.error("El run %s no tiene la métrica 'roc_auc' registrada", args.run_id)
        return 2

    logger.info(
        "Candidato: run_id=%s roc_auc=%.4f | versión=%s (run de la versión=%s) | umbral=%.4f",
        args.run_id, roc_auc, ultima.version, ultima.run_id, args.min_roc_auc,
    )
    if ultima.run_id != args.run_id:
        logger.warning(
            "La última versión (%s) pertenece al run %s y no al run solicitado %s; "
            "se promueve igualmente la última versión registrada",
            ultima.version, ultima.run_id, args.run_id,
        )
    if roc_auc < args.min_roc_auc:
        logger.error(
            "RECHAZADO: roc_auc=%.4f < --min-roc-auc=%.4f. Se conserva la versión anterior en "
            "'Production' y no se modifica el registro.",
            roc_auc, args.min_roc_auc,
        )
        return 1

    try:
        _promover(cliente, ultima.version, args.stage)
    except Exception as exc:
        logger.error("Fallo la transición de la versión %s a %s: %s", ultima.version, args.stage, exc)
        return 2

    print(f"model_uri=models:/{MODELO_REGISTRADO}/{args.stage}")
    print(f"version={ultima.version} stage={args.stage} roc_auc={roc_auc:.4f}")
    logger.info("Versión %s promovida a %s (roc_auc=%.4f)", ultima.version, args.stage, roc_auc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
