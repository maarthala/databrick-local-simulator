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

### 1 · See what's already there
Before querying, look at what the catalog holds. `SHOW SCHEMAS IN iceberg` lists the
**namespaces** — the [medallion](../unit1/medallion.md) tiers `bronze` / `silver` / `gold`
(raw → cleaned → business-ready):

```sql
%%sql
SHOW SCHEMAS IN iceberg
```
> `SHOW NAMESPACES IN iceberg` is the same command — Iceberg calls schemas **namespaces**. These
> list **even when empty**, so a namespace you just created shows here (SQLPad's sidebar, by
> contrast, hides empty ones). On a fresh k8s stack the tiers exist but may be empty until the
> pipeline runs.

Then drill in — the tables in a namespace, and a table's columns:
```sql
%%sql
SHOW TABLES IN iceberg.gold
```
```sql
%%sql
DESCRIBE iceberg.gold.daily_sales
```

### 2 · Query a table
Catalog tables need **no registration** — reference them as `iceberg.<namespace>.<table>`:

```sql
%%sql
SELECT * FROM iceberg.gold.daily_sales
ORDER BY order_date DESC
LIMIT 10
```

The cell returns the rows as a rendered table (a pandas DataFrame under the hood, capped at 1000
rows for display).

### 3 · Joins & aggregation
`%%sql` handles full SQL, joins across namespaces included:

```sql
%%sql
SELECT c.country, count(*) AS orders, sum(o.amount) AS revenue
FROM iceberg.silver.orders o
JOIN iceberg.silver.customers c ON c.customer_id = o.customer_id
GROUP BY c.country
ORDER BY revenue DESC
```

### 4 · Create your own schema & table
`%%sql` isn't read-only — you can **create** objects too. Make a scratch **namespace**, add a
table, and put a couple of rows in it (one statement per cell, no `;`):

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
  (1, 'Ada Lovelace', 'UK'),
  (2, 'Alan Turing',  'UK')
```
```sql
%%sql
SELECT * FROM iceberg.sandbox.dim_customer
```

Your table is now a **real, governed Iceberg table** — visible to Trino, Superset, SQLPad, and the
Polaris Console, exactly like the pipeline's tables. Tidy up when done:
```sql
%%sql
DROP TABLE iceberg.sandbox.dim_customer
```

!!! warning "On k8s the lakehouse is governed"
    Creating a schema or table needs the right **Polaris grant** (`CREATE_NAMESPACE` /
    `TABLE_CREATE`). If you get a **403 / not-authorized** (rather than a SQL error), that's RBAC,
    not your SQL — see [Unit 6](../unit6/polaris.md). Locally you have full access.

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
df = spark.sql("SELECT * FROM iceberg.gold.daily_sales WHERE order_date >= '2023-08-01'")
df.groupBy().sum("revenue").show()      # keep working with the DataFrame
```

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
