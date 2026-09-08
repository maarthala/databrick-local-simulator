# 6.8 The governed lakehouse: querying through Unity Catalog

## Concept
Everything so far governed UC's *own* registry. This lesson is the real thing:
**Spark queries the actual medallion data *through* Unity Catalog, and UC enforces
each persona's RBAC at query time** — the Databricks front-door model, working on
this stack.

```
you (analyst / engineer / lead)
   │  spark.sql("SELECT … FROM lakehouse.gold.daily_sales")
   ▼
 Spark ── asks ──► Unity Catalog:  may this user? where's the data?  (checks grants, vends creds)
   ▼
 MinIO (Delta)  → rows returned only if you're allowed
```

The medallion lives twice on this stack, on purpose — **two engines, two roles**:

| Engine → catalog | Access model | Role in the course |
|---|---|---|
| **Trino → `iceberg.*`** | **full / open** — every user sees everything | SQL, BI, dashboards, exploration (Units 2, 7) |
| **Spark → `lakehouse.*`** (UC/Delta) | **governed** — per-user RBAC via Unity Catalog | governance (this unit) |

Think of it as: **Trino is the open analytics engine; Spark is the governed engine.**
That's the same division you'll meet in industry — an open SQL layer for broad
access, and a governed catalog (Unity Catalog) that gates who reads what. On
Databricks both run *through* UC; here we teach governance on the engine where UC
works natively — **Spark** — and use **Trino for full-access SQL**.

## Lab

### 1 · Publish the medallion into the governed catalog (operator/pipeline)
The pipeline mirrors the Iceberg medallion into UC's `lakehouse` catalog as Delta:
```bash
common/uc-spark/publish-medallion-uc.sh          # → PUBLISHED lakehouse.<layer>.<table> …
```
This runs as the **pipeline principal** (see the note on writes below). After it,
`lakehouse` holds `bronze`/`silver`/`gold` as governed Delta tables on MinIO.

### 2 · Query it as a persona — RBAC enforced by UC
`run-uc-spark.sh` runs a Spark job **as a specific user** (their Keycloak token);
UC decides what they can read. Same job, three identities, three results:
```bash
cat > matrix.py <<'PY'
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
for t in ["gold.daily_sales", "silver.orders", "bronze.customers"]:
    try:
        n = spark.sql(f"SELECT count(*) c FROM lakehouse.{t}").collect()[0][0]
        print(f"{t} = OK({n})")
    except Exception:
        print(f"{t} = DENIED")
PY

for p in analyst engineer lead; do
  echo "== $p =="
  common/uc-spark/run-uc-spark.sh "$(common/uc-cli/login.sh $p)" matrix.py
done
```
✅ **What you'll see — the medallion policy, enforced at query time:**

| Persona | `gold.daily_sales` | `silver.orders` | `bronze.customers` |
|---|---|---|---|
| analyst | ✅ OK | ⛔ DENIED | ⛔ DENIED |
| engineer | ✅ OK | ✅ OK | ⛔ DENIED |
| lead | ✅ OK | ✅ OK | ✅ OK |

`analyst` literally **cannot read** the raw-PII `bronze` — UC refuses, in the engine, per their token. That's governance doing its job on real data.

## What works, and what to do where it doesn't
Unity Catalog OSS is powerful but unfinished in a few spots. Teach the working
path; here's the honest map and the right move when something won't work:

!!! success "Works — lean on these"
    - **Spark reads through UC** with per-user RBAC (this lesson).
    - **Catalogs / schemas / grants** via the `uc` CLI and web UI (6.1–6.4).
    - **Pipeline writes** into the governed lakehouse (`publish-medallion-uc.sh`).

!!! warning "Doesn't work here — use the alternative"
    - **Trino → UC**: not reachable cleanly on this OSS build. UC's Iceberg REST
      endpoint works, but it only exposes a table to Trino if the table carries
      **UniForm** (Iceberg) metadata — which doesn't generate through the UC Spark
      connector here (and Trino's Delta connector has no UC-metastore option).
      **Alternative:** for SQL/BI and Superset, query the **`iceberg`** catalog via
      Trino (Units 2 & 7); use UC/Spark for *governed* access. *Hint: on Databricks
      every engine goes through UC — one catalog, all engines.*
    - **Per-user writes**: personas can't write as themselves (UC-server
      `generateTemporaryPathCredentials` is a stub → 403). **Alternative:** the
      **pipeline writes as a service/admin principal** (the normal production
      pattern); humans get governed *reads*. *Hint: on Databricks, `MODIFY`/`CREATE`
      grants let users write as themselves, audited.*
    - **`uc table create --storage_location s3://…`**: the CLI can't vend MinIO
      creds. **Alternative:** write the table with Spark/`deltalake` and let the
      pipeline register it (`publish_uc.py`), or use a local `file://` path for a
      quick demo (6.5). *Hint: `file://` needs no credential vending.*
    - **Notebook (Spark Connect) per-user governance**: the shared Connect server
      can't carry each user's token. **Alternative:** use `run-uc-spark.sh` (a
      per-user `spark-submit`) for governed queries; use the notebook for
      ungoverned dev against `iceberg`.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **`lakehouse` catalog** | the UC/Delta copy of the medallion Spark reads *through UC* (governed) |
| **`iceberg` catalog** | the open medallion Trino+Spark read directly (not governed) |
| **`run-uc-spark.sh`** | runs a Spark job as one persona's token → UC enforces their grants |
| **`publish-medallion-uc.sh`** | pipeline step that mirrors Iceberg → governed UC/Delta |
| **service/pipeline principal** | the identity that *writes* (per-user writes aren't available on OSS) |

## You can now…
- Query the **real medallion through Unity Catalog** and watch RBAC gate each persona
- Explain the **two-catalog** design (`iceberg` for open SQL/BI, `lakehouse` for governed Spark)
- Know **what works vs. the alternative/hint** for the OSS gaps — and that Databricks closes them
