# =====================================================================
# DataLab Productivo Local — Imagen de MLflow Tracking + Model Registry
# Documento: docs/infrastructure/docker-setup.md (servicio `mlflow`)
#            docs/mlops/mlflow-dbt-pipeline.md (tracking y promoción)
#
# Backend store: PostgreSQL (datalab_meta en oltp-postgres:5432)
# Artifact store: s3://datalake/mlflow (MinIO en minio:9000)
# Por eso se añaden los drivers psycopg2 (PostgreSQL) y boto3 (S3).
# Sin secretos: llegan por variables de entorno en docker-compose.yml.
# =====================================================================
FROM ghcr.io/mlflow/mlflow:v2.14.1

# Drivers de backend y de artefactos (sin caché para mantener la imagen ligera).
RUN pip install --no-cache-dir psycopg2-binary boto3

# Puerto del servidor de tracking (host interno `mlflow:5000`).
EXPOSE 5000
