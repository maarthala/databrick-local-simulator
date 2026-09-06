-- ShopFlow OLTP schema + a realistic generated dataset (the live application database,
-- i.e. the source system). Loaded into the stack's Postgres as database `shopflow`.
--
-- This seeds the FOUR core tables (customers, products, orders, order_items) with enough
-- volume to practice real SQL: ~2,000 customers, ~200 products, ~40,000 orders, and
-- ~100,000 order items spread over two years. The richer tables in the schema docs
-- (returns, payments, inventory, …) are added later as the course needs them.
--
-- Re-runnable: it drops and recreates the database from scratch.

DROP DATABASE IF EXISTS shopflow;
CREATE DATABASE shopflow;
\connect shopflow

-- ---------------------------------------------------------------------------
-- Schema (core tables)
-- ---------------------------------------------------------------------------
CREATE TABLE customers (
  customer_id      SERIAL PRIMARY KEY,
  full_name        TEXT NOT NULL,
  email            TEXT UNIQUE NOT NULL,
  country          TEXT NOT NULL,
  signup_date      DATE NOT NULL,
  loyalty_tier     TEXT NOT NULL DEFAULT 'none',   -- none | silver | gold
  marketing_opt_in BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE products (
  product_id   SERIAL PRIMARY KEY,
  name         TEXT NOT NULL,
  category     TEXT NOT NULL,
  price        NUMERIC(10,2) NOT NULL,            -- current list price
  cost         NUMERIC(10,2) NOT NULL,            -- what ShopFlow pays the supplier
  supplier_id  INT,                               -- FK to suppliers (not seeded yet)
  updated_at   TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE orders (
  order_id     SERIAL PRIMARY KEY,
  customer_id  INT NOT NULL REFERENCES customers(customer_id),
  channel      TEXT NOT NULL,                     -- web | app | marketplace | wholesale
  order_ts     TIMESTAMP NOT NULL,
  status       TEXT NOT NULL,                     -- placed | shipped | delivered | cancelled
  currency     TEXT NOT NULL DEFAULT 'USD',
  promo_id     INT                                -- FK to promotions (not seeded yet)
);

CREATE TABLE order_items (
  order_id    INT NOT NULL REFERENCES orders(order_id),
  product_id  INT NOT NULL REFERENCES products(product_id),
  quantity    INT NOT NULL,
  unit_price  NUMERIC(10,2) NOT NULL,             -- price captured at order time
  PRIMARY KEY (order_id, product_id)
);

-- ---------------------------------------------------------------------------
-- Data generation
-- ---------------------------------------------------------------------------

-- 6,000 customers across several countries, signed up over ~2.5 years.
-- (Many will never place an order — like a real signup base — see the orders step.)
INSERT INTO customers (full_name, email, country, signup_date, loyalty_tier, marketing_opt_in)
SELECT
  'Customer ' || g,
  'customer' || g || '@example.com',
  (ARRAY['US','US','UK','UK','DE','FR','IN','CA','AU'])[1 + floor(random()*9)::int],
  DATE '2023-01-01' + (random()*900)::int,
  (ARRAY['none','none','none','none','silver','silver','gold'])[1 + floor(random()*7)::int],
  (random() < 0.6)
FROM generate_series(1, 6000) AS g;

-- 200 products across categories; cost is 40–70% of price (so margin is learnable)
INSERT INTO products (name, category, price, cost, supplier_id, updated_at)
SELECT name, category, price,
       round((price * (0.4 + random()*0.3))::numeric, 2) AS cost,
       supplier_id, now()
FROM (
  SELECT 'Product ' || g AS name,
         (ARRAY['Electronics','Furniture','Stationery','Clothing','Home & Kitchen','Sports','Books','Toys'])[1 + floor(random()*8)::int] AS category,
         round((5 + random()*495)::numeric, 2) AS price,
         1 + floor(random()*20)::int AS supplier_id
  FROM generate_series(1, 200) AS g
) t;

-- 40,000 orders over two years; status weighted toward 'delivered'.
-- Customer assignment is deliberately SKEWED (power curve) so the data has a realistic
-- long tail: a few high-volume "whale" customers, many one-time buyers, and some who
-- never order at all — which makes repeat-rate, LEFT JOIN, and cohort analysis meaningful.
INSERT INTO orders (customer_id, channel, order_ts, status, currency)
SELECT
  1 + LEAST(floor(-ln(1 - random()) * 500)::int, 5999),
  (ARRAY['web','web','web','app','app','marketplace','wholesale'])[1 + floor(random()*7)::int],
  TIMESTAMP '2023-06-01 00:00:00'
    + (random()*730)::int * INTERVAL '1 day'
    + (random()*86400)::int * INTERVAL '1 second',
  (ARRAY['delivered','delivered','delivered','delivered','delivered','delivered',
         'delivered','shipped','placed','cancelled'])[1 + floor(random()*10)::int],
  (ARRAY['USD','USD','USD','GBP','EUR','INR'])[1 + floor(random()*6)::int]
FROM generate_series(1, 40000) AS g;

-- 1–4 distinct products per order (~100k line items); unit_price = price at order time
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 1 + floor(random()*5)::int, p.price
FROM orders o
CROSS JOIN LATERAL (
  SELECT product_id, price
  FROM products
  ORDER BY random()
  LIMIT (1 + (o.order_id % 4))          -- 1–4 distinct products, varies per order
) AS p;

-- Quick sanity output
SELECT 'customers'   AS table, count(*) FROM customers
UNION ALL SELECT 'products',    count(*) FROM products
UNION ALL SELECT 'orders',      count(*) FROM orders
UNION ALL SELECT 'order_items', count(*) FROM order_items;
