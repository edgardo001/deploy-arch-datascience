-- =====================================================================
-- DataLab Productivo Local — marts.fct_orders
-- Documento: docs/architecture/data-pipeline.md §4-§5 (Gold + contrato)
--
-- Materialización: incremental · tag: gold · esquema: marts
-- Estrategia: delete+insert por `unique_key=order_id` (idempotente:
-- reejecutar con el mismo run_id no duplica líneas de pedido).
-- Granularidad declarada: 1 fila por LÍNEA de pedido (order_id + product_id).
-- Métricas: line_total, gross_margin, margin_rate.
-- =====================================================================
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='order_id',
    tags=['gold', 'marts', 'fact', 'orders'],
    schema='marts',
    order_by='(order_date, customer_id)'
) }}

SELECT
    e.order_id                                            AS order_id,
    e.product_id                                          AS product_id,
    e.customer_id                                         AS customer_id,
    d.date_key                                            AS date_key,
    e.order_date                                          AS order_date,
    e.ordered_at                                          AS ordered_at,
    e.status                                              AS status,
    e.channel                                             AS channel,
    e.seller_id                                           AS seller_id,
    p.product_sk                                          AS product_sk,
    p.category                                            AS category,
    p.brand                                               AS brand,
    e.quantity                                            AS quantity,
    e.unit_price                                          AS unit_price,
    e.discount_pct                                        AS discount_pct,
    e.line_total                                          AS line_total,
    -- Nombre de columna fijado por el contrato Gold (infra/contracts/marts.yml).
    e.order_total_amount                                  AS total_amount,
    -- Margen bruto de la línea: ingreso neto menos coste de la mercancía.
    toDecimal64(e.line_total - (e.quantity * p.cost_amount), 2) AS gross_margin,
    if(e.line_total > 0,
       round((e.line_total - (e.quantity * p.cost_amount)) / e.line_total, 4),
       0)                                                 AS margin_rate,
    e.updated_at                                          AS updated_at
FROM {{ ref('int_orders_enriched') }} AS e
INNER JOIN {{ ref('dim_date') }} AS d
        ON d.date_day = e.order_date
LEFT JOIN {{ ref('dim_product') }} AS p
       ON p.product_id = e.product_id
{% if is_incremental() %}
-- Ventana incremental: reprocesa el día de corte completo (idempotente por
-- delete+insert) y cualquier línea posterior.
WHERE e.order_date >= (SELECT max(order_date) FROM {{ this }})
{% endif %}
