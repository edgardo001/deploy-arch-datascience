-- =====================================================================
-- DataLab Productivo Local — Semilla reproducible del OLTP
-- Documentos: docs/architecture/data-pipeline.md §2 (volumen de las etapas)
--             docs/infrastructure/docker-setup.md (smoke test de la §6)
-- Script 03 de 03 (tras 02_oltp_schema.sql).
--
-- Volúmenes: 200 clientes, 5 vendedores, 50 productos, 800 órdenes
-- repartidas en 120 días, sus líneas coherentes con total_amount, un pago
-- por orden y 100 tickets de soporte.
-- Reproducible e idempotente:
--   · fechas ancladas a `now() - (n || ' days')::interval`
--   · atributos derivados de expresiones deterministas sobre `n` (sin random)
--   · ON CONFLICT DO NOTHING en todas las tablas (reejecutar no duplica)
-- =====================================================================

\set ON_ERROR_STOP on
\connect ecommerce_oltp

INSERT INTO public.sellers (seller_id, seller_name, region, channel, joined_at, updated_at)
SELECT 'SEL-' || lpad(n::text, 3, '0'),
       'Vendedor ' || n,
       (ARRAY['norte','sur','centro','este','oeste'])[1 + ((n - 1) % 5)],
       (ARRAY['marketplace','directo','partner'])[1 + ((n - 1) % 3)],
       now() - ((n * 30) || ' days')::interval,
       now() - ((n * 30) || ' days')::interval
FROM generate_series(1, 5) AS n
ON CONFLICT (seller_id) DO NOTHING;

INSERT INTO public.customers (customer_id, full_name, email, phone, city, region, segment,
                              gender, age_band, created_at, updated_at)
SELECT 'CUS-' || lpad(n::text, 5, '0'),
       'Cliente ' || n,
       'cliente' || n || '@example.com',
       '+34 6' || lpad(((n * 7919) % 100000000)::text, 8, '0'),
       (ARRAY['Madrid','Barcelona','Valencia','Sevilla','Bilbao','Malaga','Zaragoza','Murcia'])[1 + ((n - 1) % 8)],
       (ARRAY['centro','noreste','este','sur','norte','sur','noreste','sureste'])[1 + ((n - 1) % 8)],
       (ARRAY['retail','pyme','enterprise'])[1 + ((n - 1) % 3)],
       (ARRAY['f','m','x'])[1 + ((n - 1) % 3)],
       (ARRAY['18-24','25-34','35-44','45-54','55+'])[1 + ((n - 1) % 5)],
       now() - ((n % 400) || ' days')::interval,
       now() - ((n % 60) || ' days')::interval
FROM generate_series(1, 200) AS n
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO public.products (product_id, sku, product_name, category, brand, unit_price,
                             cost_amount, seller_id, is_active, created_at, updated_at)
SELECT 'PRD-' || lpad(n::text, 5, '0'),
       'SKU-' || lpad(n::text, 5, '0'),
       'Producto ' || n,
       (ARRAY['electronica','hogar','moda','deportes','libros'])[1 + ((n - 1) % 5)],
       'Marca ' || (1 + ((n - 1) % 12)),
       round(9.90 + (n % 20) * 7.25, 2),
       round((9.90 + (n % 20) * 7.25) * 0.62, 2),
       'SEL-' || lpad((1 + ((n - 1) % 5))::text, 3, '0'),
       (n % 17) <> 0,
       now() - ((n % 300) || ' days')::interval,
       now() - ((n % 45) || ' days')::interval
FROM generate_series(1, 50) AS n
ON CONFLICT (product_id) DO NOTHING;

-- Órdenes: 800 filas repartidas por `n % 120` días atrás. `total_amount`
-- se deriva de las líneas para que cuadre exactamente con order_items.
WITH ord AS (
    SELECT n,
           'ORD-' || lpad(n::text, 6, '0')                        AS order_id,
           'CUS-' || lpad((1 + ((n * 37) % 200))::text, 5, '0')   AS customer_id,
           now() - ((n % 120) || ' days')::interval
                 - ((n % 11) || ' hours')::interval               AS order_ts,
           (ARRAY['pending','paid','shipped','delivered','cancelled','refunded'])[1 + ((n - 1) % 6)] AS status,
           (ARRAY['web','app','phone'])[1 + ((n - 1) % 3)]        AS channel
    FROM generate_series(1, 800) AS n
), lines AS (
    SELECT o.n, o.order_id, o.customer_id, o.order_ts, o.status, o.channel,
           1 + ((o.n + i.item_ix) % 4)                            AS quantity,
           round(9.90 + ((((o.n * 7) + (i.item_ix * 11)) % 50) % 20) * 7.25, 2) AS unit_price,
           (o.n % 3) * 2.5                                        AS discount_pct
    FROM ord AS o
    CROSS JOIN generate_series(1, 2) AS i(item_ix)
    WHERE i.item_ix = 1 OR (o.n % 3) = 0
), tot AS (
    SELECT n, order_id, customer_id, order_ts, status, channel,
           round(sum(quantity * unit_price * (1 - discount_pct / 100.0)), 2) AS total_amount
    FROM lines
    GROUP BY n, order_id, customer_id, order_ts, status, channel
)
INSERT INTO public.orders (order_id, customer_id, order_ts, status, channel, total_amount,
                           created_at, updated_at)
SELECT order_id, customer_id, order_ts, status, channel, total_amount, order_ts, order_ts
FROM tot
ON CONFLICT (order_id) DO NOTHING;

INSERT INTO public.order_items (order_id, product_id, quantity, unit_price, discount_pct,
                                line_total, updated_at)
SELECT 'ORD-' || lpad(o.n::text, 6, '0'),
       'PRD-' || lpad((1 + (((o.n * 7) + (i.item_ix * 11)) % 50))::text, 5, '0'),
       1 + ((o.n + i.item_ix) % 4),
       round(9.90 + ((((o.n * 7) + (i.item_ix * 11)) % 50) % 20) * 7.25, 2),
       (o.n % 3) * 2.5,
       round((1 + ((o.n + i.item_ix) % 4))
             * round(9.90 + ((((o.n * 7) + (i.item_ix * 11)) % 50) % 20) * 7.25, 2)
             * (1 - ((o.n % 3) * 2.5) / 100.0), 2),
       now() - ((o.n % 120) || ' days')::interval
FROM generate_series(1, 800) AS o(n)
CROSS JOIN generate_series(1, 2) AS i(item_ix)
WHERE i.item_ix = 1 OR (o.n % 3) = 0
ON CONFLICT (order_id, product_id) DO NOTHING;

INSERT INTO public.payments (payment_id, order_id, paid_at, payment_method, paid_amount,
                             payment_status, updated_at)
SELECT 'PAY-' || lpad(n::text, 6, '0'),
       'ORD-' || lpad(n::text, 6, '0'),
       o.order_ts + INTERVAL '2 hours',
       (ARRAY['card','transfer','wallet','cash'])[1 + ((n - 1) % 4)],
       CASE WHEN o.status IN ('cancelled','refunded') THEN 0 ELSE o.total_amount END,
       CASE o.status WHEN 'cancelled' THEN 'rejected' WHEN 'refunded' THEN 'refunded'
                     WHEN 'pending' THEN 'pending' ELSE 'approved' END,
       o.order_ts + INTERVAL '2 hours'
FROM generate_series(1, 800) AS n
JOIN public.orders AS o ON o.order_id = 'ORD-' || lpad(n::text, 6, '0')
ON CONFLICT (payment_id) DO NOTHING;

INSERT INTO public.support_tickets (ticket_id, customer_id, order_id, opened_at, topic,
                                    priority, status, updated_at)
SELECT 'TCK-' || lpad(n::text, 5, '0'),
       'CUS-' || lpad((1 + ((n * 37) % 200))::text, 5, '0'),
       'ORD-' || lpad((1 + ((n * 13) % 800))::text, 6, '0'),
       now() - ((n % 120) || ' days')::interval - ((n % 9) || ' hours')::interval,
       (ARRAY['envio','facturacion','devolucion','producto','cuenta'])[1 + ((n - 1) % 5)],
       (ARRAY['low','medium','high'])[1 + ((n - 1) % 3)],
       (ARRAY['open','in_progress','resolved','closed'])[1 + ((n - 1) % 4)],
       now() - ((n % 120) || ' days')::interval
FROM generate_series(1, 100) AS n
ON CONFLICT (ticket_id) DO NOTHING;
