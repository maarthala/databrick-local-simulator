# OSS ⇄ Databricks / Snowflake / Fabric / Azure

This course teaches Data Engineering on an **open-source** stack — deliberately, so you learn the
*concepts* without a cloud bill. Every concept maps directly to the commercial platforms you'll
learn next. This page is your dictionary.

## The big picture
> You're not learning "toy" tools. You're learning the **same building blocks** the platforms are
> made of — and in two cases (**Unity Catalog** and **Medallion**), the *literally identical*
> product / terminology.

## Component map
| This stack (OSS) | Databricks | Snowflake | Microsoft Fabric | Azure (native) |
|---|---|---|---|---|
| **MinIO** (S3 object storage) | cloud storage / UC Volumes | Stages & external volumes | **OneLake** | ADLS Gen2 |
| **Iceberg** tables (via Iceberg REST catalog) | **Delta Lake** (native) | Iceberg & native tables | Delta on OneLake | Delta on ADLS |
| **Unity Catalog** (governance) | **Unity Catalog** — *this is its OSS edition* | Database→Schema + RBAC roles (Polaris/Horizon for Iceberg) | Fabric catalog + Purview | Microsoft Purview |
| **Medallion** Bronze/Silver/Gold | **Medallion** (Databricks' term) | raw/staging/marts (same idea) | Medallion on OneLake | same pattern |
| **Python + pandas / NumPy / PyArrow** (Jupyter) | Databricks notebooks (pandas / PySpark) | **Snowpark** (Python) | Fabric notebooks | Synapse notebooks |
| **`requests` / REST ingest** | notebook + Auto Loader | external access + COPY INTO | Dataflows Gen2 / Copy | Data Factory REST connector |
| **Spark** (Spark Connect) | Databricks Runtime (Spark) | Snowpark | Fabric Spark notebooks | Synapse/Databricks Spark |
| **Trino** (SQL engine over the lake) | Databricks **SQL Warehouse** | Virtual **Warehouse** | Fabric SQL endpoint / Warehouse | Synapse SQL |
| **Airflow** (DAGs) | Databricks **Workflows / Jobs** | Tasks & Streams (+ external orch.) | Fabric **Data Factory** pipelines | Azure **Data Factory** |
| **Superset** (BI) | Databricks AI/BI Dashboards | Snowsight | **Power BI** (Direct Lake) | Power BI |
| **Keycloak** (SSO) + UC RBAC | UC + SCIM/SSO (Entra/Okta) | Snowflake RBAC + SSO | Entra ID | Entra ID |
| **SQL** (joins, CTEs, window fns, MERGE) | identical | identical | identical | identical |

## The three biggest transfers
1. **Unity Catalog here *is* Databricks Unity Catalog** — the open-source edition of the exact
   product. You finish this course already knowing the Databricks governance **model**.
2. **Medallion / Bronze–Silver–Gold is Databricks' own vocabulary** — 1:1.
3. **Your SQL is 100% portable** — joins, `GROUP BY`, CTEs, window functions, and `MERGE` run
   unchanged on Databricks SQL, Snowflake, and Fabric (only a few date-function *names* differ).

## How the lakehouse is wired here (and what changes on the cloud)
On this stack, **Spark builds** the medallion and **Trino/Superset read** it — both through one
shared **`iceberg`** catalog (Iceberg REST + MinIO). Governance (**Unity Catalog**) is a *separate*
layer that models catalogs, schemas, and grants.

On **Databricks**, those two are **one product**: Unity Catalog both *stores* the tables (as Delta)
and *enforces* access — the query engines call it on every read. That unification is the main thing
the managed platform adds over this OSS stack.

## What's *different* on managed platforms (so there are no surprises)
The **concepts, SQL, Spark code, and governance model transfer directly.** What the platforms add
— and what you're *not* practicing here — is the **managed operational layer**:

- **Engine-level governance enforcement** — on the cloud, the query engines enforce Unity Catalog
  grants automatically. On this OSS stack you *define and inspect* the policy (the transferable
  skill), but Trino/Spark aren't wired to enforce it — that wiring is the managed convenience.
- **Serverless / auto-scaling compute** — no clusters to run; pay per query/second.
- **Billing & cost governance** — the real day-2 skill on the platforms.
- **Proprietary performance** — Photon (Databricks), micro-partitions + result cache (Snowflake),
  query acceleration (Fabric).
- **Built-in lineage, monitoring, and data quality** — richer than the OSS equivalents.

The takeaway: **you'll arrive at Databricks/Snowflake/Fabric/Azure already fluent in the
architecture and the work** — the platform course then teaches the managed layer on top, not the
fundamentals.
