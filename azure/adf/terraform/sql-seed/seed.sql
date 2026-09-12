-- ShopFlow seed data (MS SQL / Azure SQL). Idempotent: safe to re-run.
-- Core OLTP tables ADF ingests: customers, products, orders, order_items.

IF OBJECT_ID('dbo.customers', 'U') IS NULL
  CREATE TABLE dbo.customers (
    customer_id      INT PRIMARY KEY,
    full_name        NVARCHAR(200) NOT NULL,
    email            NVARCHAR(255) NOT NULL UNIQUE,
    country          NVARCHAR(50)  NOT NULL,
    signup_date      DATE          NOT NULL,
    loyalty_tier     NVARCHAR(20)  NOT NULL DEFAULT 'none',   -- none | silver | gold
    marketing_opt_in BIT           NOT NULL DEFAULT 0
  );

IF OBJECT_ID('dbo.products', 'U') IS NULL
  CREATE TABLE dbo.products (
    product_id  INT PRIMARY KEY,
    name        NVARCHAR(200)  NOT NULL,
    category    NVARCHAR(50)   NOT NULL,
    price       DECIMAL(10, 2) NOT NULL,             -- current list price
    cost        DECIMAL(10, 2) NOT NULL,             -- supplier cost
    supplier_id INT            NULL,
    updated_at  DATETIME2      NOT NULL DEFAULT SYSUTCDATETIME()
  );

IF OBJECT_ID('dbo.orders', 'U') IS NULL
  CREATE TABLE dbo.orders (
    order_id    INT PRIMARY KEY,
    customer_id INT           NOT NULL REFERENCES dbo.customers(customer_id),
    channel     NVARCHAR(20)  NOT NULL,              -- web | app | marketplace | wholesale
    order_ts    DATETIME2     NOT NULL,
    status      NVARCHAR(20)  NOT NULL,              -- placed | shipped | delivered | cancelled
    currency    NVARCHAR(3)   NOT NULL DEFAULT 'USD',
    promo_id    INT           NULL
  );

IF OBJECT_ID('dbo.order_items', 'U') IS NULL
  CREATE TABLE dbo.order_items (
    order_id   INT            NOT NULL REFERENCES dbo.orders(order_id),
    product_id INT            NOT NULL REFERENCES dbo.products(product_id),
    quantity   INT            NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,              -- price captured at order time
    PRIMARY KEY (order_id, product_id)
  );

-- drives the metadata-driven ForEach/Copy pipeline
IF OBJECT_ID('dbo.metadata', 'U') IS NULL
  CREATE TABLE dbo.metadata (SchemaName NVARCHAR(50), TableName NVARCHAR(100));

IF NOT EXISTS (SELECT 1 FROM dbo.customers)
  INSERT INTO dbo.customers (customer_id, full_name, email, country, signup_date, loyalty_tier, marketing_opt_in) VALUES
    (1, N'Ava Smith',  N'ava@example.com',   N'UK', '2025-06-01', N'gold',   1),
    (2, N'Eddie Jones', N'eddie@example.com', N'US', '2025-08-15', N'silver', 0),
    (3, N'Lena Novak', N'lena@example.com',   N'DE', '2026-01-10', N'none',   1),
    (4, N'Raj Patel',  N'raj@example.com',    N'IN', '2026-03-20', N'silver', 1);

IF NOT EXISTS (SELECT 1 FROM dbo.products)
  INSERT INTO dbo.products (product_id, name, category, price, cost, supplier_id) VALUES
    (1, N'Wireless Mouse', N'Electronics',  25.00,  12.00, NULL),
    (2, N'Office Chair',   N'Furniture',   180.00, 110.00, NULL),
    (3, N'USB-C Cable',    N'Electronics',   9.99,   3.50, NULL),
    (4, N'Standing Desk',  N'Furniture',   420.00, 260.00, NULL),
    (5, N'Notebook',       N'Stationery',    4.50,   1.20, NULL);

IF NOT EXISTS (SELECT 1 FROM dbo.orders)
  INSERT INTO dbo.orders (order_id, customer_id, channel, order_ts, status, currency, promo_id) VALUES
    (1001, 1, N'web',         '2026-02-01T10:00:00', N'delivered', N'GBP', NULL),
    (1002, 2, N'app',         '2026-02-03T14:30:00', N'shipped',   N'USD', NULL),
    (1003, 1, N'web',         '2026-02-10T09:15:00', N'placed',    N'GBP', NULL),
    (1004, 3, N'marketplace', '2026-02-12T16:45:00', N'delivered', N'EUR', NULL),
    (1005, 4, N'app',         '2026-03-01T11:00:00', N'cancelled', N'USD', NULL);

IF NOT EXISTS (SELECT 1 FROM dbo.order_items)
  INSERT INTO dbo.order_items (order_id, product_id, quantity, unit_price) VALUES
    (1001, 1, 2, 25.00),
    (1001, 3, 1,  9.99),
    (1002, 2, 1, 180.00),
    (1003, 4, 1, 420.00),
    (1004, 5, 3,  4.50),
    (1004, 1, 1, 24.00),
    (1005, 3, 2,  9.50);

IF NOT EXISTS (SELECT 1 FROM dbo.metadata)
  INSERT INTO dbo.metadata (SchemaName, TableName) VALUES
    (N'dbo', N'customers'),
    (N'dbo', N'products'),
    (N'dbo', N'orders'),
    (N'dbo', N'order_items');
