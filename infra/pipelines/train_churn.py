#!/usr/bin/env python3
"""Entrenamiento del clasificador de churn sobre ``marts.customer_features`` (Gold).

Flujo (docs/mlops/mlflow-dbt-pipeline.md §3):

1. Lee la tabla de *features* desde ClickHouse; los marts Gold son la única fuente admitida
   (evita el *training/serving skew* frente a Bronze o al OLTP).
2. Entrena ``XGBClassifier`` o, si XGBoost no está instalado, ``GradientBoostingClassifier``.
3. Registra el run en MLflow con *tags* (``run_id``, ``dbt_manifest``), parámetros, métricas
   (``roc_auc``, ``pr_auc``, ``brier``), firma de modelo e ``input_example``.
4. Registra el modelo como ``churn_classifier`` e imprime el ``model_uri`` resultante.

Uso:
    python infra/pipelines/train_churn.py --run-id "$RUN_ID" --algo xgboost

Sin secretos en el código: todo se toma de variables de entorno (``CLICKHOUSE_*``,
``MLFLOW_*``, ``MINIO_ROOT_*``) con valores por defecto razonables para la red ``datalab_net``.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys

import pandas as pd

# ── Contrato de features y etiqueta (docs/mlops/mlflow-dbt-pipeline.md §2) ──────
FEATURES_POR_DEFECTO = ["recency_days", "orders_last_30d", "monetary_365d",
                        "avg_ticket", "tickets_support_90d"]
ETIQUETA = "churn_label"
MODELO_REGISTRADO = "churn_classifier"
TABLA_FEATURES = os.getenv("FEATURES_TABLE", "marts.customer_features")
MANIFEST = os.getenv("DBT_MANIFEST_PATH", "/usr/app/dbt/target/manifest.json")
SEMILLA = 42

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("train_churn")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argumentos de línea de comandos del entrenamiento."""
    parser = argparse.ArgumentParser(description="Entrena y registra el modelo de churn en MLflow")
    parser.add_argument("--run-id", default=os.getenv("RUN_ID", ""),
                        help="run_id de Airflow propagado a MLflow (obligatorio para trazabilidad)")
    parser.add_argument("--algo", default="xgboost", choices=["xgboost", "gradient_boosting"],
                        help="algoritmo de boosting a entrenar")
    parser.add_argument("--features", default=",".join(FEATURES_POR_DEFECTO),
                        help="lista de features separadas por coma")
    parser.add_argument("--test-size", type=float, default=0.2,
                        help="proporción del conjunto de test (estratificado)")
    return parser.parse_args(argv)


def ejecutor_clickhouse():
    """Devuelve ``(filas, modo)`` con ``filas(sql) -> list[tuple]``.

    Prefiere ``clickhouse-connect`` (HTTP) y degrada a ``clickhouse-driver`` (nativo) si el primero
    no está instalado; si no hay ninguno, lanza un error explícito en vez de romper en el *import*.
    """
    host, usuario = os.getenv("CLICKHOUSE_HOST", "clickhouse"), os.getenv("CLICKHOUSE_USER", "dbt")
    clave, base = os.getenv("CLICKHOUSE_PASSWORD", ""), os.getenv("CLICKHOUSE_DB", "marts")
    try:
        import clickhouse_connect

        cliente = clickhouse_connect.get_client(
            host=host, port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            username=usuario, password=clave, database=base,
        )
        return lambda sql: [tuple(f) for f in cliente.query(sql).result_rows], "clickhouse-connect"
    except ImportError:
        logger.warning("clickhouse-connect no está instalado; se intenta clickhouse-driver")
    try:
        from clickhouse_driver import Client

        cliente = Client(host=host, port=int(os.getenv("CLICKHOUSE_NATIVE_PORT", "9000")),
                         user=usuario, password=clave, database=base)
        return lambda sql: [tuple(f) for f in cliente.execute(sql)], "clickhouse-driver"
    except ImportError as exc:
        raise RuntimeError(
            "Se requiere 'clickhouse-connect' o 'clickhouse-driver' para leer "
            f"{TABLA_FEATURES}; ninguna está instalada en este entorno"
        ) from exc


def hash_manifest(ruta: str = MANIFEST) -> str:
    """sha256 del ``manifest.json`` de dbt (linaje de las features usadas)."""
    if not os.path.exists(ruta):
        logger.warning("No existe %s; se registra 'sin-manifest' como dbt_manifest", ruta)
        return "sin-manifest"
    with open(ruta, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def leer_features(features: list[str]) -> pd.DataFrame:
    """Lee las features y la etiqueta desde ClickHouse (``marts.customer_features``)."""
    columnas = [*features, ETIQUETA]
    lista = ", ".join(f"`{c}`" for c in columnas)
    filas, modo = ejecutor_clickhouse()
    logger.info("Consultando %s con %s", TABLA_FEATURES, modo)
    df = pd.DataFrame(
        filas(f"SELECT {lista} FROM {TABLA_FEATURES} WHERE `{ETIQUETA}` IS NOT NULL"),
        columns=columnas,
    )
    logger.info("Leídas %s filas de %s (%s features)", len(df), TABLA_FEATURES, len(features))
    if df.empty:
        raise RuntimeError(f"{TABLA_FEATURES} no devolvió filas: ejecuta 'dbt build --select marts' antes")
    return df


def construir_modelo(algo: str, desbalance: float) -> tuple[object, dict, str]:
    """Devuelve ``(estimador, params, nombre_algo)`` degradando a sklearn si falta XGBoost."""
    if algo == "xgboost":
        try:
            from xgboost import XGBClassifier

            params = {"n_estimators": 400, "max_depth": 5, "learning_rate": 0.08,
                      "scale_pos_weight": round(desbalance, 4), "subsample": 0.9,
                      "random_state": SEMILLA, "eval_metric": "logloss"}
            return XGBClassifier(**params), params, "xgboost"
        except ImportError:
            logger.warning("xgboost no está instalado; se degrada a GradientBoostingClassifier")

    from sklearn.ensemble import GradientBoostingClassifier

    params = {"n_estimators": 300, "max_depth": 3, "learning_rate": 0.05, "random_state": SEMILLA}
    return GradientBoostingClassifier(**params), params, "gradient_boosting"

def preparar_mlflow() -> None:
    """Configura tracking y artefactos en MinIO (credenciales solo por entorno)."""
    import mlflow

    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000"))
    os.environ.setdefault("AWS_ACCESS_KEY_ID", os.getenv("MINIO_ROOT_USER", ""))
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", os.getenv("MINIO_ROOT_PASSWORD", ""))
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", "churn_prediction"))


def main(argv: list[str] | None = None) -> int:
    """Entrena, evalúa, registra el modelo y devuelve el código de salida del proceso."""
    args = parse_args(argv)
    if not args.run_id:
        logger.error("Falta --run-id (o la variable RUN_ID): sin run_id no hay trazabilidad")
        return 2

    features = [f.strip() for f in args.features.split(",") if f.strip()]
    df = leer_features(features)

    import mlflow
    import mlflow.sklearn
    from mlflow.models import infer_signature
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    from sklearn.model_selection import train_test_split

    X, y = df[features], df[ETIQUETA].astype(int)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=args.test_size, stratify=y, random_state=SEMILLA
    )
    negativos, positivos = int((y_tr == 0).sum()), max(int((y_tr == 1).sum()), 1)
    modelo, params, algoritmo = construir_modelo(args.algo, negativos / positivos)

    preparar_mlflow()
    with mlflow.start_run(run_name=f"churn_{args.run_id}") as run:
        mlflow.set_tags({"run_id": args.run_id, "dbt_manifest": hash_manifest(),
                         "feature_table": TABLA_FEATURES, "algo": algoritmo,
                         "budget_seconds": os.getenv("RUN_BUDGET_SECONDS", "1800")})
        mlflow.log_params({**params, "test_size": args.test_size, "n_rows": len(df),
                           "n_features": len(features), "features": ",".join(features)})
        modelo.fit(X_tr, y_tr)
        proba = modelo.predict_proba(X_te)[:, 1]
        metricas = {
            "roc_auc": float(roc_auc_score(y_te, proba)),
            "pr_auc": float(average_precision_score(y_te, proba)),
            "brier": float(brier_score_loss(y_te, proba)),
        }
        mlflow.log_metrics(metricas)

        firma = infer_signature(X_tr, modelo.predict_proba(X_tr)[:, 1])
        mlflow.sklearn.log_model(
            modelo,
            "model",
            signature=firma,
            input_example=X_tr.head(5),
            registered_model_name=MODELO_REGISTRADO,
        )
        if os.path.exists(MANIFEST):
            mlflow.log_artifact(MANIFEST)
        model_uri = f"runs:/{run.info.run_id}/model"

    logger.info("Entrenamiento %s OK run_id=%s métricas=%s", algoritmo, args.run_id, metricas)
    print(f"model_uri={model_uri}")
    print(f"metrics={metricas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
