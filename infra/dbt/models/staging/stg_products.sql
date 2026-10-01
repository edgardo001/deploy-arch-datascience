-- =====================================================================
-- DataLab Productivo Local — staging.stg_products  (capa Silver)
-- Documento: docs/architecture/data-pipeline.md §3 Paso 3
-- Fuente: s3://datalake/bronze/products/dt=*/part-*.parquet (MinIO)
--
-- Materialización: view · tag: silver · esquema: marts_staging
-- Precios y costes tipados como Decimal; el margen bruto se calcula en
-- `fct_orders`, nunca en staging.
-- =====================================================================
{{ config(
    materialized='view',
    tags=['silver', 'staging', 'products'],
    schema='marts_staging'
) }}

SELECT
    CAST(product_id AS String)                     AS product_id,
    upper(trim(toString(sku)))                     AS sku,
    trim(toString(product_name))                   AS product_name,
    lower(trim(toString(category)))                AS category,
    lower(trim(toString(brand)))                   AS brand,
    toDecimal64(unit_price, 2)                     AS unit_price,
    toDecimal64(cost_amount, 2)                    AS cost_amount,
    CAST(seller_id AS String)                      AS seller_id,
    toUInt8(is_active)                             AS is_active,
    parseDateTimeBestEffort(toString(updated_at))  AS updated_at
FROM {{ s3_parquet(source('bronze', 'products')) }}
WHERE product_id IS NOT NULL
  AND trim(toString(product_id)) != ''
