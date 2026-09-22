# 3.8 Query tables with `%%sql`

## Concept
Notebooks on this stack ship a **`%%sql` cell magic** — put it on the first line of a cell and write
plain SQL, exactly like Databricks. It runs through the pre-created **`spark`** session
([3.7](spark.md)), so it queries the **same governed `iceberg` catalog** that Trino, Superset, and
the Spark jobs use. Results render as a table.

No setup, no connection — `spark` and `%%sql` are already there when the notebook opens.

> `%%sql` is for **quick exploration** in a notebook. When you *build* Gold tables with the same
> SQL — `spark.sql("…")` in a real pipeline — that's [4.4](../unit4/spark-sql-gold.md).

!!! info "Three rules for every `%%sql` cell"
    1. **Qualify with the catalog** — `iceberg.<namespace>.<table>`. A bare `SHOW SCHEMAS` or
       `orders` targets Spark's *default* catalog (not the lakehouse) and errors.
    2. **No trailing `;`** — `%%sql` runs one `spark.sql(...)`, and Spark's parser rejects a
       trailing semicolon.
    3. **One statement per cell** — unlike SQLPad, you can't stack several with `;`.

## Lab

### 1 · See what namespaces exist
First, look at what the catalog holds. `SHOW SCHEMAS IN iceberg` lists the **namespaces** — the
[medallion](../unit1/medallion.md) tiers `bronze` / `silver` / `gold` (raw → cleaned →
business-ready):

```sql
%%sql
SHOW SCHEMAS IN iceberg
```
> `SHOW NAMESPACES IN iceberg` is the same command — Iceberg calls schemas **namespaces**. They
> list **even when empty** (SQLPad's sidebar, by contrast, hides empty ones).

!!! note "The medallion tiers are empty right now — that's expected"
    `bronze` / `silver` / `gold` are **built later, in [Unit 4](../unit4/fundamentals.md)** (Spark
    reads the sources and writes these tables). Following the course in order, they exist as
    namespaces but hold **no tables yet** — so `SELECT * FROM iceberg.gold.…` would say *table not
    found*. No problem: below you'll **create your own schema and data** to practise on, then meet
    the pipeline's tables in Unit 4.

### 2 · Create your own schema, table & data
`%%sql` isn't read-only — you can **create** objects. Make a scratch **namespace**, add a table,
and insert a few rows (one statement per cell, no `;`):

```sql
%%sql
CREATE SCHEMA IF NOT EXISTS iceberg.sandbox
```
> `CREATE SCHEMA` = `CREATE NAMESPACE` = `CREATE DATABASE` in Spark — all synonyms.
> `IF NOT EXISTS` makes it safe to re-run.

```sql
%%sql
CREATE TABLE IF NOT EXISTS iceberg.sandbox.dim_customer (
  customer_id int,
  full_name   string,
  country     string
)
```
> Note Spark's type names: **`string`** (not `varchar`), `int`, `double`, `date`, … Because the
> `iceberg` catalog *is* an Iceberg catalog, the table is created as **Iceberg** automatically —
> no `USING iceberg` needed.

```sql
%%sql
INSERT INTO iceberg.sandbox.dim_customer VALUES
  (1, 'Ada Lovelace',      'UK'),
  (2, 'Alan Turing',       'UK'),
  (3, 'Grace Hopper',      'US'),
  (4, 'Katherine Johnson', 'US')
```

!!! warning "On k8s the lakehouse is governed"
    Creating a schema or table needs the right **Polaris grant** (`CREATE_NAMESPACE` /
    `TABLE_CREATE`). If you get a **403 / not-authorized** (rather than a SQL error), that's RBAC,
    not your SQL — see [Unit 6](../unit6/polaris.md). Locally you have full access.

### 3 · Explore & query your data
`sandbox` now has a table — discover and query it exactly as you would any catalog table:

```sql
%%sql
SHOW TABLES IN iceberg.sandbox          -- your new table shows up
```
```sql
%%sql
DESCRIBE iceberg.sandbox.dim_customer   -- columns + types
```
```sql
%%sql
SELECT * FROM iceberg.sandbox.dim_customer
```
```sql
%%sql
SELECT country, count(*) AS customers
FROM iceberg.sandbox.dim_customer
GROUP BY country
ORDER BY customers DESC
```

The result renders as a table (a pandas DataFrame under the hood, ≤1000 rows for display). Your
table is a **real, governed Iceberg table** — visible to Trino, Superset, SQLPad, and the Polaris
Console. Tidy up when you're done experimenting:
```sql
%%sql
DROP TABLE iceberg.sandbox.dim_customer
```

### 4 · The same `%%sql`, on the pipeline's tables (after Unit 4)
Once [Unit 4](../unit4/fundamentals.md) has built Bronze → Silver → Gold, the **identical** `%%sql`
queries them — no new skills, just real tables. A Gold lookup:

```sql
%%sql
SELECT * FROM iceberg.gold.daily_sales
ORDER BY order_date DESC
LIMIT 10
```

…and a join across namespaces (Silver):

```sql
%%sql
SELECT c.country, count(*) AS orders, sum(o.amount) AS revenue
FROM iceberg.silver.orders o
JOIN iceberg.silver.customers c ON c.customer_id = o.customer_id
GROUP BY c.country
ORDER BY revenue DESC
```

### `%%sql` vs `spark.sql(...)`
Two ways to run SQL — pick by what you need next:

| | `%%sql` (cell magic) | `spark.sql("...")` (Python) |
|---|---|---|
| Best for | quick look, exploring, final display | capturing results to keep working in Python |
| Returns | a rendered table (pandas, ≤1000 rows) | a **Spark DataFrame** (lazy, full size) |
| Capture to a variable | ✗ (display only) | ✓ `df = spark.sql(...)` |

So explore with `%%sql`; when you need to **use** the result (transform, join in Python, write it
back), switch to `spark.sql(...)`:

```python
df = spark.sql("SELECT * FROM iceberg.sandbox.dim_customer WHERE country = 'UK'")
df.count()                              # keep working with the DataFrame in Python
```
(After Unit 4 the same pattern captures a Gold table:
`spark.sql("SELECT * FROM iceberg.gold.daily_sales")`.)

!!! tip "Raw files need a view first"
    `%%sql` works on **catalog tables** with no setup. To `%%sql` a raw file in object storage,
    register it as a temp view once (see [3.9](upload-register.md)):
    ```python
    spark.read.parquet("s3a://demo-bucket/shopflow/history/orders") \
         .createOrReplaceTempView("orders_hist")
    ```
    ```sql
    %%sql
    SELECT status, count(*) FROM orders_hist GROUP BY status
    ```
    The view lives only for this kernel session; catalog tables persist.

## 🎯 This runs unchanged on Azure, Databricks, Snowflake & Fabric
`%%sql` **is** Databricks' notebook SQL cell. Same idea in Snowflake worksheets and Fabric
notebooks — write SQL against the catalog, get a table back. The `catalog.schema.table` addressing is
identical.

## You can now…
- Run SQL in a notebook with `%%sql` — qualifying the `iceberg` catalog, no `;`, one per cell
- **Discover** what exists with `SHOW SCHEMAS / SHOW TABLES / DESCRIBE IN iceberg`
- **Create** your own namespace, table, and rows (`CREATE SCHEMA` / `CREATE TABLE` / `INSERT`)
- Choose `%%sql` (display) vs `spark.sql()` (capture & keep working) appropriately
- Register a raw file as a temp view to `%%sql` it
