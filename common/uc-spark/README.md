# Lesson: the unified catalog — Spark reading/writing GOVERNED tables in Unity Catalog

This shows the **catalog concept** end to end: a governance layer (Unity Catalog)
that owns table metadata + access control, and a compute engine (Spark) that
creates and queries those tables — with **per-user RBAC enforced by the catalog**,
not the engine.

```
        Keycloak (identity)                 MinIO (object storage)
              │                                    ▲  data files (Delta/Parquet)
        per-user token                             │
              ▼                                     │
   Spark ──────────────► Unity Catalog ────────────┘
   (engine)   catalog.schema.table   (governance: metadata + grants + cred vending)
              lakehouse.sales.orders
```

## The three-level namespace
`catalog.schema.table` → `lakehouse.sales.orders`. The engine never sees file
paths; it asks the catalog, which returns metadata **and** vends storage
credentials (only if the user is authorized).

## Prerequisites (already in this repo)
- **Patched UC server** — static credential vending for MinIO (`common/uc-server/`).
- **Patched Spark image** — UC connectors baked in (`common/dockerfiles/Dockerfile.spark`
  + `common/dockerfiles/uc-jars/`). Rebuild + load the spark image to activate.
- **Keycloak** per-user identity (`common/uc-cli/`).

## Demo 1 — create a governed table (as an admin/owner)

`create.py`:
```python
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
loc = "s3://demo-bucket/lakehouse/sales/orders"
df = spark.createDataFrame([(1,10.0),(2,20.0),(3,30.0)], "id int, amount double")
# initialize the Delta table at the location (UniForm-ready), then register in UC
(df.write.format("delta").mode("overwrite")
   .option("delta.columnMapping.mode","name")
   .option("delta.enableIcebergCompatV2","true")
   .option("delta.universalFormat.enabledFormats","iceberg")
   .save(loc))
spark.sql("DROP TABLE IF EXISTS lakehouse.sales.orders")
spark.sql(f"CREATE TABLE lakehouse.sales.orders USING delta LOCATION '{loc}'")
spark.sql("SELECT * FROM lakehouse.sales.orders ORDER BY id").show()
```
```bash
T=$(common/uc-cli/login.sh analyst)         # or use the admin token
common/uc-spark/run-uc-spark.sh "$T" create.py
uc --server http://uc.de.lan:30808 --auth_token "$T" table list --catalog lakehouse --schema sales
```

## Demo 2 — per-user RBAC through the engine (the point)

Grant only analyst `SELECT`:
```bash
ADMIN=$(kubectl -n de-stack exec deploy/unity-catalog -- cat etc/conf/token.txt)
uc --server http://uc.de.lan:30808 --auth_token "$ADMIN" permission create \
   --securable_type table --name lakehouse.sales.orders --privilege SELECT \
   --principal analyst@dev-epireum.com
```

`query.py`: `spark.sql("SELECT * FROM lakehouse.sales.orders ORDER BY id").show()`

```bash
common/uc-spark/run-uc-spark.sh "$(common/uc-cli/login.sh analyst)" query.py   # ✅ rows 1,2,3
common/uc-spark/run-uc-spark.sh "$(common/uc-cli/login.sh engineer)"   query.py   # ❌ 403 PERMISSION_DENIED
```

**This is the lesson:** the *same query* on the *same table* succeeds for analyst and
is denied for engineer — the catalog enforced it, transparently to the engine. Learners
grant/revoke with `uc permission create/delete` and watch the engine's behavior change.

## Notes / limitations
- **Governed catalog + engine + RBAC** is fully demonstrated with **Spark**.
- **Trino** reading the same table via UC's Iceberg REST is NOT wired: it needs
  UniForm→Iceberg metadata, which Delta 4.x isn't emitting in this setup (a known
  sharp edge). Trino instead uses its own `iceberg` catalog (see the Trino lesson).
- The UC connectors are pinned to **0.7.0-SNAPSHOT built for Spark 4.0** and
  patched for MinIO permanent creds; rebuilding requires `common/uc-server/` patches.
