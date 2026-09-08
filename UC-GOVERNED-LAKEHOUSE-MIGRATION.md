# Migration plan — make Unity Catalog the governed front door to the lakehouse

**Goal:** give learners a *near-Databricks* experience — they run
`SELECT * FROM lakehouse.gold.daily_sales` in Spark **or** Trino, and **Unity
Catalog enforces their persona's RBAC** and vends storage credentials. Today UC
governs a *separate* registry while Trino/Spark query the Iceberg lakehouse
directly (ungoverned). This plan closes that gap.

## Target architecture
```
learner (analyst/engineer/lead)
      │  SELECT … FROM lakehouse.<layer>.<table>
      ▼
 Spark  /  Trino        ← both wired to UC as a catalog
      │  "who is this user? what may they see? where's the data?"
      ▼
 Unity Catalog          ← checks grants, vends scoped MinIO creds
      │
      ▼
 MinIO (Delta tables)   ← the governed lakehouse
```

## Key decision: **Delta**, not Iceberg, for the governed lakehouse
UC OSS's mature, connector-supported format is **Delta Lake** (the
`UCSingleCatalog` Spark connector and Trino's `delta_lake`+Unity path both speak
Delta). UC-over-Iceberg exists (UniForm) but is the fragile path that was
deferred here. **So the medallion migrates from Iceberg → Delta-on-UC.** The
Iceberg catalog stays during migration (for rollback + teaching the contrast).

## What already exists (foundations — mostly done)
- ✅ UC on **Postgres** (`ucdb`), **signing-key persistence** (tokens survive restarts)
- ✅ **Static-cred vending** patch (`common/uc-server`, `vendflat` image) — UC vends MinIO keys
- ✅ **Spark↔UC connector** launcher (`common/uc-spark/run-uc-spark.sh`, `UCSingleCatalog`)
- ✅ Seeded **personas + admin** identity, container-free `login.sh`
- Versions: Spark **4.0.0**/Scala 2.13, Trino **473**, `unitycatalog-spark 0.5.0`, `delta-spark 4.x` — compatible.

The remaining work is wiring these into the **default** query paths and moving the data.

---

## Phase 1 — Spark queries through UC by default
Make the UC catalog a first-class Spark catalog (alongside `iceberg` for now).

- **`common/dockerfiles/Dockerfile.spark`** — bake the connector jars in (no runtime `--packages`):
  `delta-spark_4.0_2.13:4.3.1`, `unitycatalog-spark_4.0_2.13:0.5.0`, `unitycatalog-hadoop:0.5.0`.
- **`local/configs/spark/spark-defaults.conf`** (+ k8s equivalent) — add:
  ```
  spark.sql.catalog.lakehouse            io.unitycatalog.spark.UCSingleCatalog
  spark.sql.catalog.lakehouse.uri        http://unity-catalog:8080
  spark.sql.catalog.spark_catalog        org.apache.spark.sql.delta.catalog.DeltaCatalog
  spark.sql.extensions                   io.delta.sql.DeltaSparkSessionExtension
  # token is per-session (Phase 4), not baked here
  ```
- **Verify:** `spark.sql("SHOW SCHEMAS IN lakehouse")` returns UC schemas; a `SELECT` on a UC table works.

**Unlocks:** the Spark front door — engine → UC → MinIO, governed. *(The launcher already proves this; this makes it the default.)*

## Phase 2 — Move the medallion into UC/Delta (pilot: Gold first)
Rewrite the jobs to write UC/Delta instead of `iceberg.*`.

- **UC namespace:** `uc catalog create lakehouse`; schemas `bronze`/`silver`/`gold` (extend `common/uc-cli/seed-governance.sh`).
- **`local/code/shared/jobs/*.py`** — change the write target:
  - `build_gold.py`: `df.writeTo("lakehouse.gold.daily_sales").createOrReplace()` (Delta via UCSingleCatalog) instead of `iceberg.gold.*`.
  - Then `build_silver.py`, `ingest_bronze.py` once Gold is proven.
- **Storage:** UC-managed Delta on MinIO — the `vendflat` vending already covers the Spark write path.
- **Grants (the medallion policy) on the UC lakehouse catalog** (seed): analyst→`gold` read, engineer→`silver` write + `gold` read, lead→all.
- **Migrate incrementally:** Gold → validate (Spark reads it via UC, RBAC gates it) → Silver → Bronze. Keep Iceberg copies until each layer is signed off.

**Unlocks:** the *actual ShopFlow data* becomes UC-governed, not a demo copy.

## Phase 3 — Trino queries through UC
Add a Trino catalog backed by UC (Trino 473 supports Delta + Unity).

- **`local/configs/trino/catalog/unity.properties`** (new):
  ```
  connector.name=delta_lake
  delta.metastore=unity            # (exact key per Trino 473 docs)
  unity.uri=http://unity-catalog:8080
  fs.native-s3.enabled=true
  s3.endpoint=http://minio:9000
  s3.path-style-access=true
  s3.aws-access-key=minioadmin
  s3.aws-secret-key=minioadmin
  ```
- **Verify:** `SELECT * FROM unity.gold.daily_sales` in Trino returns rows.
- **Caveat (be honest in docs):** Trino uses UC for **table discovery + location**; full *per-user* UC grant enforcement in Trino/OSS is weaker than Spark's. Spark is the strongly-governed engine; Trino is governed-access + its own coarse policy.

**Unlocks:** BI/SQL users (Superset → Trino) also go through the governed catalog.

## Phase 4 — Per-user identity end-to-end (the "real" RBAC)
For RBAC to actually gate *each learner*, their **UC token** must flow into their engine session.

- **Jupyter / Spark Connect:** on login, set `spark.sql.catalog.lakehouse.token` from the learner's `login.sh <persona>` token (a notebook helper cell / kernel env). Different persona → different visible tables.
- **Airflow jobs:** a dedicated **pipeline service principal** (write grants on bronze/silver/gold), token via a k8s/compose secret.
- **Token refresh:** tokens are short-lived (we hit this) — provide a one-liner/helper to refresh, and document the `401`/stale-token recovery.

**Unlocks:** analyst-vs-engineer-vs-lead differences enforced *at query time* — the Databricks experience.

## Phase 5 — Cutover, docs, both stacks
- Once all layers are UC/Delta and both engines query UC: make `lakehouse` the primary catalog; keep `iceberg` only to *teach the contrast* (or retire it).
- **Docs:** update **Unit 2** (Trino → `unity.*`), **Unit 4** (Spark writes UC/Delta), **Unit 6** (governed queries now enforced), and replace the "front door vs separate room" caveat with "it's now the front door."
- **k8s parity:** mirror every config change in `k8s/helm/de-stack` (spark-defaults ConfigMap, Trino catalog, seed grants, jars in the image).

---

## Risks & decisions to lock before starting
| Topic | Decision / risk |
|---|---|
| **Format** | **Delta** (mature UC path). Iceberg-via-UniForm is the fragile alternative — avoid. |
| **Version pins** | delta-spark 4.3.x / unitycatalog-spark 0.5.0 / Spark 4.0 / Trino 473 are tightly coupled; pin exactly (this stack has hit version breakage before). |
| **Trino RBAC depth** | Trino↔UC = governed access + location, **not** full per-user UC enforcement. Set expectations. |
| **Per-user tokens** | the trickiest UX; short-lived tokens need a refresh story. |
| **Dual-write window** | keep Iceberg during migration for rollback; costs disk + double writes temporarily. |
| **Both stacks** | every change lands in compose **and** k8s. |

## Effort (rough)
| Phase | Scope | Effort |
|---|---|---|
| 1 Spark default UC catalog | image + config | ~0.5 day |
| 2 Medallion → UC/Delta (pilot Gold → all) | rewrite 3 jobs + seed grants + validate | ~1–2 days |
| 3 Trino → UC | 1 catalog file + validate + version checks | ~0.5–1 day |
| 4 Per-user tokens | notebook helper + service principal + refresh | ~1 day |
| 5 Cutover + docs + k8s parity | docs + Helm mirror | ~1 day |
| **Total** | | **~4–6 days**, incremental & testable per phase |

## Recommended first step
**Phase 1 + a Gold-only Phase 2 pilot**, on compose: prove that
`spark.sql("SELECT * FROM lakehouse.gold.daily_sales")` works *through UC with a
persona token* end-to-end. That single demo de-risks the whole plan — if Gold
flows governed, the rest is repetition. Then decide whether to push through
Trino (Phase 3) and per-user auth (Phase 4).
