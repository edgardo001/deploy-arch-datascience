"""DAG ``ingest_oltp_to_bronze`` — ingesta incremental PostgreSQL OLTP → Bronze (MinIO).

Contrato operativo (AGENTS.md §2.3 y docs/architecture/data-pipeline.md §3):

* **Extracción incremental** por ``updated_at``; el *watermark* se lee de ``meta.ingest_watermarks``
  y, si esa tabla no existe, de ``meta.ingest_audit``.
* **Aterrizaje inmutable** en ``s3://datalake/bronze/<entidad>/dt=YYYY-MM-DD/part-000.parquet``,
  reemplazando la partición para ser idempotente por ``run_id``/``dt``.
* **Cuadre de conteos** origen (PostgreSQL) contra destino (Parquet en MinIO) por partición.
* **Auditoría** en ``meta.ingest_audit`` con ``run_id``, ``entity``, ``dt``, ``rows_read``,
  ``watermark`` y ``checksum``.

Credenciales: solo conexiones de Airflow (``oltp_postgres`` para la fuente y la metadata store,
``minio`` para S3) y variables de entorno; nunca un DSN con contraseña en el código.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3
import pyarrow.parquet as pq
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.hooks.base import BaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook

logger = logging.getLogger(__name__)

ENTIDADES = {"orders": "public.orders", "customers": "public.customers", "products": "public.products"}
COLUMNA_INCREMENTAL = "updated_at"
CONN_OLTP, CONN_MINIO = "oltp_postgres", "minio"
BUCKET = os.getenv("MINIO_BUCKET", "datalake")
OLTP_DB = os.getenv("POSTGRES_OLTP_DB", "ecommerce_oltp")
META_DB = os.getenv("POSTGRES_META_DB", "datalab_meta")
STAGING_DIR = os.getenv("BRONZE_STAGING_DIR", "/tmp/bronze_staging")
WATERMARK_INICIAL = "1970-01-01T00:00:00+00:00"

DEFAULT_ARGS = {"owner": "data_engineer", "retries": 3, "retry_delay": timedelta(seconds=30),
                "retry_exponential_backoff": True, "max_retry_delay": timedelta(minutes=10)}


def _hook(base: str) -> PostgresHook:
    """Hook Postgres sobre la conexión Airflow ``oltp_postgres`` apuntando a ``base``."""
    return PostgresHook(postgres_conn_id=CONN_OLTP, schema=base)


def _cliente_minio():
    """Cliente boto3 hacia MinIO usando la conexión Airflow ``minio``."""
    endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio:9000")
    acceso, secreto = os.getenv("MINIO_ROOT_USER"), os.getenv("MINIO_ROOT_PASSWORD")
    try:
        conn = BaseHook.get_connection(CONN_MINIO)
        if conn.host:
            endpoint = f"http://{conn.host}:{conn.port or 9000}"
        acceso, secreto = conn.login or acceso, conn.password or secreto
    except Exception as exc:  # conexión no registrada → se usan las variables de entorno
        logger.warning("Conexión '%s' no disponible (%s); uso variables de entorno", CONN_MINIO, exc)
    return boto3.client("s3", endpoint_url=endpoint,
                        aws_access_key_id=acceso, aws_secret_access_key=secreto)


def _leer_watermark(entidad: str) -> str:
    """Último *watermark* conocido: ``ingest_watermarks`` y, si no existe, ``ingest_audit``."""
    hook = _hook(META_DB)
    fuentes = ("SELECT max(watermark) FROM meta.ingest_watermarks WHERE entity = %s",
               "SELECT max(watermark) FROM meta.ingest_audit WHERE entity = %s")
    for sql in fuentes:
        try:
            valor = hook.get_first(sql, parameters=(entidad,))[0]
        except Exception as exc:  # tabla ausente o sin permisos → siguiente fuente
            logger.warning("[%s] fuente de watermark no disponible: %s", entidad, exc)
            continue
        if valor is not None:
            return valor.isoformat() if hasattr(valor, "isoformat") else str(valor)
    return WATERMARK_INICIAL


def _extraer(entidad: str, run_id: str, ds: str) -> dict:
    """Extrae la ventana incremental de una entidad y la deja en *staging* local."""
    inicio, fin = _leer_watermark(entidad), datetime.now(timezone.utc).isoformat()
    sql = (f"SELECT * FROM {ENTIDADES[entidad]} WHERE {COLUMNA_INCREMENTAL} > %s "
           f"AND {COLUMNA_INCREMENTAL} <= %s ORDER BY {COLUMNA_INCREMENTAL}")
    try:
        df = _hook(OLTP_DB).get_pandas_df(sql, parameters=(inicio, fin))
    except Exception as exc:
        raise AirflowException(f"[run_id={run_id}] falló la extracción de {entidad}: {exc}") from exc
    os.makedirs(STAGING_DIR, exist_ok=True)
    ruta = os.path.join(STAGING_DIR, f"{entidad}_{ds}.parquet")
    df.to_parquet(ruta, index=False, compression="snappy")
    logger.info("[run_id=%s] extract_%s: %s filas (watermark %s → %s) → %s",
                run_id, entidad, len(df), inicio, fin, ruta)
    return {"entity": entidad, "run_id": run_id, "dt": ds, "rows_read": int(len(df)),
            "watermark_start": inicio, "watermark_end": fin, "staging_path": ruta}


@task
def extract(entity: str, *, run_id: str, ds: str) -> dict:
    """Extrae una entidad de forma incremental; ``{{ run_id }}`` viaja a los logs."""
    return _extraer(entity, run_id, ds)


def _subir_entidad(cliente, meta: dict) -> dict:
    """Sube una entidad a ``bronze/<entidad>/dt=.../part-000.parquet`` sobrescribiendo la partición."""
    prefijo = f"bronze/{meta['entity']}/dt={meta['dt']}/"
    clave = f"{prefijo}part-000.parquet"
    with open(meta["staging_path"], "rb") as fh:
        contenido = fh.read()
    try:
        previos = cliente.list_objects_v2(Bucket=BUCKET, Prefix=prefijo).get("Contents", [])
        if previos:  # idempotencia: la partición se reemplaza, nunca se duplica
            cliente.delete_objects(Bucket=BUCKET, Delete={"Objects": [{"Key": o["Key"]} for o in previos]})
        cliente.put_object(Bucket=BUCKET, Key=clave, Body=contenido)
    except Exception as exc:
        raise AirflowException(f"[run_id={meta['run_id']}] falló la subida de {meta['entity']} "
                               f"a s3://{BUCKET}/{clave}: {exc}") from exc
    logger.info("[run_id=%s] bronze %s → s3://%s/%s (%s bytes)",
                meta["run_id"], meta["entity"], BUCKET, clave, len(contenido))
    return {**meta, "s3_uri": f"s3://{BUCKET}/{clave}", "checksum": hashlib.sha256(contenido).hexdigest()[:32]}


@task
def write_bronze_parquet(ordenes: dict, clientes: dict, productos: dict) -> list[dict]:
    """Sube las tres entidades a Bronze con boto3 (endpoint MinIO de la conexión ``minio``)."""
    cliente = _cliente_minio()
    return [_subir_entidad(cliente, meta) for meta in (ordenes, clientes, productos)]


@task
def validate_counts(escrituras: list[dict]) -> list[dict]:
    """Cuadra filas origen/destino por entidad y partición; falla ruidoso si no coinciden."""
    hook, cliente = _hook(OLTP_DB), _cliente_minio()
    for meta in escrituras:
        sql = (f"SELECT count(*) FROM {ENTIDADES[meta['entity']]} "
               f"WHERE {COLUMNA_INCREMENTAL} > %s AND {COLUMNA_INCREMENTAL} <= %s")
        origen = int(hook.get_first(sql, parameters=(meta["watermark_start"], meta["watermark_end"]))[0])
        clave = meta["s3_uri"].split(f"s3://{BUCKET}/", 1)[1]
        destino = pq.read_table(io.BytesIO(cliente.get_object(Bucket=BUCKET, Key=clave)["Body"].read())).num_rows
        if origen != destino:
            raise AirflowException(f"Descuadre de conteos en {meta['entity']} dt={meta['dt']} "
                                   f"(run_id={meta['run_id']}): origen={origen} destino={destino} "
                                   f"partición={meta['s3_uri']}")
        meta["rows_bronze"] = destino
        logger.info("[run_id=%s] cuadre OK %s dt=%s: %s filas", meta["run_id"], meta["entity"], meta["dt"], destino)
    return escrituras


@task
def update_watermark(validaciones: list[dict]) -> None:
    """Registra la auditoría de ingesta y avanza el *watermark* de cada entidad."""
    hook = _hook(META_DB)
    for meta in validaciones:
        try:
            hook.run(
                "INSERT INTO meta.ingest_audit (run_id, entity, dt, rows_read, watermark, checksum) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (run_id, entity, dt) DO UPDATE SET rows_read = EXCLUDED.rows_read, "
                "watermark = EXCLUDED.watermark, checksum = EXCLUDED.checksum",
                parameters=(meta["run_id"], meta["entity"], meta["dt"], meta["rows_bronze"],
                            meta["watermark_end"], meta["checksum"]),
            )
        except Exception as exc:
            raise AirflowException(
                f"[run_id={meta['run_id']}] no se pudo auditar {meta['entity']}: {exc}"
            ) from exc
        logger.info("[run_id=%s] ingest_audit %s", meta["run_id"],
                    json.dumps({"entity": meta["entity"], "dt": meta["dt"], "rows_read": meta["rows_bronze"],
                                "watermark": meta["watermark_end"], "checksum": meta["checksum"]}, default=str))


@dag(
    dag_id="ingest_oltp_to_bronze",
    description="Ingesta incremental PostgreSQL OLTP → Parquet Bronze en MinIO",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["bronze", "ingest"],
    doc_md=__doc__,
)
def ingest_oltp_to_bronze() -> None:
    """Extracción en paralelo → aterrizaje Bronze → cuadre de conteos → auditoría."""
    # task_ids exigidos: extract_orders, extract_customers, extract_products (misma tarea reutilizada).
    # Los parámetros de contexto se pasan explícitos y templateados (no se dejan sin argumento).
    extracciones = [
        extract.override(task_id=f"extract_{entidad}")(
            entidad, run_id="{{ run_id }}", ds="{{ ds }}")
        for entidad in ENTIDADES
    ]
    escrituras = write_bronze_parquet(*extracciones)
    update_watermark(validate_counts(escrituras))


ingest_oltp_to_bronze()
