{# =====================================================================
 # DataLab Productivo Local — Macro de lectura de Parquet en MinIO (Bronze)
 # Documento: docs/architecture/data-pipeline.md §2-3 (aterrizaje Bronze)
 #            docs/infrastructure/docker-setup.md (servicio `minio`)
 #
 # ClickHouse lee el Data Lake con la función de tabla s3(). Firma real:
 #   s3(url [, NOSIGN | access_key_id, secret_access_key], format
 #      [, structure] [, compression])
 # El endpoint del object storage va DENTRO de la URL (no como argumento).
 # Las credenciales se resuelven con env_var(): el bucket `datalake` es
 # privado, nunca público, y no se hardcodea ningún secreto.
 # ===================================================================== #}

{% macro s3_parquet(relation, dt='*') -%}
    {%- set entity = relation.identifier if relation is not string else relation -%}
    {%- set bucket = var('bronze_bucket', env_var('MINIO_BUCKET', 'datalake')) -%}
    {%- set prefix = var('bronze_prefix', 'bronze') -%}
    {%- set host = var('minio_endpoint_host', env_var('MINIO_ENDPOINT_HOST', 'minio')) -%}
    {%- set port = var('minio_endpoint_port', env_var('MINIO_ENDPOINT_PORT', '9000')) -%}
    {%- set url = 'http://' ~ host ~ ':' ~ port ~ '/' ~ bucket ~ '/' ~ prefix ~ '/'
                  ~ entity ~ '/dt=' ~ dt ~ '/part-*.parquet' -%}
    s3('{{ url }}',
       '{{ env_var("MINIO_ROOT_USER", "minioadmin") }}',
       '{{ env_var("MINIO_ROOT_PASSWORD", "minioadmin") }}',
       'Parquet',
       'auto')
{%- endmacro %}
