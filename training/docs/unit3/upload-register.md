# 3.9 Upload a file & register it as a table

## Concept
A very common real task: someone hands you a file, you drop it in the **data lake** (MinIO), then
make it a **catalog table** so everyone can query it in SQL and Spark — governed, shared, and
addressable as `iceberg.<namespace>.<table>`.

Three moves: **upload → read → register**. Then it's a first-class table in the `iceberg` catalog,
visible to notebooks, Trino, Superset, and the Polaris Console.

## Lab

### 1 · Upload the file to the lake (MinIO)
Open the **MinIO console** at <http://localhost:9001> (login `minioadmin` / `minioadmin`):

1. Go to bucket **`demo-bucket`**.
2. Create/enter a folder, e.g. **`uploads/`**.
3. **Upload** your file — say `customers.csv`.

The object is now at **`s3a://demo-bucket/uploads/customers.csv`**. (Any client works too — MinIO is
S3-compatible — but the console needs no tooling.)

### 2 · Read it in the notebook
`spark` is already there ([3.7](spark.md)). Point it at the path:

```python
df = (spark.read
        .option("header", True)        # first row is column names
        .option("inferSchema", True)   # detect types (int/double/…)
        .csv("s3a://demo-bucket/uploads/customers.csv"))

df.printSchema()
df.show(5)
```

For Parquet it's just `spark.read.parquet("s3a://demo-bucket/uploads/…")` (schema is built in — no
options needed).

### 3 · Register it as a catalog table
Write the DataFrame into the governed **`iceberg`** catalog. Pick (or create) a namespace, then
create the table:

```python
spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.bronze")

df.writeTo("iceberg.bronze.customers_upload").createOrReplace()
```

- **`writeTo("iceberg.bronze.customers_upload")`** — target table in `iceberg` → namespace `bronze`.
- **`.createOrReplace()`** — create it (or replace if re-running). The data is written as Iceberg
  files in MinIO and the table is registered in Polaris.

!!! tip "SQL-only alternative"
    Same result without the DataFrame step:
    ```sql
    %%sql
    CREATE TABLE iceberg.bronze.customers_upload USING iceberg AS
    SELECT * FROM csv.`s3a://demo-bucket/uploads/customers.csv`
    ```

### 4 · Access it — SQL and Spark
It's now a normal catalog table. Query it any way:

```sql
%%sql
SELECT * FROM iceberg.bronze.customers_upload LIMIT 10
```

```python
df = spark.table("iceberg.bronze.customers_upload")   # or spark.sql("SELECT ...")
df.count()
```

The same table is now visible in **Trino**, **Superset**, and the **Polaris Console** — one governed
copy, every engine.

### Just exploring? Use a temp view instead
If you only need to poke at a file for this session (no permanent table), skip the catalog and
register a **temp view** — no write, no namespace:

```python
spark.read.option("header", True).csv("s3a://demo-bucket/uploads/customers.csv") \
     .createOrReplaceTempView("customers_tmp")
```
```sql
%%sql
SELECT count(*) FROM customers_tmp
```
The view disappears when the kernel stops; a catalog table persists and is shared.

## 🎯 This runs unchanged on Azure, Databricks, Snowflake & Fabric
Upload to **ADLS / S3**, then `CREATE TABLE … AS SELECT` or `writeTo(...).createOrReplace()` into
**the Databricks catalog** / **Snowflake** / **Fabric** — the exact same read-then-register
pattern; only the storage URL and catalog name change.

## You can now…
- Upload a file to the data lake via the MinIO console
- Read a CSV/Parquet from `s3a://…` in a notebook
- **Register** it as a governed `iceberg` catalog table (`writeTo().createOrReplace()` or `CREATE TABLE AS`)
- Query it from SQL, Spark, Trino, and Superset — and know when a **temp view** is enough instead
