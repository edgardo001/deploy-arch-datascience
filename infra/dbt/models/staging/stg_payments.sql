-- =====================================================================
-- DataLab Productivo Local — staging.stg_payments  (capa Silver)
-- Documento: docs/architecture/data-pipeline.md §3 Paso 3
-- Fuente: s3://datalake/bronze/payments/dt=*/part-*.parquet (MinIO)
--
-- Materialización: view · tag: silver · esquema: marts_staging
-- Bronze solo se lee en `staging`: fct_payments consume esta vista.
-- =====================================================================
{{ config(
    materialized='view',
    tags=['silver', 'staging', 'payments'],
    schema='marts_staging'
) }}

SELECT
    CAST(payment_id AS String)                     AS payment_id,
    CAST(order_id AS String)                       AS order_id,
    parseDateTimeBestEffort(toString(paid_at))     AS paid_at,
    lower(trim(toString(payment_method)))          AS payment_method,
    toDecimal64(paid_amount, 2)                    AS paid_amount,
    lower(trim(toString(payment_status)))          AS payment_status,
    parseDateTimeBestEffort(toString(updated_at))  AS updated_at
FROM {{ s3_parquet(source('bronze', 'payments')) }}
WHERE payment_id IS NOT NULL
  AND trim(toString(payment_id)) != ''
