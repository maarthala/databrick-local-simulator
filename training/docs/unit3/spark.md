# 3.7 Spark from a notebook

## Concept
pandas ([3.2](pandas.md)) is perfect until the data outgrows one machine's memory. Then you reach
for **Apache Spark** — a distributed engine whose DataFrame API deliberately echoes pandas, but
runs across a cluster. This page is a gentle first contact from the notebook; **[Unit 4](../unit4/fundamentals.md)**
goes deep and builds the whole ShopFlow lakehouse with it.

On our stack the notebook is a lightweight **Spark Connect** client: it sends your code to the
cluster's Connect server, which already has the **`iceberg`** lakehouse catalog configured. So
connecting is one line.

## Lab

### Connect
```python
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.getOrCreate()   # Spark Connect client → the cluster
print(spark.version)
```

### A Spark DataFrame feels like pandas…
```python
df = spark.createDataFrame(
    [(1, "US", 120.0, "delivered"),
     (2, "UK", 40.0,  "cancelled"),
     (3, "US", 300.0, "delivered")],
    ["order_id", "country", "amount", "status"],
)

df.show()                                   # like df.head() — but an ACTION (runs now)
df.filter(F.col("status") == "delivered") \
  .groupBy("country") \
  .agg(F.sum("amount").alias("revenue")) \
  .show()
```

…the verbs mirror pandas (`filter`≈boolean index, `groupBy().agg()`≈`groupby().agg()`), but Spark
is **lazy**: it builds a plan and only runs on an *action* like `show()` (you'll dig into this in
[4.1](../unit4/fundamentals.md)).

### Read the lakehouse & run SQL
Because the notebook is wired to the `iceberg` catalog, you can query the Gold tables directly —
the *same* tables Trino and Superset read:

```python
spark.sql("SELECT * FROM iceberg.gold.daily_sales ORDER BY order_date DESC LIMIT 7").show()
```

### pandas ⇄ Spark
Move between the two: prototype small in pandas, scale out in Spark, or pull a small Spark result
back to pandas for plotting:

```python
pdf = spark.sql("SELECT * FROM iceberg.gold.daily_sales").toPandas()   # Spark → pandas
type(pdf)                                                              # pandas.DataFrame

sdf = spark.createDataFrame(pdf)                                       # pandas → Spark
```

!!! warning "`.toPandas()` pulls everything to one machine"
    It collects the *entire* result into the driver's memory — fine for a small Gold mart, but
    never call it on a billion-row table. Aggregate in Spark first, then `toPandas()` the small
    result.

### "Submitting a Spark job"
Interactive notebook cells are great for exploring. For **production**, the same code is run
non-interactively — a **Spark job** submitted on a schedule. On this stack that's
`spark-submit script.py` against the cluster; in [Unit 5](../unit5/schedule.md) **Airflow** submits
these jobs for you. The *code* is identical — only how it's launched changes.

## Challenge
From the notebook, use Spark to compute **delivered revenue per country** from
`iceberg.silver.orders` (built in Unit 4), then bring the small result back to pandas and print it
sorted by revenue.

??? note "Solution"
    ```python
    from pyspark.sql import functions as F

    result = (
        spark.table("iceberg.silver.orders")
        .filter(F.col("status") == "delivered")
        .groupBy("country")
        .agg(F.sum("line_amount").alias("revenue"))
    )
    pdf = result.toPandas().sort_values("revenue", ascending=False)
    print(pdf)
    ```
    (Requires the Silver table from [Unit 4](../unit4/transform-silver.md). The aggregation runs
    distributed in Spark; only the tiny per-country result is pulled to pandas.)

!!! tip "🎯 The same Spark on Azure, Databricks, Snowflake & Fabric"
    - **Azure Databricks / Microsoft Fabric** — this *is* Apache Spark; the notebook code and
      `spark.sql` run unchanged, and jobs are scheduled as Workflows / pipelines.
    - **Snowflake** — **Snowpark** gives a Spark-like DataFrame API; `.to_pandas()` bridges the same way.
    - **Azure Data Factory** — Mapping Data Flows run on managed Spark under the hood.

    You've now met all the tools; Unit 4 uses Spark to build the real lakehouse.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Spark Connect** | Lightweight client → remote Spark cluster |
| **Spark DataFrame** | Distributed table; pandas-like verbs, runs across the cluster |
| **Lazy / action** | Plan builds up; runs only on `show`/`count`/`write` |
| **`spark.sql(...)`** | Run SQL over the `iceberg` catalog |
| **`toPandas()` / `createDataFrame()`** | Spark → pandas / pandas → Spark |
| **Spark job / `spark-submit`** | Run the same code non-interactively (Airflow schedules it) |

## You can now…
- Connect to Spark from a notebook and run DataFrame ops and `spark.sql`
- See how Spark's verbs mirror pandas — at cluster scale
- Move data between pandas and Spark (and know when *not* to `toPandas()`)
- Understand what "submitting a Spark job" means — the bridge into Unit 4
