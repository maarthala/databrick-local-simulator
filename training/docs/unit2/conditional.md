# 2.5 Conditional logic, NULLs & filtering

## Concept
Raw data is messy: missing values, codes that need labels, categories you want as columns.
Four everyday tools handle almost all of it — and you'll use them in **every** transform:

- **`CASE`** — SQL's if/else. Turn values into labels, buckets, or flags.
- **Conditional aggregation** — `SUM(CASE WHEN …)` or the `FILTER (WHERE …)` clause to
  compute *"how many of X"* per group, or to **pivot** rows into columns.
- **`COALESCE` / `NULLIF`** — handle `NULL`s: supply a default, or guard against divide-by-zero.
- **`CAST` / `TRY_CAST`** — convert types safely (text → number, timestamp → date).

## Lab
> Run these in the **Trino CLI** or **Superset SQL Lab** (see [2.1](intro.md)). In Superset,
> pick the **shopflow / public** schema and skip the `USE` line below.

```sql
USE shopflow.public;
```

**`CASE` — label each order's outcome:**

```sql
SELECT status,
       CASE
         WHEN status = 'delivered' THEN 'revenue'
         WHEN status = 'cancelled' THEN 'lost'
         ELSE 'in progress'
       END AS outcome,
       count(*) AS orders
FROM orders
GROUP BY status
ORDER BY orders DESC;
```

**Conditional aggregation — many counts in one row.** `FILTER (WHERE …)` and
`SUM(CASE WHEN …)` do the same thing; here per country:

```sql
SELECT c.country,
       count(*)                                              AS total_orders,
       count(*) FILTER (WHERE o.status = 'delivered')        AS delivered,
       count(*) FILTER (WHERE o.status = 'cancelled')        AS cancelled,
       sum(CASE WHEN o.status = 'delivered' THEN 1 ELSE 0 END) AS delivered_via_case
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.country
ORDER BY total_orders DESC;
```

**Pivot rows into columns** — revenue per category *split by channel*, using conditional
aggregation (the classic "SQL pivot"):

```sql
SELECT p.category,
       sum(CASE WHEN o.channel = 'web'         THEN oi.quantity*oi.unit_price END) AS web_rev,
       sum(CASE WHEN o.channel = 'app'         THEN oi.quantity*oi.unit_price END) AS app_rev,
       sum(CASE WHEN o.channel = 'marketplace' THEN oi.quantity*oi.unit_price END) AS market_rev
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products   p  ON p.product_id = oi.product_id
WHERE o.status = 'delivered'
GROUP BY p.category
ORDER BY p.category;
```

**`COALESCE` — supply a default for `NULL`.** `promo_id` is `NULL` when no promotion applied:

```sql
SELECT order_id,
       COALESCE(CAST(promo_id AS varchar), 'no promo') AS promo
FROM orders
LIMIT 10;
```

**`NULLIF` — guard against divide-by-zero.** Cancellation rate per country:

```sql
SELECT c.country,
       count(*) FILTER (WHERE o.status = 'cancelled') AS cancelled,
       count(*)                                       AS total,
       round(100.0 * count(*) FILTER (WHERE o.status = 'cancelled')
             / NULLIF(count(*), 0), 1)                AS cancel_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.country
ORDER BY cancel_pct DESC;
```

**`CAST` / `TRY_CAST` — convert types.** `TRY_CAST` returns `NULL` instead of erroring on
bad input (invaluable when ingesting dirty data):

```sql
SELECT CAST(order_ts AS date)      AS order_date,   -- timestamp → date
       TRY_CAST(currency AS integer) AS bad_cast     -- 'USD' → NULL, no error
FROM orders
LIMIT 5;
```

!!! tip "`FILTER` vs `CASE`"
    `count(*) FILTER (WHERE …)` is the cleaner, modern form and works on **Trino, Spark/
    Databricks, and Postgres**. `SUM(CASE WHEN … THEN 1 ELSE 0 END)` is the universal form
    that *also* works on **Snowflake and Fabric (T-SQL)**. When in doubt, reach for `CASE`.

## Challenge
Build a **channel scorecard**: one row per `channel` showing total orders, delivered orders,
delivered %, cancelled %, and total delivered revenue. Sort by delivered revenue, highest first.

??? note "Solution"
    ```sql
    SELECT o.channel,
           count(*)                                        AS orders,
           count(*) FILTER (WHERE o.status = 'delivered')  AS delivered,
           round(100.0 * count(*) FILTER (WHERE o.status = 'delivered')
                 / NULLIF(count(*), 0), 1)                 AS delivered_pct,
           round(100.0 * count(*) FILTER (WHERE o.status = 'cancelled')
                 / NULLIF(count(*), 0), 1)                 AS cancelled_pct,
           round(sum(CASE WHEN o.status = 'delivered'
                          THEN oi.quantity*oi.unit_price ELSE 0 END), 2) AS delivered_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY o.channel
    ORDER BY delivered_revenue DESC;
    ```

!!! tip "🎯 This runs unchanged on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** used `CASE`, conditional aggregation (pivot), `COALESCE`/`NULLIF`,
    and `CAST`/`TRY_CAST` to shape and clean data.

    - **Azure Databricks** / **Snowflake** — `CASE`, `COALESCE`, `NULLIF`, `CAST`/`TRY_CAST`
      and `SUM(CASE WHEN …)` pivots are standard ANSI SQL and run unchanged.
    - **Microsoft Fabric** — same in the SQL endpoint (T-SQL uses `TRY_CAST`/`TRY_CONVERT`;
      pivots via `CASE` or the `PIVOT` operator).
    - **Azure Data Factory** — the no-code analog is the **Derived Column** (CASE/coalesce
      expressions) and **Pivot** transformations in a Mapping Data Flow.

    Only the `FILTER (WHERE …)` shorthand isn't on Snowflake/Fabric — the `CASE` form is
    100% portable.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **`CASE WHEN`** | SQL if/else — derive labels, buckets, flags |
| **Conditional aggregation** | Count/sum only rows meeting a condition, per group |
| **`FILTER (WHERE …)`** | Cleaner shorthand for conditional aggregation |
| **Pivot** | Turn row values into columns via `SUM(CASE WHEN …)` |
| **`COALESCE`** | First non-`NULL` value — supply a default |
| **`NULLIF(a,b)`** | `NULL` when `a=b` — classic divide-by-zero guard |
| **`CAST` / `TRY_CAST`** | Convert types; `TRY_` yields `NULL` instead of erroring |

## You can now…
- Turn values into labels and buckets with `CASE`
- Compute per-group conditional counts and **pivot** rows into columns
- Handle `NULL`s safely with `COALESCE` and `NULLIF`
- Convert types with `CAST`, and survive dirty input with `TRY_CAST`
