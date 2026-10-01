-- =====================================================================
-- DataLab Productivo Local — marts.dim_product
-- Documento: docs/architecture/data-pipeline.md §4 (modelo dimensional)
--
-- Materialización: table · tag: gold · esquema: marts
-- Granularidad: 1 fila por producto (product_id).
-- La dimensión NO se filtra por is_active: los hechos históricos deben
-- poder unirse a productos ya descatalogados.
-- =====================================================================
{{ config(
    materialized='table',
    tags=['gold', 'marts', 'dimension'],
    schema='marts',
    order_by='product_id'
) }}

WITH products AS (
    SELECT
        product_id,
        sku,
        product_name,
        category,
        brand,
        unit_price,
        cost_amount,
        seller_id,
        updated_at
    FROM {{ ref('stg_products') }}
),

sales AS (
    SELECT product_id, max(ingested_dt) AS last_ingested_dt
    FROM {{ ref('int_orders_enriched') }}
    GROUP BY product_id
)

SELECT
    lower(hex(MD5(p.product_id)))                     AS product_sk,
    p.product_id                                      AS product_id,
    p.sku                                             AS sku,
    p.product_name                                    AS product_name,
    p.category                                        AS category,
    -- Segmento de negocio y prioridad comercial desde la semilla curada
    -- `product_category_map` (infra/dbt/seeds/product_category_map.csv).
    cm.segment                                        AS category_segment,
    cm.priority                                       AS category_priority,
    p.brand                                           AS brand,
    p.unit_price                                      AS list_price,
    p.cost_amount                                     AS cost_amount,
    -- Margen unitario teórico (el realizado se calcula en fct_orders).
    toDecimal64(p.unit_price - p.cost_amount, 2)      AS unit_margin,
    if(p.unit_price > 0,
       round((p.unit_price - p.cost_amount) / p.unit_price, 4),
       0)                                             AS margin_rate,
    p.seller_id                                       AS seller_id,
    p.updated_at                                      AS updated_at,
    s.last_ingested_dt                                AS last_ingested_dt
FROM products AS p
LEFT JOIN sales AS s ON s.product_id = p.product_id
LEFT JOIN {{ ref('product_category_map') }} AS cm ON cm.category = p.category
