# 6.5 Tables in Unity Catalog

## Concept
You've made a catalog, a schema, and assigned them ([6.4](create-assign.md)). A **table** is the next
securable down — and on this stack there's an important truth about *where a table's data lives*.

There are **two catalogs** here:

```
Unity Catalog (sales_cat)   → governance: names + grants, and UC-managed Delta tables (file://)
iceberg  catalog            → the shared lakehouse: real tables + data, queried by Trino/Spark
```

Unity Catalog can hold its **own** Delta tables — great for learning the table lifecycle and
governance. But the **shared, engine-queryable** tables (your Bronze/Silver/Gold medallion) live in
the **`iceberg`** catalog, created with Trino/Spark (Units [2](../unit2/intro.md) &
[4](../unit4/read-bronze.md)). This lesson covers the UC side; the contrast at the end says when to
use which.

!!! info "Why `file://` and not `s3://` here"
    UC creates a table by writing a Delta log at the `storage_location`. Pointing it at MinIO
    (`s3://…`) fails — UC wants **temporary (STS) credentials** to write, and our MinIO vends only
    static keys (`temporaryCredentials is null`). A **local `file://` path** needs no vending, so
    that's what UC tables use on this stack. On Databricks, cloud storage + auto credential vending
    makes `s3://`/ADLS the norm.

## Lab

### 1 · Create a table (as the catalog owner)
Creating a table needs **`CREATE TABLE` on the schema** — so do it as the **owner** of the catalog
(`login.sh admin`), not the bootstrap token (which would get `403`). The `uc` CLI writes the Delta
files **where the CLI runs**, so use a local path you can write:

```bash
UC=http://localhost:8081
T=$(common/uc-cli/login.sh admin)
mkdir -p ~/uc-data

uc --server $UC --auth_token "$T" table create \
  --full_name sales_cat.orders.customers \
  --columns "id INT, name STRING, city STRING" \
  --storage_location "file://$HOME/uc-data/customers"
```
✅ Registers `sales_cat.orders.customers` as an **EXTERNAL DELTA** table, `created_by` you.

### 2 · Write and read
```bash
uc --server $UC --auth_token "$T" table write --full_name sales_cat.orders.customers   # sample rows
uc --server $UC --auth_token "$T" table read  --full_name sales_cat.orders.customers
```
✅ `read` returns the rows. (`write` here inserts **sample/dummy** data — it's a demo helper, not a
real loader; real loads come from Spark/Trino against `iceberg`.)

### 3 · Govern it — grant `SELECT` to a user
A table is a securable, so the grant chain from 6.4 extends one level:
```bash
uc --server $UC --auth_token "$T" permission create --securable_type table \
   --name sales_cat.orders.customers --privilege "SELECT" --principal analyst@dev-epireum.com
```
`analyst` already has `USE CATALOG`/`USE SCHEMA` from 6.4, so this completes their read path to the
table.

### Clean up
```bash
uc --server $UC --auth_token "$T" table delete --full_name sales_cat.orders.customers
rm -rf ~/uc-data
```

## Gotchas
| Symptom | Cause | Fix |
|---|---|---|
| `temporaryCredentials is null` | you used `s3://` | use a local `file://` path |
| `IOException: Creating directories … _delta_log` | the `file://` path isn't writable where `uc` runs | pick a path on your own machine (`file://$HOME/…`) |
| `403 PERMISSION_DENIED` on create | not the owner / no `CREATE TABLE` | create as `login.sh admin` (the owner) |

## The other catalog — where the *shared* tables live
For a table Trino and Spark can actually query (the real lakehouse), you create it in the **`iceberg`**
catalog, not UC:

=== "Trino (SQL)"
    ```sql
    CREATE TABLE iceberg.demo_sales.customers (id INT, name VARCHAR, city VARCHAR);
    INSERT INTO iceberg.demo_sales.customers VALUES (1,'Ava','Berlin');
    SELECT * FROM iceberg.demo_sales.customers;
    ```
=== "Spark (PySpark)"
    ```python
    df.writeTo("iceberg.demo_sales.customers").create()
    ```

| | UC Delta table (`file://`) | `iceberg` table (Trino/Spark) |
|---|---|---|
| Storage | local to the CLI machine | shared MinIO (`demo-bucket`) |
| Queryable by Trino/Spark here | ❌ | ✅ |
| Use for | learning UC's table lifecycle + grants | the real, shared medallion lakehouse |

On **Databricks/Snowflake/Fabric** these are **one**: `CREATE TABLE` in a governed catalog is both
governed *and* queryable, backed by cloud storage. The split you see here is the OSS + MinIO seam.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **EXTERNAL table** | UC records the schema + a `storage_location` you manage (the only kind the CLI creates) |
| **`storage_location`** | where the table's files live — `file://` here (needs to be writable by the CLI) |
| **`uc table write`** | demo helper that inserts sample rows (not a production loader) |
| **`SELECT` grant** | the table-level privilege that lets a user read rows |

## You can now…
- Create a **Delta table** in Unity Catalog (`file://`) and `write`/`read` it
- Grant **`SELECT`** on it, completing a user's read path
- Explain **why UC tables use `file://`** and **where the shared, queryable tables live** (`iceberg`)
