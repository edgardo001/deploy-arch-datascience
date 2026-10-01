-- =====================================================================
-- DataLab Productivo Local — marts.fct_payments
-- Documento: docs/architecture/data-pipeline.md §4 (modelo dimensional)
--
-- Materialización: incremental · tag: gold · esquema: marts
-- Estrategia: delete+insert por `unique_key=payment_id`.
-- Granularidad declarada: 1 fila por PAGO (payment_id).
-- =====================================================================
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='payment_id',
    tags=['gold', 'marts', 'fact', 'payments'],
    schema='marts',
    order_by='(paid_date, customer_id)'
) }}

WITH orders AS (
    SELECT
        order_id,
        customer_id,
        status         AS order_status,
        total_amount   AS order_total_amount,
        order_date     AS order_date,
        updated_at     AS order_updated_at
    FROM {{ ref('stg_orders') }}
)

SELECT
    pay.payment_id                                      AS payment_id,
    pay.order_id                                        AS order_id,
    ord.customer_id                                     AS customer_id,
    d.date_key                                          AS date_key,
    toDate(pay.paid_at)                                 AS paid_date,
    pay.paid_at                                         AS paid_at,
    pay.payment_method                                  AS payment_method,
    pay.payment_status                                  AS payment_status,
    pay.paid_amount                                     AS paid_amount,
    ord.order_status                                    AS order_status,
    -- Diferencia entre lo facturado y lo cobrado (0 si está cuadrado).
    toDecimal64(ord.order_total_amount - pay.paid_amount, 2) AS amount_gap,
    toUInt8(pay.payment_status = 'approved')            AS is_approved,
    pay.updated_at                                      AS updated_at
FROM {{ ref('stg_payments') }} AS pay
LEFT JOIN orders AS ord ON ord.order_id = pay.order_id
LEFT JOIN {{ ref('dim_date') }} AS d ON d.date_day = toDate(pay.paid_at)
{% if is_incremental() %}
-- Reprocesa la última fecha de pago completa: idempotente por delete+insert.
WHERE toDate(pay.paid_at) >= (SELECT max(paid_date) FROM {{ this }})
{% endif %}
