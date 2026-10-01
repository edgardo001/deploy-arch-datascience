-- =====================================================================
-- DataLab Productivo Local — test singular `anomaly_volume`
-- Documento: docs/architecture/data-pipeline.md §5 (contrato de volumen:
--            ±20 % vs. la media de 7 días → revisión manual)
--
-- Ubicación: infra/dbt/tests/ (test-path). Un .sql dentro de `models/`
-- se trataría como MODELO, no como test.
-- Tipo: test singular (se ejecuta con `dbt test`). Debe devolver 0 filas
-- para pasar: cada fila devuelta es una fecha con volumen bajo.
-- Regla: el volumen diario de pedidos de fct_orders no puede caer por
-- debajo del 80 % del volumen medio diario de la ventana analizada.
-- =====================================================================

WITH daily AS (
    SELECT
        order_date,
        count(DISTINCT order_id) AS orders_count
    FROM {{ ref('fct_orders') }}
    WHERE order_date >= today() - 30
      AND order_date < today()
    GROUP BY order_date
),

threshold AS (
    SELECT avg(orders_count) * 0.8 AS min_orders
    FROM daily
)

SELECT
    d.order_date,
    d.orders_count,
    round(t.min_orders, 2) AS min_expected,
    round(d.orders_count / nullIf(t.min_orders, 0) * 100, 2) AS pct_of_threshold
FROM daily AS d
CROSS JOIN threshold AS t
WHERE t.min_orders > 0
  AND d.orders_count < t.min_orders
ORDER BY d.order_date
