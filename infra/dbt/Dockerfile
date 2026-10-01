# =====================================================================
# DataLab Productivo Local — Imagen de transformación analítica (dbt)
# Documento: docs/infrastructure/docker-setup.md (servicio `dbt`)
#            docs/agents/specialists-deep-dive.md (comandos de analytics_engineer)
#
# Se construye en ./infra/dbt y el compose además monta ese directorio en
# /usr/app/dbt, por lo que dbt_project.yml, profiles.yml y models/ se
# editan en caliente sin reconstruir.
# Sin secretos: las credenciales de ClickHouse/MinIO llegan por env_var()
# desde .env a través de dbt profiles.yml y de los macros del proyecto.
# =====================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DBT_PROFILES_DIR=/usr/app/dbt

# dbt-core y el adaptador de ClickHouse, fijados a la serie 1.8.x
# (dbt-clickhouse 1.8.2 + dbt-core 1.8.9). dbt-duckdb queda como motor
# alternativo para ejecución local sin warehouse.
RUN pip install --no-cache-dir \
        dbt-core==1.8.9 \
        dbt-clickhouse==1.8.2 \
        dbt-duckdb

# Las dependencias de paquetes dbt (`dbt deps`) NO se ejecutan en build:
# se resuelven en runtime para no empaquetar dbt_packages/ en la imagen.
WORKDIR /usr/app/dbt

# Entrada por defecto: `docker compose run --rm dbt build` ejecuta `dbt build`.
ENTRYPOINT ["dbt"]
CMD ["--version"]
