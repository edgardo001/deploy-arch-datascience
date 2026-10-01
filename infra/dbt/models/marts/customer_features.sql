-- =====================================================================
-- DataLab Productivo Local — marts.customer_features
-- Documento: docs/mlops/mlflow-dbt-pipeline.md §2 (contrato de features)
--
-- Materialización: incremental · tag: features · esquema: marts
-- Estrategia: delete+insert por `unique_key=customer_id` (idempotente).
-- Granularidad declarada: 1 fila por CLIENTE con la foto de features de
-- `report_date` (fecha de cálculo). Fuente única: marts Gold.
-- =====================================================================
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='customer_id',
    tags=['gold', 'features', 'marts'],
    schema='marts',
    order_by='(report_date, customer_id)'
) }}

WITH orders AS (
    SELECT
        customer_id,
        order_id,
        order_date,
        status,
        line_total
    FROM {{ ref('fct_orders') }}
    WHERE status NOT IN ('cancelled', 'refunded')
      -- Sin compras en 365 días no cambian las features: se reescriben solo
      -- las filas cuyo cálculo puede variar (idempotente y barato).
      AND order_date >= today() - 365
),

customer_orders AS (
    SELECT
        customer_id,
        max(order_date)                                              AS last_order_date,
        min(order_date)                                              AS first_order_date,
        count(DISTINCT order_id)                                     AS orders_total,
        countIf(order_date >= today() - 30)                          AS orders_last_30d,
        sumIf(line_total, order_date >= today() - 365)               AS monetary_365d,
        avgIf(line_total, order_date >= today() - 365)               AS avg_ticket
    FROM orders
    GROUP BY customer_id
),

tickets AS (
    SELECT
        customer_id,
        countIf(opened_date >= today() - 90)                         AS tickets_support_90d
    FROM {{ ref('stg_support_tickets') }}
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
),

featured AS (
    SELECT
        o.customer_id,
        today()                                                      AS report_date,
        dateDiff('day', o.last_order_date, today())                  AS recency_days,
        toUInt32(o.orders_last_30d)                                  AS orders_last_30d,
        toDecimal64(coalesce(o.monetary_365d, 0), 2)                 AS monetary_365d,
        toDecimal64(coalesce(o.avg_ticket, 0), 2)                    AS avg_ticket,
        toUInt32(coalesce(t.tickets_support_90d, 0))                 AS tickets_support_90d,
        -- Etiqueta de churn: sin compra en los últimos `churn_days` (180 d).
        toUInt8(o.last_order_date < today() - {{ var('churn_days', 180) }}) AS churn_label,
        toUInt32(o.orders_total)                                     AS orders_total,
        o.first_order_date                                           AS first_order_date,
        o.last_order_date                                            AS last_order_date,
        -- Marca de frescura exigida por el contrato Gold (marts.yml).
        toDateTime(today())                                          AS updated_at
    FROM customer_orders AS o
    LEFT JOIN tickets AS t ON t.customer_id = o.customer_id
)

SELECT *
FROM featured
{% if is_incremental() %}
-- La foto diaria se recalcula para los clientes con actividad en la ventana
-- de features; delete+insert por customer_id evita acumular versiones viejas.
WHERE report_date > (SELECT max(report_date) FROM {{ this }})
{% endif %}
