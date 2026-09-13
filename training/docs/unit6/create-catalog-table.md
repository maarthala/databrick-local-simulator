# 6.3 Create your own catalog, namespace & table

You've *used* the governed catalog; now build the whole hierarchy yourself and see
exactly where each piece lives. The structure is three levels:

```
catalog  →  namespace (schema)  →  table
 (learn)      (demo)               (sales)   →  addressed as  learn.demo.sales
```

Key idea to hold onto:

| Level | Where it lives | Hits MinIO? |
|---|---|---|
| **Catalog** | Polaris (metadata) | ❌ no |
| **Namespace** | Polaris (metadata) | ❌ no |
| **Table (created)** | Polaris + a `metadata.json` in MinIO | ✅ first object |
| **Rows (inserted)** | Parquet data + manifests in MinIO | ✅ data files |

So a catalog/namespace is just *registration*; the **table** is the first thing that
writes to object storage.

## A · Create a catalog (Polaris Console)

Open the Console — <http://localhost:8189> (k8s: `http://polaris-console.de.lan`) —
sign in as `root` / `s3cr3t`, then **Catalogs → Create catalog**:

- **Name:** `learn`
- **Storage type:** `S3`
- **Default base location:** `s3://demo-bucket/learn`
- **Endpoint:** `http://minio:9000`
- **Region:** `us-east-1`
- **Path-style access:** **ON** ← required for MinIO
- **Create**

!!! warning "Path-style access is mandatory for MinIO"
    MinIO addresses buckets as `minio:9000/bucket` (path-style). The default S3 style is
    `bucket.minio:9000` (virtual-host), which doesn't resolve on MinIO — table I/O then
    fails with an `UnknownHost` error. So **turn Path-style access ON**. (On real AWS S3
    you'd leave it off.)

Grant your admin write access so you can create tables in it: on the catalog →
**Catalog Roles** → create one → grant **`CATALOG_MANAGE_CONTENT`** → assign it to the
`service_admin` principal-role. *(The built-in `polaris_lake` catalog already has this.)*

## B · Create a namespace & table

A **namespace** (schema) is a folder for tables. A **table** has a schema and holds rows.

!!! note "Where you create it decides who can query it"
    The notebook's `spark` is pre-wired only to the **`iceberg`** catalog (= the built-in
    `polaris_lake`). A brand-new catalog like `learn` is **not** visible to the notebook
    until Spark is configured with it. So to create-and-query in one go, build under the
    **`iceberg`** catalog. (Use your own `learn` catalog once you add a Spark config for it.)

In a notebook (`spark` is already there):

```python
# namespace (schema) — metadata only, nothing in MinIO yet
spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.demo")

# table — writes the first metadata.json to MinIO
spark.sql("""
CREATE TABLE IF NOT EXISTS iceberg.demo.sales (
    id int, product string, amount double, sold_on date
) USING iceberg
""")

# rows — writes Parquet data + manifests
spark.sql("""
INSERT INTO iceberg.demo.sales VALUES
    (1,'Widget',120.50, DATE'2026-01-05'),
    (2,'Gadget', 75.00, DATE'2026-01-06'),
    (3,'Widget', 60.25, DATE'2026-02-01')
""")
```

You can also create the namespace/table visually in the **Console** (Catalog →
**Create namespace** / **Create Iceberg Table**); the notebook is just quicker for a
table with data.

**Watch it land in MinIO** (console <http://localhost:9001>, or the CLI): after
`CREATE TABLE` you'll see `warehouse/demo/sales/metadata/00000-….metadata.json`; after
`INSERT`, a `data/*.parquet` plus manifest/snapshot files appear.

## C · Query the table

All three work — pick by need:

```python
spark.table("iceberg.demo.sales").show()                 # DataFrame API
```
```python
spark.sql("SELECT * FROM iceberg.demo.sales ORDER BY id").show()
```
```sql
%%sql
SELECT product, sum(amount) AS revenue
FROM iceberg.demo.sales
GROUP BY product
```

The same table is now visible in **Trino**, **Superset**, and the **Polaris Console** —
one governed copy, every engine.

## 🎯 This runs unchanged on Azure, Databricks, Snowflake & Fabric
`catalog → schema → table` with `CREATE NAMESPACE` / `CREATE TABLE … USING iceberg` is
the same in **Databricks Unity Catalog** and **Snowflake** (Snowflake calls it
database → schema → table). Only the catalog name and storage URL change.

## You can now…
- Create a **catalog** in the Console (and set **path-style** for MinIO)
- Create a **namespace** and a **table**, and say when each first touches object storage
- Query the table from the notebook (DataFrame, `spark.sql`, `%%sql`) — and from Trino/Superset
- Explain why a *new* catalog needs a Spark config before the notebook can see it
