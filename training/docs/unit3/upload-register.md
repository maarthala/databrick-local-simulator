# 3.9 Upload a file & register it as a table

## Concept
A very common real task: someone hands you a file, you drop it in the **data lake** (MinIO), then
make it a **catalog table** so everyone can query it in SQL and Spark — governed, shared, and
addressable as `iceberg.<namespace>.<table>`.

Three moves: **upload → read → register**. Then it's a first-class table in the `iceberg` catalog,
visible to notebooks, Trino, Superset, and the Polaris Console.

> This is the ad-hoc *"someone handed me a file"* version. Ingesting ShopFlow's own sources
> (Postgres + Parquet) into Bronze systematically — the pipeline version — is
> [4.2](../unit4/read-bronze.md).

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

#### SQL-only alternative — and getting the **column names** right
You can register the file without the DataFrame step, but there's a trap. The obvious one-liner
**does not work well for CSVs with a header**:

```sql
%%sql
-- DON'T: the csv.`path` shorthand accepts NO options, so it can't set header=true
CREATE TABLE iceberg.bronze.customers_upload USING iceberg AS
SELECT * FROM csv.`s3a://demo-bucket/uploads/customers.csv`
```
Because that shorthand can't be told that row 1 is a header, you get generic columns
**`_c0, _c1, _c2`** *and* the header line (`id,name,country`) lands as a **data row**:

| _c0 | _c1  | _c2     |
|-----|------|---------|
| id  | name | country |  ← the header, now a row 😱
| 1   | Ada  | UK      |

**The fix: register a temp view with `USING csv OPTIONS (...)` first, then `CREATE TABLE … AS`.**
The options are where `header`/`inferSchema` live (`%%sql` is one statement per cell, so this is two
cells):

```sql
%%sql
CREATE TEMPORARY VIEW customers_raw USING csv
OPTIONS (path 's3a://demo-bucket/uploads/customers.csv', header 'true', inferSchema 'true')
```
```sql
%%sql
CREATE TABLE iceberg.bronze.customers_upload USING iceberg AS
SELECT * FROM customers_raw
```
Now the columns take their **names from the header** (`id`, `name`, `country`) with inferred types —
no stray header row.

- **`header 'true'`** — treat row 1 as column names (and skip it from the data).
- **`inferSchema 'true'`** — detect types (`int`/`double`/…); omit it and every column is `string`.
- For Parquet there's no header problem — a Parquet file already carries names and types built in,
  so the plain `parquet.<path>` shorthand works fine (no options needed).

!!! tip "Define the columns yourself (explicit names + types)"
    Don't want inferred names/types? **Declare the schema on the view** and keep `header 'true'` so
    the first row is still skipped:
    ```sql
    %%sql
    CREATE TEMPORARY VIEW customers_raw (id INT, name STRING, country STRING) USING csv
    OPTIONS (path 's3a://demo-bucket/uploads/customers.csv', header 'true')
    ```
    This is the SQL twin of the DataFrame reader's `.option("header", True)` / `.schema(...)` — the
    header/options `spark.read` sets in Python become the `OPTIONS (...)` clause in SQL.

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
- In SQL-only mode, get **column names right** with `CREATE TEMPORARY VIEW … USING csv OPTIONS (header 'true', …)` — or declare an explicit schema — instead of the header-losing `csv.<path>` shorthand
- Query it from SQL, Spark, Trino, and Superset — and know when a **temp view** is enough instead
