-- =====================================================================
-- DataLab Productivo Local — staging.stg_orders  (capa Silver)
-- Documento: docs/architecture/data-pipeline.md §3 Paso 3 (conformado Silver)
-- Fuente: s3://datalake/bronze/orders/dt=*/part-*.parquet (MinIO)
--
-- Materialización: view · tag: silver · esquema: marts_staging
-- Responsabilidad: castear, normalizar y descartar filas sin clave.
-- NO se agrega ni se une con otras entidades (eso es `intermediate`).
-- =====================================================================
{{ config(
    materialized='view',
    tags=['silver', 'staging', 'orders'],
    schema='marts_staging'
) }}

SELECT
    CAST(order_id AS String)                       AS order_id,
    CAST(customer_id AS String)                    AS customer_id,
    parseDateTimeBestEffort(toString(order_ts))    AS ordered_at,
    lower(trim(toString(status)))                  AS status,
    lower(trim(toString(channel)))                 AS channel,
    toDecimal64(total_amount, 2)                   AS total_amount,
    toDate(parseDateTimeBestEffort(toString(order_ts))) AS order_date,
    parseDateTimeBestEffort(toString(updated_at))  AS updated_at,
    -- Columna virtual de la función s3(): la partición Hive `dt=YYYY-MM-DD`
    -- viaja en la ruta del objeto y sirve de linaje de la ingesta. Se extrae
    -- con regex (clase [0-9] en lugar de \d para evitar ambigüedad de escapes
    -- en el literal SQL de ClickHouse) sin depender de la posición del bucket.
    toDate(extract(_path, 'dt=([0-9]{4}-[0-9]{2}-[0-9]{2})')) AS ingested_dt
FROM {{ s3_parquet(source('bronze', 'orders')) }}
WHERE order_id IS NOT NULL
  AND trim(toString(order_id)) != ''
