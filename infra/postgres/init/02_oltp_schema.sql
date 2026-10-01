-- =====================================================================
-- DataLab Productivo Local — Esquema OLTP del e-commerce
-- Documentos: docs/architecture/data-pipeline.md §2-3 (origen del pipeline)
--             docs/infrastructure/docker-setup.md (servicio `oltp-postgres`)
-- Script 02 de 03: tablas e índices. Semilla de datos en 03_oltp_seed.sql.
--
-- Base: ecommerce_oltp (POSTGRES_OLTP_DB) · schema `public`
-- Toda tabla lleva `updated_at`: es la clave incremental (watermark) de la
-- extracción hacia s3://datalake/bronze/<entidad>/dt=YYYY-MM-DD/.
-- Idempotente: CREATE TABLE / INDEX IF NOT EXISTS.
-- =====================================================================

\set ON_ERROR_STOP on
\connect ecommerce_oltp

CREATE TABLE IF NOT EXISTS public.customers (
    customer_id  TEXT PRIMARY KEY,
    full_name    TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    phone        TEXT,
    city         TEXT NOT NULL,
    region       TEXT NOT NULL,
    segment      TEXT NOT NULL DEFAULT 'retail' CHECK (segment IN ('retail','pyme','enterprise')),
    gender       TEXT CHECK (gender IN ('f','m','x')),
    age_band     TEXT CHECK (age_band IN ('18-24','25-34','35-44','45-54','55+')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.sellers (
    seller_id      TEXT PRIMARY KEY,
    seller_name    TEXT NOT NULL,
    region         TEXT NOT NULL,
    channel        TEXT NOT NULL CHECK (channel IN ('marketplace','directo','partner')),
    joined_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.products (
    product_id   TEXT PRIMARY KEY,
    sku          TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    brand        TEXT NOT NULL,
    unit_price   NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    cost_amount  NUMERIC(12,2) NOT NULL CHECK (cost_amount >= 0),
    seller_id    TEXT REFERENCES public.sellers(seller_id),
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.orders (
    order_id     TEXT PRIMARY KEY,
    customer_id  TEXT NOT NULL REFERENCES public.customers(customer_id),
    order_ts     TIMESTAMPTZ NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('pending','paid','shipped','delivered',
                                                'cancelled','refunded')),
    channel      TEXT NOT NULL DEFAULT 'web',
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id      TEXT NOT NULL REFERENCES public.orders(order_id) ON DELETE CASCADE,
    product_id    TEXT NOT NULL REFERENCES public.products(product_id),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    discount_pct  NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 100),
    line_total    NUMERIC(12,2) NOT NULL CHECK (line_total >= 0),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (order_id, product_id)
);

CREATE TABLE IF NOT EXISTS public.payments (
    payment_id     TEXT PRIMARY KEY,
    order_id       TEXT NOT NULL REFERENCES public.orders(order_id) ON DELETE CASCADE,
    paid_at        TIMESTAMPTZ NOT NULL,
    payment_method TEXT NOT NULL CHECK (payment_method IN ('card','transfer','wallet','cash')),
    paid_amount    NUMERIC(12,2) NOT NULL CHECK (paid_amount >= 0),
    payment_status TEXT NOT NULL CHECK (payment_status IN ('approved','pending','rejected','refunded')),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.support_tickets (
    ticket_id   TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES public.customers(customer_id),
    order_id    TEXT REFERENCES public.orders(order_id),
    opened_at   TIMESTAMPTZ NOT NULL,
    topic       TEXT NOT NULL,
    priority    TEXT NOT NULL CHECK (priority IN ('low','medium','high')),
    status      TEXT NOT NULL CHECK (status IN ('open','in_progress','resolved','closed')),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices: extracción incremental (updated_at/opened_at) y explotación OLTP.
CREATE INDEX IF NOT EXISTS idx_customers_updated_at    ON public.customers (updated_at);
CREATE INDEX IF NOT EXISTS idx_products_updated_at     ON public.products (updated_at);
CREATE INDEX IF NOT EXISTS idx_sellers_updated_at      ON public.sellers (updated_at);
CREATE INDEX IF NOT EXISTS idx_orders_updated_at       ON public.orders (updated_at);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id      ON public.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id    ON public.order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id       ON public.payments (order_id);
CREATE INDEX IF NOT EXISTS idx_payments_updated_at     ON public.payments (updated_at);
CREATE INDEX IF NOT EXISTS idx_support_tickets_opened  ON public.support_tickets (opened_at);

-- Continúa en 03_oltp_seed.sql (semilla reproducible e idempotente).
