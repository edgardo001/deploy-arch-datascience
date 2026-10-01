-- =====================================================================
-- DataLab Productivo Local — marts.dim_seller
-- Documento: docs/architecture/data-pipeline.md §4 (modelo dimensional)
--
-- Materialización: table · tag: gold · esquema: marts
-- Granularidad: 1 fila por vendedor (seller_id).
-- Antigüedad (tenure_days) calculada contra hoy, no almacenada como
-- atributo mutable, para que el test de unicidad siga siendo estable.
-- =====================================================================
{{ config(
    materialized='table',
    tags=['gold', 'marts', 'dimension'],
    schema='marts',
    order_by='seller_id'
) }}

SELECT
    lower(hex(MD5(s.seller_id)))                         AS seller_sk,
    s.seller_id                                          AS seller_id,
    s.seller_name                                        AS seller_name,
    s.region                                             AS region,
    s.channel                                            AS channel,
    s.joined_at                                          AS joined_at,
    dateDiff('day', toDate(s.joined_at), today())        AS tenure_days,
    -- Nº de productos vivos que dependen del vendedor (atributo de cobertura).
    countIf(p.product_id IS NOT NULL)                    AS products_count,
    max(p.updated_at)                                    AS last_product_update
FROM {{ ref('stg_sellers') }} AS s
LEFT JOIN {{ ref('stg_products') }} AS p
       ON p.seller_id = s.seller_id
WHERE s.seller_id IS NOT NULL
GROUP BY
    s.seller_id,
    s.seller_name,
    s.region,
    s.channel,
    s.joined_at
