-- =====================================================================
-- DataLab Productivo Local — intermediate.int_orders_enriched
-- Documento: docs/architecture/data-pipeline.md §3 Paso 4 (integración)
-- Entradas: staging.stg_orders + Parquet Bronze de order_items,
--           stg_products y Bronze de sellers.
--
-- Materialización: view · tag: silver · esquema: marts_staging
-- Contrato interno: una fila por LÍNEA de pedido (order_id + product_id).
-- SIN agregación final ni métricas de negocio: eso pertenece a los marts.
-- =====================================================================
{{ config(
    materialized='view',
    tags=['silver', 'intermediate', 'orders'],
    schema='marts_staging'
) }}

WITH order_lines AS (
    SELECT
        CAST(order_id AS String)      AS order_id,
        CAST(product_id AS String)    AS product_id,
        toUInt32(quantity)            AS quantity,
        toDecimal64(unit_price, 2)    AS unit_price,
        toDecimal64(discount_pct, 2)  AS discount_pct,
        toDecimal64(line_total, 2)    AS line_total
    FROM {{ s3_parquet(source('bronze', 'order_items')) }}
    WHERE order_id IS NOT NULL
      AND product_id IS NOT NULL
),

sellers AS (
    SELECT
        seller_id,
        seller_name,
        region    AS seller_region,
        channel   AS seller_channel,
        joined_at AS seller_joined_at
    FROM {{ ref('stg_sellers') }}
)

SELECT
    -- Grano del contrato: línea de pedido.
    o.order_id                                        AS order_id,
    li.product_id                                     AS product_id,

    -- Cabecera del pedido.
    o.customer_id                                     AS customer_id,
    o.ordered_at                                      AS ordered_at,
    o.order_date                                      AS order_date,
    o.status                                          AS status,
    o.channel                                         AS channel,
    o.total_amount                                    AS order_total_amount,

    -- Línea.
    li.quantity                                       AS quantity,
    li.unit_price                                     AS unit_price,
    li.discount_pct                                   AS discount_pct,
    li.line_total                                     AS line_total,

    -- Producto (atributos de la dimensión).
    p.product_name                                    AS product_name,
    p.sku                                             AS sku,
    p.category                                        AS category,
    p.brand                                           AS brand,
    p.cost_amount                                     AS cost_amount,
    p.seller_id                                       AS seller_id,

    -- Vendedor.
    s.seller_name                                     AS seller_name,
    s.seller_region                                   AS seller_region,
    s.seller_channel                                  AS seller_channel,

    -- Watermark más reciente de las entidades implicadas.
    greatest(o.updated_at, p.updated_at)              AS updated_at,
    o.ingested_dt                                     AS ingested_dt
FROM {{ ref('stg_orders') }} AS o
INNER JOIN order_lines AS li
        ON li.order_id = o.order_id
LEFT JOIN {{ ref('stg_products') }} AS p
       ON p.product_id = li.product_id
LEFT JOIN sellers AS s
       ON s.seller_id = p.seller_id
WHERE o.order_id IS NOT NULL
