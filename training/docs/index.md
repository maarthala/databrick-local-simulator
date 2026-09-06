# Data Engineering — hands-on with a governed lakehouse

Welcome. You'll learn Data Engineering the way it's actually practiced: by **building a real data pipeline** for a fictional e-commerce company, **ShopFlow**, on a lakehouse you run yourself — object storage, a governed catalog, Spark, SQL, orchestration, and BI.

By the end you will have built, end to end:

```mermaid
flowchart LR
  A[(Postgres OLTP)] --> B
  H[S3 history] --> B
  subgraph Lakehouse
    B[Bronze<br/>raw] --> S[Silver<br/>clean] --> G[Gold<br/>business marts]
  end
  G --> D[Superset<br/>dashboards]
  UC[(Unity Catalog<br/>governance + RBAC)] -.governs.- B & S & G
  AF[Airflow] -.schedules.- B & S & G
```

## How this course works
Every lesson follows the same rhythm:

1. **Concept** — the idea and why it matters
2. **Lab** — copy-runnable steps on your own stack
3. **Challenge** — you solve a variation (solutions are provided, hidden — try first!)
4. **You can now…** — the concrete skills you've gained

## Why open-source first? (this is your Azure rehearsal)
This course is deliberately **Azure-centric in its destination**: after you master
the concepts here, you'll re-implement the very same ShopFlow pipeline on
**Azure Data Factory (ADF)**, **Azure Databricks**, and **Microsoft Fabric** — and the
same skills carry to **Snowflake** too.

We learn on a **free, open-source stack first on purpose**. Every concept — ingestion,
Delta/Iceberg tables, Spark transforms, SQL, orchestration, catalog governance, BI —
is the *same* on the cloud platforms; only the buttons and the bill change. So you
practice here for **$0**, then arrive on Azure already fluent and **spend cloud money
only on the managed layer**, not on relearning the basics.

!!! abstract "On the cloud platforms"
    Most lessons end with a box titled **"🎯 This runs unchanged on Azure, Databricks,
    Snowflake & Fabric"** — it maps the *exact activity* you just performed to the specific
    feature that does it on each platform (e.g. *this MERGE = ADF Data Flow "Alter Row" =
    Databricks `MERGE INTO` = Snowflake `MERGE` = Fabric Spark MERGE*).

    In fact the catalog you'll use here (**Unity Catalog**) *is* the open-source edition
    of Databricks' own, and **Medallion (Bronze/Silver/Gold)** is Databricks' own
    terminology — so parts of this course are already Azure Databricks, verbatim.

## Path
1. **[The ShopFlow scenario](scenario.md)** — the company and its data
2. **[Technical architecture](unit0/architecture.md)** — the tools and how data moves through them
3. **Foundations** → **SQL** → **Python** → **Spark** → **Orchestration** → **Governance** → **BI**
4. **Two capstone projects** to prove it all
5. **[Bridge to the platforms](platforms/rosetta.md)** — your OSS ⇄ cloud dictionary

## Prerequisites
Basic SQL helps but isn't required. No prior Spark, cloud, or DE experience needed.
The stack you're reading this on is already running — get oriented with the
[technical architecture](unit0/architecture.md) before the first unit.
