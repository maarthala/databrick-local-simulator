# Databrick Local Simulator

A hands-on Data Engineering learning environment — a **governed lakehouse**
(MinIO, Apache Polaris governed Iceberg catalog, Spark, Trino, Superset, Airflow,
Jupyter) that you can run two ways with the **same stack**:

## 📚 Training course

Read the hands-on **Data Engineering course** online — build the ShopFlow
Bronze→Silver→Gold lakehouse and map every skill to Databricks, Snowflake & Fabric:

**→ [maarthala.github.io/databrick-local-simulator](https://maarthala.github.io/databrick-local-simulator/)**

Start with **Prerequisites & setup** and **Bring up the stack**, then work through the units.
The stack's landing page links straight to this course, so it's always the current version.

## 💬 Community & help

Join our **Discord** to discuss the stack, get help with setup or problems, and connect
with other learners:

**→ [discord.gg/2B5mTgGjM](https://discord.gg/2B5mTgGjM)**

- Instructor-led **DE training** for students & career-changers — **learning@epireum.com**
- **Companies** looking for DE talent or delivery — **contact@epireum.com**

## Setup — pick your environment

### 🖥️ [Local (Docker Compose)](./local/README.md)
Run the whole governed lakehouse on a single machine with Docker Compose.
Fastest to start; great for learning and offline use.
→ **[local/README.md](./local/README.md)**

### ☸️ [Kubernetes](./k8s/README.md)
The same stack on a MicroK8s/Kubernetes cluster via a Helm umbrella chart, with a
one-command Ansible bootstrap (build-and-import for locked-down nodes, or pull from
a registry for bigger clusters).
→ **[k8s/README.md](./k8s/README.md)**

## Repository layout
```
local/    Docker Compose stack + its setup, config, and challenges (Tasks.md)
k8s/      Helm chart (k8s/helm) + Ansible bootstrap (k8s/ansible)
common/   Shared by both: Dockerfiles for the custom images, the Polaris seed
          (common/polaris), and the Polaris Console build (common/polaris-console)
```

Both environments deploy the **same governed-lakehouse component set** and are
self-contained (each runs its own Postgres). What differs is only the orchestrator
(Compose vs Kubernetes) and the hostnames (localhost ports vs `*.de.lan` ingress).

## Major releases & integrations
Notable additions — a new tool, data source, or capability — are logged here so you
can see what's new at a glance. This is **not** a per-commit changelog; only
integration-level updates (like AdventureWorks or SQLPad) get an entry.

| Date | Release / integration | What it adds | Scope |
|---|---|---|---|
| 2026-09-17 | **AdventureWorks SQL challenge** | Course unit 2.9 — 33 progressive SQL challenges (joins → CASE/COALESCE → windows → CTEs → subqueries/outer-joins → RFM capstone) with solutions | course |
| 2026-09-20 | **SQLPad (SQL workbench)** | Web SQL editor for read **+ write** (INSERT/UPDATE/DDL) on Postgres (OLTP) & Trino (OLAP); replaced Metabase | local · k8s |
| 2026-09-17 | **AdventureWorks OLTP** | Full 68-table AdventureWorks sample DB in Postgres, queryable via Trino/SQLPad/Superset | local · k8s |
| 2026-09-17 | **Spark internals lessons** | Course units 4.7 (architecture & query lifecycle) and 4.8 (data skew & salting) | course |
| 2026-09-13 | **Notebook auto-push** | Jupyter commits + pushes each notebook to git on every save | local · k8s |
| 2026-09-13 | **`%%sql` cell magic** | Databricks-style SQL cells in notebooks, backed by the governed Spark session | local · k8s |
| 2026-09-13 | **Pre-created Spark session** | A ready `spark` session on notebook open — no boilerplate | local · k8s |
| 2026-09-12 | **Azure AdventureWorks** | AdventureWorks sample on Azure SQL for the ADF learning track | azure |
| 2026-09-10 | **Azure ADF (Terraform)** | Provision Azure Data Factory + SQL as code (base-setup + sql stacks) | azure |
| 2026-09-08 | **Apache Polaris governance** | Single governed Iceberg REST catalog for Spark & Trino (replaced Unity Catalog) | local · k8s |
| 2026-09-08 | **Polaris on Kubernetes** | The governed catalog + Console added to the Helm chart | k8s |
| 2026-09-08 | **Medallion Airflow DAG** | Bronze→Silver→Gold pipeline orchestrated end-to-end | local · k8s |
| 2026-09-06 | **ShopFlow DE course** | Hands-on training site (units 0–10) served by the stack landing page | course |
| 2026-09-06 | **Kubernetes deployment** | Helm umbrella chart + one-command Ansible bootstrap | k8s |
| 2026-09-06 | **Governed lakehouse stack** | MinIO, Spark (+ Connect), Trino, Superset, Airflow, Jupyter on Compose | local |
| 2026-09-06 | **ShopFlow dataset** | 12-table e-commerce sample seeded into Postgres + the lake | local · k8s |
