# Imagen de Airflow del DataLab: extiende la base oficial e instala los providers y las
# librerías que usan los DAGs (PostgresHook, boto3, pandas/pyarrow, psycopg2, dbt-clickhouse…).
# Construcción:  docker compose build airflow   (el Compose del repo usa build: ./infra/airflow)
# El Compose NO monta este directorio: solo `dags/` y `plugins/`, así que la imagen es inmutable.
FROM apache/airflow:2.9.3-python3.11

# La imagen oficial ya define USER airflow; se reafirma para que pip instale sin privilegios.
USER airflow

# Requisitos con versiones compatibles con Airflow 2.9.3 / Python 3.11.
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /requirements.txt

# Los scripts de ML (infra/pipelines) y de QA (infra/qa) se ejecutan dentro del contenedor con
# `python /opt/airflow/pipelines/...`; los montajes concretos los define docker-compose.yml.
ENV PIPELINES_DIR=/opt/airflow/pipelines \
    PYTHONUNBUFFERED=1
