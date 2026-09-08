# 6.6 Beyond tables: volumes & functions

## Concept
Unity Catalog's real pitch isn't "a catalog of tables" — it's **one governance model for all your
data and AI assets**. Tables are just one kind of **securable**. The same `catalog.schema.<object>`
namespace and the same `permission create` grant model also cover:

- **Volumes** — governed **file/blob storage** (unstructured data: CSVs, Excel, images, models…)
- **Functions** — governed, reusable **logic** (a UDF you register once and share)
- Registered models — versioned **AI models** (out of scope for this course, but same idea)

One access model across data (tables), files (volumes), and logic (functions) — that's the concept to
take away, and it maps 1:1 to Databricks Unity Catalog.

## Lab — Volumes (a governed landing zone)
A **volume** is a first-class securable pointing at a storage location. The DE use case: a **landing
zone** for raw files before they're validated and promoted into Bronze (exactly the shape of the
[Ingest-Excel recipe](../recipes/excel.md)).

```bash
UC=http://localhost:8081
T=$(common/uc-cli/login.sh admin)
mkdir -p ~/uc-data/landing

# create an external volume (file:// — same storage rule as tables in 6.5)
uc --server $UC --auth_token "$T" volume create \
  --full_name sales_cat.orders.landing \
  --storage_location "file://$HOME/uc-data/landing"
```
✅ Registers `sales_cat.orders.landing` (EXTERNAL volume).

**Govern who can read vs write the landing area:**
```bash
# engineers drop files in
uc --server $UC --auth_token "$T" permission create --securable_type volume \
   --name sales_cat.orders.landing --privilege "WRITE VOLUME" --principal engineer@dev-epireum.com

# analysts may only read
uc --server $UC --auth_token "$T" permission create --securable_type volume \
   --name sales_cat.orders.landing --privilege "READ VOLUME" --principal analyst@dev-epireum.com
```
Now the *raw landing area* is governed too — not just the finished tables. That's the point: you can
lock down where data **arrives**, not only where it **lands after modelling**.

## Lab — Functions (governed, reusable logic)
Register a transformation once, grant `EXECUTE`, and it's shared + governed like any other object.

```bash
uc --server $UC --auth_token "$T" function create \
  --full_name sales_cat.orders.add_tax \
  --input_params "amount DOUBLE" \
  --data_type DOUBLE \
  --def "return amount * 1.20" \
  --comment "gross = net * 1.2"

# let analysts call it, without being able to change it
uc --server $UC --auth_token "$T" permission create --securable_type function \
   --name sales_cat.orders.add_tax --privilege "EXECUTE" --principal analyst@dev-epireum.com
```
✅ `add_tax` is now a governed, reusable function — logic as a securable.

### Clean up
```bash
uc --server $UC --auth_token "$T" function delete --full_name sales_cat.orders.add_tax
uc --server $UC --auth_token "$T" volume   delete --full_name sales_cat.orders.landing
rm -rf ~/uc-data
```

## What's *not* usable on this stack (and why)
| Feature | Status here | Why |
|---|---|---|
| **Registered models** | works (metadata) | real feature; only relevant if you add an ML unit |
| **Credentials / external locations** | ⚠️ error | they govern *cloud-storage access* and need STS credential vending, which static-cred MinIO can't do — same wall as `s3://` tables |

On Databricks these two are central (they're how UC brokers secure access to ADLS/S3); on OSS + MinIO
they don't apply. Everything else — catalogs, schemas, tables, volumes, functions — works.

## The privilege map, at a glance
| Securable | Grant to read | Grant to write / run |
|---|---|---|
| Table | `SELECT` | `MODIFY`, `CREATE TABLE` (schema) |
| Volume | `READ VOLUME` | `WRITE VOLUME` |
| Function | — | `EXECUTE` |
| Catalog / Schema | `USE CATALOG` / `USE SCHEMA` (needed for anything inside) | `CREATE …` |

## You can now…
- Create and govern a **volume** (a landing zone) with `READ VOLUME` / `WRITE VOLUME`
- Register and grant `EXECUTE` on a **function**
- Explain UC's core idea: **one grant model across tables, files, and logic** — the same governance
  you'll use on Databricks Unity Catalog
