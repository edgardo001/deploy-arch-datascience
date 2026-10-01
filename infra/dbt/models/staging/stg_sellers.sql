-- =====================================================================
-- DataLab Productivo Local — staging.stg_sellers  (capa Silver)
-- Documento: docs/architecture/data-pipeline.md §3 Paso 3
-- Fuente: s3://datalake/bronze/sellers/dt=*/part-*.parquet (MinIO)
--
-- Materialización: view · tag: silver · esquema: marts_staging
-- =====================================================================
{{ config(
    materialized='view',
    tags=['silver', 'staging', 'sellers'],
    schema='marts_staging'
) }}

SELECT
    CAST(seller_id AS String)                     AS seller_id,
    trim(toString(seller_name))                   AS seller_name,
    lower(trim(toString(region)))                 AS region,
    lower(trim(toString(channel)))                AS channel,
    parseDateTimeBestEffort(toString(joined_at))  AS joined_at,
    parseDateTimeBestEffort(toString(updated_at)) AS updated_at
FROM {{ s3_parquet(source('bronze', 'sellers')) }}
WHERE seller_id IS NOT NULL
  AND trim(toString(seller_id)) != ''
