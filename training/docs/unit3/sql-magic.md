# 3.8 Query tables with `%%sql`

## Concept
Notebooks on this stack ship a **`%%sql` cell magic** — put it on the first line of a cell and write
plain SQL, exactly like Databricks. It runs through the pre-created **`spark`** session
([3.7](spark.md)), so it queries the **same governed `iceberg` catalog** that Trino, Superset, and
the Spark jobs use. Results render as a table.

No setup, no connection — `spark` and `%%sql` are already there when the notebook opens.

> `%%sql` is for **quick exploration** in a notebook. When you *build* Gold tables with the same
> SQL — `spark.sql("…")` in a real pipeline — that's [4.4](../unit4/spark-sql-gold.md).

## Lab

### Query any catalog table directly
Catalog tables need **no registration** — reference them as `iceberg.<namespace>.<table>`:

```sql
%%sql
SELECT * FROM iceberg.gold.daily_sales
ORDER BY order_date DESC
LIMIT 10
```

The cell returns the rows as a rendered table (a pandas DataFrame under the hood, capped at 1000
rows for display).

### Explore what's there
```sql
%%sql
SHOW NAMESPACES IN iceberg
```
```sql
%%sql
SHOW TABLES IN iceberg.gold
```
```sql
%%sql
DESCRIBE iceberg.gold.daily_sales
```

### Real analysis — joins & aggregation
`%%sql` handles full SQL, joins across namespaces included:

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
- Run SQL in a notebook with `%%sql`, against any `iceberg` catalog table — no setup
- Explore with `SHOW NAMESPACES / SHOW TABLES / DESCRIBE`
- Choose `%%sql` (display) vs `spark.sql()` (capture & keep working) appropriately
- Register a raw file as a temp view to `%%sql` it
