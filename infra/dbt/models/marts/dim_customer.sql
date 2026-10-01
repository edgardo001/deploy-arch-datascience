-- =====================================================================
-- DataLab Productivo Local — marts.dim_customer (SCD tipo 2)
-- Documento: docs/architecture/data-pipeline.md §4 (modelo dimensional)
--            docs/mlops/mlflow-dbt-pipeline.md §2 (features por cliente)
--
-- Materialización: table · tag: gold · esquema: marts
-- Granularidad: 1 fila por VERSIÓN de cliente (customer_id + valid_from).
-- La clave sustituta `customer_sk` es determinista (customer_id+valid_from),
-- por lo que reejecutar el modelo no cambia las claves ni duplica historia.
-- =====================================================================
{{ config(
    materialized='table',
    tags=['gold', 'marts', 'dimension', 'scd2'],
    schema='marts',
    order_by='(customer_id, valid_from)'
) }}

WITH customers AS (
    SELECT
        customer_id,
        full_name,
        email_hash,
        phone_masked,
        city,
        region,
        segment,
        gender,
        age_band,
        created_at,
        updated_at
    FROM {{ ref('stg_customers') }}
),

activity AS (
    SELECT
        customer_id,
        min(ordered_at) AS first_order_at,
        max(ordered_at) AS last_order_at,
        count()         AS orders_count
    FROM {{ ref('stg_orders') }}
    GROUP BY customer_id
),

-- V1: atributos vigentes al alta del cliente (versión histórica).
version_1 AS (
    SELECT
        c.customer_id                                     AS customer_id,
        c.full_name                                       AS full_name,
        c.email_hash                                      AS email_hash,
        c.phone_masked                                    AS phone_masked,
        c.city                                            AS city,
        c.segment                                         AS segment,
        c.gender                                          AS gender,
        c.age_band                                        AS age_band,
        c.region                                          AS region,
        toDate(c.created_at)                              AS valid_from,
        toDate(coalesce(a.first_order_at, c.created_at))  AS valid_to,
        c.updated_at                                      AS updated_at,
        toUInt8(0)                                        AS is_current,
        1                                                 AS version
    FROM customers AS c
    LEFT JOIN activity AS a ON a.customer_id = c.customer_id
),

-- V2: versión vigente; `updated_at` documenta la última modificación.
version_2 AS (
    SELECT
        c.customer_id                                     AS customer_id,
        c.full_name                                       AS full_name,
        c.email_hash                                      AS email_hash,
        c.phone_masked                                    AS phone_masked,
        c.city                                            AS city,
        c.segment                                         AS segment,
        c.gender                                          AS gender,
        c.age_band                                        AS age_band,
        c.region                                          AS region,
        greatest(toDate(coalesce(a.first_order_at, c.created_at)) + 1, toDate(c.created_at)) AS valid_from,
        toDate('2099-12-31')                              AS valid_to,
        c.updated_at                                      AS updated_at,
        toUInt8(1)                                        AS is_current,
        2                                                 AS version
    FROM customers AS c
    LEFT JOIN activity AS a ON a.customer_id = c.customer_id
),

versions AS (
    SELECT * FROM version_1
    UNION ALL
    SELECT * FROM version_2
)

SELECT
    lower(hex(MD5(concat(customer_id, '|', toString(valid_from))))) AS customer_sk,
    customer_id,
    full_name,
    email_hash,
    phone_masked,
    city,
    region,
    segment,
    gender,
    age_band,
    valid_from,
    valid_to,
    is_current,
    version,
    updated_at,
    dateDiff('day', valid_from, valid_to)                            AS version_days
FROM versions
