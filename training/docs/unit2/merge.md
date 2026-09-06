# 2.6 Changing data: MERGE & upserts

## Concept
Everything so far only **read** data. But data engineering is mostly about **changing** a
target table as new data arrives: apply updates, add new rows, remove deleted ones — without
duplicating anything. The workhorse for this is **`MERGE`** (a.k.a. **upsert** =
*update-or-insert*):

```
MERGE INTO target  USING source  ON <match>
  WHEN MATCHED       THEN UPDATE / DELETE
  WHEN NOT MATCHED   THEN INSERT
```

In one atomic statement it decides, row by row, whether each incoming record is an **update**
to an existing row or a **brand-new** row. This is exactly how you'll build the **Silver**
layer in [Unit 4](../unit4/transform-silver.md): merge each day's changed and late-arriving
orders into the clean table.

!!! note "Why we need a lakehouse table for this"
    You can't `MERGE` a folder of files, and you shouldn't write to the live `shopflow`
    source (it's read-only for us). `MERGE`, `UPDATE`, and `DELETE` need the **ACID table
    format** from [1.3](../unit1/formats.md). So this lab writes to a scratch **Iceberg**
    table in the `iceberg` catalog — a real lakehouse table you can safely experiment on.

## Lab
> Run these in the **Trino CLI** or **Superset SQL Lab** (see [2.1](intro.md)). This lab
> **writes**, so it uses the `iceberg` catalog (fully qualified), not `shopflow`.

**Set up a scratch table** (your own sandbox — the source stays untouched):

```sql
CREATE SCHEMA IF NOT EXISTS iceberg.sandbox;

DROP TABLE IF EXISTS iceberg.sandbox.dim_customer;
CREATE TABLE iceberg.sandbox.dim_customer (
  customer_id int,
  full_name   varchar,
  country     varchar,
  updated_at  date
);

INSERT INTO iceberg.sandbox.dim_customer VALUES
  (1, 'Ada Lovelace', 'UK', DATE '2024-01-01'),
  (2, 'Alan Turing',  'UK', DATE '2024-01-01');
```

**The upsert** — a daily batch with one *changed* customer and one *new* one:

```sql
MERGE INTO iceberg.sandbox.dim_customer AS t
USING (VALUES
         (2, 'Alan M. Turing', 'UK', DATE '2024-06-01'),   -- changed name
         (3, 'Grace Hopper',   'US', DATE '2024-06-01')     -- brand new
      ) AS s(customer_id, full_name, country, updated_at)
ON t.customer_id = s.customer_id
WHEN MATCHED     THEN UPDATE SET full_name = s.full_name, updated_at = s.updated_at
WHEN NOT MATCHED THEN INSERT (customer_id, full_name, country, updated_at)
                     VALUES (s.customer_id, s.full_name, s.country, s.updated_at);

SELECT * FROM iceberg.sandbox.dim_customer ORDER BY customer_id;
-- id 2 updated, id 3 inserted, id 1 untouched
```

**Conditional match — only update if the incoming row is *newer*** (`WHEN MATCHED AND …`).
Late/out-of-order data is real (remember the ShopFlow event stream), so you often guard updates:

```sql
MERGE INTO iceberg.sandbox.dim_customer AS t
USING (VALUES (1, 'Ada L.', DATE '2023-12-01')) AS s(customer_id, full_name, updated_at)
ON t.customer_id = s.customer_id
WHEN MATCHED AND s.updated_at > t.updated_at
     THEN UPDATE SET full_name = s.full_name, updated_at = s.updated_at;
-- no-op: the incoming row is OLDER than what's already there
```

**Delete through MERGE** (e.g. a GDPR erasure request):

```sql
MERGE INTO iceberg.sandbox.dim_customer AS t
USING (VALUES (3)) AS s(customer_id)
ON t.customer_id = s.customer_id
WHEN MATCHED THEN DELETE;
```

**Plain `UPDATE` / `DELETE`** also work on a lakehouse table:

```sql
UPDATE iceberg.sandbox.dim_customer SET country = 'United Kingdom' WHERE country = 'UK';
DELETE FROM iceberg.sandbox.dim_customer WHERE customer_id = 1;
SELECT * FROM iceberg.sandbox.dim_customer ORDER BY customer_id;
```

!!! tip "MERGE makes pipelines *idempotent*"
    Re-run the upsert with the same batch and the result is identical — no duplicates. That
    **idempotency** (from [1.1](../unit1/what-is-de.md)) is what lets you safely re-run a
    failed job or backfill a day without corrupting the table.

## Challenge
Create `iceberg.sandbox.orders_silver (order_id int, status varchar, updated_at date)` and seed
it with two delivered orders. Then MERGE a daily batch that (a) updates order 1's status to
`returned`, (b) inserts a new order 3, and (c) tries to update order 2 with an **older**
timestamp (which should be ignored). Verify the final table.

??? note "Solution"
    ```sql
    DROP TABLE IF EXISTS iceberg.sandbox.orders_silver;
    CREATE TABLE iceberg.sandbox.orders_silver (order_id int, status varchar, updated_at date);
    INSERT INTO iceberg.sandbox.orders_silver VALUES
      (1, 'delivered', DATE '2024-05-01'),
      (2, 'delivered', DATE '2024-05-02');

    MERGE INTO iceberg.sandbox.orders_silver AS t
    USING (VALUES
             (1, 'returned',  DATE '2024-05-10'),   -- newer update
             (2, 'cancelled', DATE '2024-04-01'),   -- OLDER → ignore
             (3, 'delivered', DATE '2024-05-11')    -- new
          ) AS s(order_id, status, updated_at)
    ON t.order_id = s.order_id
    WHEN MATCHED AND s.updated_at > t.updated_at
         THEN UPDATE SET status = s.status, updated_at = s.updated_at
    WHEN NOT MATCHED
         THEN INSERT (order_id, status, updated_at) VALUES (s.order_id, s.status, s.updated_at);

    SELECT * FROM iceberg.sandbox.orders_silver ORDER BY order_id;
    -- 1 → returned, 2 → still delivered (older ignored), 3 → inserted
    ```

!!! tip "🎯 This runs unchanged on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** upserted a table with `MERGE` (`WHEN MATCHED` / `WHEN NOT MATCHED`),
    conditional updates, and `DELETE` — the core of building Silver.

    - **Azure Databricks** — `MERGE INTO` on a Delta table is near-identical (this is *the*
      Databricks Silver-build pattern; `WHEN NOT MATCHED BY SOURCE` adds deletes).
    - **Snowflake** — the same `MERGE INTO … WHEN MATCHED / WHEN NOT MATCHED` on a table.
    - **Microsoft Fabric** — `MERGE` in the Warehouse (T-SQL); Spark `MERGE INTO` in a Lakehouse.
    - **Azure Data Factory** — the no-code analog is the **Alter Row** transformation
      (upsert/update/delete policies) writing to a sink.

    `MERGE` is one of the highest-value DE skills — and it's essentially portable everywhere.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Upsert** | Insert new rows, update existing ones — in one step |
| **`MERGE INTO`** | The SQL statement that performs an upsert |
| **`WHEN MATCHED`** | What to do when the key already exists (UPDATE/DELETE) |
| **`WHEN NOT MATCHED`** | What to do for brand-new keys (INSERT) |
| **Conditional merge** | `WHEN MATCHED AND <cond>` — e.g. only update if newer |
| **Idempotent** | Re-running gives the same result (no duplicates) |
| **Late-arriving data** | Records that show up out of order — guard with a condition |

## You can now…
- Upsert a table with `MERGE` using `WHEN MATCHED` / `WHEN NOT MATCHED`
- Guard updates against older/late data with `WHEN MATCHED AND …`
- Delete through MERGE, and run plain `UPDATE` / `DELETE` on lakehouse tables
- Explain why MERGE needs a table format and how it makes pipelines idempotent
