#!/usr/bin/env python3
"""Scoring batch del modelo ``churn_classifier`` sobre las features Gold.

Flujo (docs/architecture/data-pipeline.md §2, etapa 6):

1. Carga el modelo registrado en MLflow por **etapa** (``Staging``/``Production``).
2. Puntúa ``marts.customer_features`` (nunca Bronze ni el OLTP) enriqueciendo con las columnas
   sensibles de ``marts.dim_customer`` para la auditoría de sesgo.
3. Escribe ``s3://datalake/silver/scoring/scoring_dt=YYYY-MM-DD/scoring.parquet``; la partición se
   sobrescribe, así que el paso es idempotente por ``dt``.
4. Registra el resumen del *scoring* en ``meta.handoffs`` (``ds_mlops`` → ``bi_viz``).

Uso:
    python infra/pipelines/score.py --model churn_classifier --stage Production --dt 2026-02-14

El ``run_id`` se toma de la variable ``RUN_ID`` (la inyecta Airflow) o se deriva del ``dt``.
Sin secretos en el código: todo por variables de entorno.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

FEATURES = ["recency_days", "orders_last_30d", "monetary_365d", "avg_ticket", "tickets_support_90d"]
TABLA_FEATURES = os.getenv("FEATURES_TABLE", "marts.customer_features")
TABLA_CLIENTES = os.getenv("CLIENTES_TABLE", "marts.dim_customer")
BUCKET = os.getenv("MINIO_BUCKET", "datalake")
UMBRAL = float(os.getenv("CHURN_SCORE_THRESHOLD", "0.5"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("score_batch")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Argumentos del scoring: modelo, etapa y partición destino."""
    parser = argparse.ArgumentParser(description="Scoring batch del modelo de churn")
    parser.add_argument("--model", default="churn_classifier", help="nombre del modelo en el Registry")
    parser.add_argument("--stage", default="Production", choices=["Staging", "Production"], help="etapa a servir")
    parser.add_argument("--dt", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="partición scoring_dt")
    return parser.parse_args(argv)


def ejecutor_clickhouse():
    """Devuelve ``(filas, modo)`` con ``filas(sql) -> list[tuple]``.

    Prefiere ``clickhouse-connect`` y degrada a ``clickhouse-driver``; si no hay ninguno, lanza un
    error explícito en vez de romper en el *import*.
    """
    host, usuario = os.getenv("CLICKHOUSE_HOST", "clickhouse"), os.getenv("CLICKHOUSE_USER", "dbt")
    clave, base = os.getenv("CLICKHOUSE_PASSWORD", ""), os.getenv("CLICKHOUSE_DB", "marts")
    try:
        import clickhouse_connect

        cliente = clickhouse_connect.get_client(host=host, port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
                                                username=usuario, password=clave, database=base)
        return lambda sql: [tuple(f) for f in cliente.query(sql).result_rows], "clickhouse-connect"
    except ImportError:
        logger.warning("clickhouse-connect no está instalado; se intenta clickhouse-driver")
    try:
        from clickhouse_driver import Client

        cliente = Client(host=host, port=int(os.getenv("CLICKHOUSE_NATIVE_PORT", "9000")),
                         user=usuario, password=clave, database=base)
        return lambda sql: [tuple(f) for f in cliente.execute(sql)], "clickhouse-driver"
    except ImportError as exc:
        raise RuntimeError("Se requiere 'clickhouse-connect' o 'clickhouse-driver' para leer "
                           f"{TABLA_FEATURES}; ninguna está instalada en este entorno") from exc


def cargar_features() -> pd.DataFrame:
    """Lee features + columnas sensibles (``ANY JOIN`` para preservar la granularidad 1:1)."""
    columnas = ["customer_id", *FEATURES, "gender", "age_band"]
    seleccion = ", ".join(f"f.`{c}`" for c in ["customer_id", *FEATURES])
    filas, modo = ejecutor_clickhouse()
    logger.info("Leyendo features de %s con %s", TABLA_FEATURES, modo)
    df = pd.DataFrame(
        filas(f"SELECT {seleccion}, c.`gender` AS gender, c.`age_band` AS age_band "
              f"FROM {TABLA_FEATURES} AS f "
              f"LEFT ANY JOIN {TABLA_CLIENTES} AS c ON c.`customer_id` = f.`customer_id`"),
        columns=columnas,
    )
    logger.info("Features para scoring: %s filas", len(df))
    if df.empty:
        raise RuntimeError(f"{TABLA_FEATURES} no devolvió filas: no hay nada que puntuar")
    return df


def cargar_modelo(nombre: str, etapa: str) -> tuple[object, str]:
    """Carga el modelo por etapa; usa el *flavor* sklearn y degrada a pyfunc si no aplica."""
    uri = f"models:/{nombre}/{etapa}"
    try:
        import mlflow.sklearn

        modelo = mlflow.sklearn.load_model(uri)
        logger.info("Modelo cargado (flavor sklearn) desde %s", uri)
        return modelo, uri
    except Exception as exc:
        logger.warning("Flavor sklearn no disponible para %s (%s); se intenta pyfunc", uri, exc)
        import mlflow.pyfunc

        return mlflow.pyfunc.load_model(uri), uri


def puntuar(modelo, df: pd.DataFrame) -> pd.DataFrame:
    """Calcula ``churn_score`` (probabilidad) y ``churn_pred`` (etiqueta) por cliente."""
    X = df[FEATURES]
    if hasattr(modelo, "predict_proba"):
        score = np.asarray(modelo.predict_proba(X))[:, 1]
    else:  # pyfunc: la salida puede ser etiqueta o probabilidad según el flavor registrado
        score = np.asarray(modelo.predict(X)).ravel().astype(float)
        logger.warning("El modelo no expone predict_proba; se usa la salida de predict como score")
    resultado = df.copy()
    resultado["churn_score"] = score
    resultado["churn_pred"] = (score >= UMBRAL).astype(int)
    return resultado


def publicar_parquet(salida: pd.DataFrame, dt: str) -> str:
    """Sube el Parquet a ``silver/scoring/scoring_dt=<dt>/scoring.parquet`` y devuelve el URI."""
    import boto3

    clave = f"silver/scoring/scoring_dt={dt}/scoring.parquet"
    buffer = io.BytesIO()
    salida.to_parquet(buffer, index=False, compression="snappy")
    cliente = boto3.client("s3", endpoint_url=os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000"),
                           aws_access_key_id=os.getenv("MINIO_ROOT_USER", ""),
                           aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD", ""))
    cliente.put_object(Bucket=BUCKET, Key=clave, Body=buffer.getvalue())
    logger.info("Scoring publicado: %s filas → s3://%s/%s", len(salida), BUCKET, clave)
    return f"s3://{BUCKET}/{clave}"


def registrar_handoff(run_id: str, dt: str, uri: str, modelo_uri: str, salida: pd.DataFrame) -> None:
    """Registra el resumen del scoring en ``meta.handoffs`` (asegura antes el run referenciado)."""
    import psycopg2

    metricas = {"filas": int(len(salida)), "positivos": int(salida["churn_pred"].sum()),
                "score_medio": round(float(salida["churn_score"].mean()), 6),
                "score_p95": round(float(salida["churn_score"].quantile(0.95)), 6), "umbral": UMBRAL}
    conexion = psycopg2.connect(host=os.getenv("POSTGRES_HOST", "oltp-postgres"),
                                port=int(os.getenv("POSTGRES_PORT", "5432")),
                                dbname=os.getenv("POSTGRES_META_DB", "datalab_meta"),
                                user=os.getenv("POSTGRES_USER", "datalab"),
                                password=os.getenv("POSTGRES_PASSWORD", ""))
    try:
        with conexion, conexion.cursor() as cur:
            cur.execute(
                "INSERT INTO meta.pipeline_runs (run_id, intent, status, current_step, current_agent) "
                "VALUES (%s, 'science', 'validado', 'batch_scoring', 'ds_mlops') "
                "ON CONFLICT (run_id) DO NOTHING", (run_id,))
            cur.execute(
                "INSERT INTO meta.handoffs (run_id, from_agent, to_agent, status, artifacts, contracts, metrics) "
                "VALUES (%s, 'ds_mlops', 'bi_viz', 'ok', %s::jsonb, %s::jsonb, %s::jsonb)",
                (run_id, json.dumps([uri, modelo_uri]),
                 json.dumps({"model_uri": modelo_uri, "scoring_dt": dt, "tabla": TABLA_FEATURES}),
                 json.dumps(metricas)))
    finally:
        conexion.close()
    logger.info("Handoff registrado en meta.handoffs: run_id=%s %s", run_id, metricas)


def main(argv: list[str] | None = None) -> int:
    """Ejecuta el scoring batch completo y devuelve el código de salida."""
    args = parse_args(argv)
    run_id = os.getenv("RUN_ID") or f"scoring_{args.dt}"
    try:
        df = cargar_features()
        modelo, modelo_uri = cargar_modelo(args.model, args.stage)
        salida = puntuar(modelo, df)
        uri = publicar_parquet(salida, args.dt)
        registrar_handoff(run_id, args.dt, uri, modelo_uri, salida)
    except Exception as exc:
        logger.error("Scoring fallido (model=%s stage=%s dt=%s): %s", args.model, args.stage, args.dt, exc)
        return 1
    print(f"run_id={run_id}")
    print(f"model_uri={modelo_uri}")
    print(f"scoring_uri={uri}")
    print(f"filas={len(salida)} positivos={int(salida['churn_pred'].sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
