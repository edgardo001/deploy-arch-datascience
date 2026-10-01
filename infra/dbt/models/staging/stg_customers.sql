-- =====================================================================
-- DataLab Productivo Local — staging.stg_customers  (capa Silver)
-- Documento: docs/memory/memory-persistence.md §7 (PII solo enmascarada)
--            docs/architecture/data-pipeline.md §3 Paso 3
-- Fuente: s3://datalake/bronze/customers/dt=*/part-*.parquet (MinIO)
--
-- Materialización: view · tag: silver · esquema: marts_staging
-- Minimización de datos: a partir de Silver el email y el teléfono
-- originales NO se propagan; solo `email_hash` (SHA-256) y `phone_masked`.
-- =====================================================================
{{ config(
    materialized='view',
    tags=['silver', 'staging', 'customers'],
    schema='marts_staging'
) }}

SELECT
    CAST(customer_id AS String)                                              AS customer_id,
    trim(toString(full_name))                                                AS full_name,
    -- Hash determinista: permite unir/segmentar sin exponer el email.
    lower(hex(SHA256(lower(trim(toString(email))))))                          AS email_hash,
    -- Máscara tipo +34 6** *** 78 (se conservan prefijo y 2 últimos dígitos).
    concat(
        substring(toString(phone), 1, 6),
        '****',
        substring(toString(phone), greatest(length(toString(phone)) - 1, 1), 2)
    )                                                                        AS phone_masked,
    lower(trim(toString(city)))                                              AS city,
    lower(trim(toString(region)))                                            AS region,
    lower(trim(toString(segment)))                                           AS segment,
    -- Columnas sensibles: las usa la auditoría de sesgo de `governance`
    -- (infra/contracts/marts.yml → marts.dim_customer.gender/age_band).
    lower(trim(toString(gender)))                                            AS gender,
    trim(toString(age_band))                                                 AS age_band,
    parseDateTimeBestEffort(toString(created_at))                            AS created_at,
    parseDateTimeBestEffort(toString(updated_at))                            AS updated_at
FROM {{ s3_parquet(source('bronze', 'customers')) }}
WHERE customer_id IS NOT NULL
  AND trim(toString(customer_id)) != ''
