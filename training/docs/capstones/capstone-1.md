# Capstone 1 (easy)

## Concept
You've now touched every layer of a real data platform: **Python** (Unit 3), **Spark** to build
(Unit 4), **Airflow** to schedule (Unit 5), **Unity Catalog** to govern (Unit 6), and **Superset**
to visualise (Unit 7). This capstone strings them together on your own — end to end — by shipping
**one new metric** for ShopFlow.

The business question: **"What fraction of each day's orders were cancelled?"** Right now nobody
knows. Your job: add an **order cancellation rate** and flow it from the lakehouse to the executive
dashboard.

## Lab
Warm up. Confirm the signal exists — ShopFlow orders carry a `status` (`delivered`, `shipped`,
`placed`, `cancelled`). Check it in the Trino CLI or Superset SQL Lab:

```sql
SELECT status, COUNT(*) AS orders
FROM iceberg.silver.orders
GROUP BY status
ORDER BY orders DESC;
```

If `cancelled` shows up, you have everything you need. (To accumulate more days, an admin can run
the `simulate_day` generator from [5.3](../unit5/schedule.md).)

## Challenge
**Project brief — ship the ShopFlow cancellation rate, Silver → dashboard.**

Add a new Gold mart `iceberg.gold.daily_cancellations` and expose it in Superset.

### Requirements
1. **Gold job.** Write `jobs/build_gold_cancellations.py` that reads `iceberg.silver.orders`,
   aggregates by `order_date`, and writes `iceberg.gold.daily_cancellations` with columns
   `order_date`, `total_orders`, `cancelled_orders`, `cancellation_rate` (0.0–1.0). Accept
   `--catalog` like the other jobs, and write with Iceberg `createOrReplace` (idempotent).
2. **Airflow.** Add a `gold_cancellations` task to your `shopflow_medallion` DAG ([5.2](../unit5/medallion-dag.md)),
   depending on `silver`.
3. **Governance.** Define the analyst grant in Unity Catalog ([6.2](../unit6/rbac.md)): analyst gets
   `SELECT` on the new Gold table — nothing more.
4. **BI.** Add a Superset **Dataset** on `gold.daily_cancellations` and a **line chart** of
   `cancellation_rate` over `order_date`, on the executive dashboard.

### Acceptance criteria
- `SELECT * FROM iceberg.gold.daily_cancellations ORDER BY order_date DESC LIMIT 5;` returns one row
  per day with `cancellation_rate` between 0 and 1.
- Re-running the DAG leaves row counts unchanged (idempotent).
- The analyst grant on Gold is defined in UC.
- The chart appears on **ShopFlow — Executive Overview**.

### Hints
- `cancellation_rate` is a ratio — **cast to `double` before dividing** or you'll get integer `0`,
  and guard against divide-by-zero on empty days.
- Model the job on Unit 4's `build_gold.py`; wire the task with Unit 5's `spark_job()` helper.
- "Idempotent" = `createOrReplace` — same Silver in, same Gold out, every run.

??? note "Solution"

    **1. Gold job — `jobs/build_gold_cancellations.py`**

        import argparse
        from pyspark.sql import SparkSession, functions as F

        p = argparse.ArgumentParser()
        p.add_argument("--catalog", default="iceberg")
        p.add_argument("--date", default=None)     # accepted for scheduling; full rebuild here
        args = p.parse_args()
        cat = args.catalog

        spark = SparkSession.builder.appName("gold_daily_cancellations").getOrCreate()
        orders = spark.table(f"{cat}.silver.orders")

        daily = (
            orders.groupBy("order_date")
            .agg(
                F.count("*").alias("total_orders"),
                F.sum(F.when(F.col("status") == "cancelled", 1).otherwise(0))
                    .alias("cancelled_orders"),
            )
            .withColumn(                                   # cast to double; guard /0
                "cancellation_rate",
                F.when(F.col("total_orders") > 0,
                       F.col("cancelled_orders").cast("double") / F.col("total_orders"))
                 .otherwise(F.lit(0.0)),
            )
        )
        daily.writeTo(f"{cat}.gold.daily_cancellations").using("iceberg").createOrReplace()
        spark.stop()

    **2. Airflow — add the task to `dags/shopflow_medallion.py`**

        gold_cancellations = BashOperator(
            task_id="gold_cancellations",
            bash_command=spark_job("build_gold_cancellations.py"),
        )
        silver >> gold_cancellations       # runs beside the existing gold task

    (`spark_job()` from [5.2](../unit5/medallion-dag.md) already adds `--catalog iceberg` and the
    cluster/cores config.)

    **3. Governance — define the analyst grant (Unity Catalog, from Unit 6)**

        # token via login.sh (container-free), $UC as in 6.1
        uc --server $UC --auth_token "$T" permission create \
          --securable_type schema --name shopflow.gold \
          --privilege SELECT --principal analyst@dev-epireum.com

    This records the least-privilege policy (analyst reads Gold only). On managed **Databricks
    Unity Catalog** the engines enforce it automatically; on this OSS stack it documents the intent
    (see the honest note in [6.2](../unit6/rbac.md)).

    **4. Superset**

        1. Datasets → + Dataset → ShopFlow Lakehouse / gold / daily_cancellations.
        2. Line Chart: X-axis order_date, Metric MAX(cancellation_rate), time grain Day.
        3. Save as "Daily Cancellation Rate" and add it to "ShopFlow — Executive Overview".

    **Verify:**

        SELECT * FROM iceberg.gold.daily_cancellations ORDER BY order_date DESC LIMIT 5;
        -- one row per day, cancellation_rate in [0,1]; re-run the DAG → row count unchanged.

!!! tip "🎯 The same metric-to-dashboard loop on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** shipped one new metric end to end — a Gold mart built in Spark,
    scheduled in Airflow, granted in Unity Catalog, charted in Superset.

    - **Transform:** the identical PySpark runs unchanged as an **Azure Databricks** or **Fabric**
      notebook; in pure **ADF** it's a Mapping Data Flow (Aggregate + Derived Column).
    - **Orchestrate:** the task becomes a **Databricks Workflow**, a **Fabric/ADF pipeline** activity.
    - **Govern:** the `SELECT`-on-Gold grant is the same **Unity Catalog `GRANT`** (Databricks) /
      role `GRANT` (Snowflake).
    - **BI:** the chart becomes a **Databricks AI/BI** tile or **Power BI (Direct Lake)** on Fabric.
    - **Snowflake:** one stack — Snowpark/SQL builds the mart, a **Task** schedules it, a role
      `GRANT` governs it, **Snowsight** charts it.

    Build in Spark → schedule → govern → chart from Gold is the universal daily rhythm of the job.

## You can now…
- Ship a brand-new metric end to end across Spark, Airflow, Unity Catalog, and Superset
- Write an idempotent Gold job a scheduler can safely re-run
- Define least-privilege grants and surface a metric on a dashboard
