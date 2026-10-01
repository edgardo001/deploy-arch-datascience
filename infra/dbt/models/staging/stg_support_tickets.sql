-- =====================================================================
-- DataLab Productivo Local — staging.stg_support_tickets  (capa Silver)
-- Documento: docs/architecture/data-pipeline.md §3 Paso 3
-- Fuente: s3://datalake/bronze/support_tickets/dt=*/part-*.parquet (MinIO)
--
-- Materialización: view · tag: silver · esquema: marts_staging
-- Bronze solo se lee en `staging`: customer_features consume esta vista.
-- =====================================================================
{{ config(
    materialized='view',
    tags=['silver', 'staging', 'support_tickets'],
    schema='marts_staging'
) }}

SELECT
    CAST(ticket_id AS String)                        AS ticket_id,
    CAST(customer_id AS String)                      AS customer_id,
    CAST(order_id AS String)                         AS order_id,
    parseDateTimeBestEffort(toString(opened_at))     AS opened_at,
    toDate(parseDateTimeBestEffort(toString(opened_at))) AS opened_date,
    lower(trim(toString(topic)))                     AS topic,
    lower(trim(toString(priority)))                  AS priority,
    lower(trim(toString(status)))                    AS status,
    parseDateTimeBestEffort(toString(updated_at))    AS updated_at
FROM {{ s3_parquet(source('bronze', 'support_tickets')) }}
WHERE ticket_id IS NOT NULL
  AND trim(toString(ticket_id)) != ''
