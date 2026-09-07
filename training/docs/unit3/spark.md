# 3.7 Spark from a notebook

## Concept
pandas ([3.2](pandas.md)) is perfect until the data outgrows one machine's memory. Then you reach
for **Apache Spark** — a distributed engine whose DataFrame API deliberately echoes pandas, but
runs across a cluster. This page is a gentle first contact from the notebook; **[Unit 4](../unit4/fundamentals.md)**
goes deep and builds the whole ShopFlow lakehouse with it.

On our stack the notebook is a lightweight **Spark Connect** client: it sends your code to the
cluster's Connect server, which already has the **`iceberg`** lakehouse catalog configured. So
connecting is one line.

### What Spark is (and why it's "lazy")
Spark is a **distributed** engine: it splits a job into pieces and runs them across **many
machines** at once. That's the whole point — where pandas ([3.2](pandas.md)) has to hold all the
data in **one** computer's memory, Spark spreads the work (and the data) over a cluster, so it can
chew through datasets far bigger than any single machine could hold.

A Spark **DataFrame** looks and feels like a pandas DataFrame — same mental model of rows and
columns, similar verbs — but under the hood it's **distributed** across the cluster instead of
sitting in local memory.

The one idea to internalise before the first cell is **transformations vs actions**:

- A **transformation** — `select`, `filter`/`where`, `groupBy`, `withColumn`, `join` — is **lazy**.
  It doesn't touch any data; it just adds a step to a **plan** of what you *want* to happen. You
  can chain a dozen of them and Spark still runs **nothing**.
- An **action** — `show`, `count`, `collect`, `write`, `toPandas` — is what finally **triggers**
  the computation. Spark looks at the whole plan you built up, optimises it, and runs it across the
  cluster all at once.

!!! info "Why lazy? Because it's faster"
    Because Spark waits until an action to run, it can see your *entire* recipe first and optimise
    it as a whole — e.g. pushing a `filter` down so it reads less data. If it ran each line eagerly
    (like pandas does), it couldn't make those cluster-wide optimisations. **You'll dig into this
    in [4.1](../unit4/fundamentals.md).**

As you read each cell below, ask one question: **is this a transformation (lazy — builds the plan)
or an action (runs it)?** We'll flag every call.

## Lab

### Connect
```python
from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.getOrCreate()   # Spark Connect client → the cluster
print(spark.version)
```

Every Spark program starts by getting a **`SparkSession`** — your handle to the cluster. Every
DataFrame, every `spark.sql(...)`, every read and write goes through this one object.

**Read it step by step:**

- **`from pyspark.sql import SparkSession, functions as F`** — imports the session class and the
  library of built-in column functions, nicknamed **`F`**. You'll write `F.col(...)`, `F.sum(...)`
  and so on throughout.
- **`SparkSession.builder.getOrCreate()`** — reuse the existing session if one is already running,
  otherwise create it. On this stack it hands you a **Spark Connect** client: a thin local object
  that ships your code over the network to the remote cluster's Connect server (elsewhere you might
  see an explicit URL like `sc://host:15002`; here it's pre-wired, so one line is enough). The
  cluster it connects to already has the **`iceberg`** lakehouse catalog configured.
- **`spark.version`** — just prints the Spark version, a quick "am I really connected?" check. This
  line does contact the cluster, so it doubles as a connection test.

### A Spark DataFrame feels like pandas…
Here we build a tiny DataFrame by hand (real data comes from the lakehouse in the next cell) and
run the classic filter-group-sum pipeline on it.

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

**Read it step by step:**

- **`spark.createDataFrame([...], [...])`** — turn a Python list of rows plus a list of column names
  into a **distributed** Spark DataFrame. (This is the reverse of `.toPandas()` you'll see later.)
  Building the DataFrame is *lazy* — nothing computes yet.
- **`df.show()`** — print the first rows as a neat table, like pandas' `df.head()`. But `show()` is
  an **action**: this is the line that actually **runs** everything and pulls a preview back.
- **`df.filter(F.col("status") == "delivered")`** — **transformation (lazy)**. Keep only rows where
  `status` is `"delivered"`. `F.col("status")` names a column; `== "delivered"` builds the
  condition. (Spark also spells this **`where`** — `filter` and `where` are the same method.) This
  mirrors a pandas boolean index, but runs across the cluster.
- **`.groupBy("country")`** — **transformation (lazy)**. Bucket the rows by country, ready to be
  summarised — one bucket per distinct value, just like pandas `groupby`.
- **`.agg(F.sum("amount").alias("revenue"))`** — **transformation (lazy)**. For each bucket, add up
  `amount` with the built-in **`F.sum`**, and **`.alias("revenue")`** renames the output column so
  it reads nicely.
- **`.show()`** — the **action** at the end of the chain. Only *now* does Spark look at the whole
  filter → group → sum plan, optimise it, and run it.

The verbs mirror pandas (`filter`≈boolean index, `groupBy().agg()`≈`groupby().agg()`), but notice
the shape: you chained three **lazy** transformations and **nothing ran** until the final `show()`
**action** — Spark's laziness in one screenful (you'll dig into this in
[4.1](../unit4/fundamentals.md)).

### Read the lakehouse & run SQL
Because the notebook is wired to the `iceberg` catalog, you can query the Gold tables directly —
the *same* tables Trino and Superset read:

```python
spark.sql("SELECT * FROM iceberg.gold.daily_sales ORDER BY order_date DESC LIMIT 7").show()
```

**Read it step by step:**

- **`spark.sql("SELECT …")`** — hand Spark a plain SQL string and get back a DataFrame. Because the
  session is wired to the `iceberg` catalog, `iceberg.gold.daily_sales` resolves to the real Gold
  table — the *same* one Trino and Superset read. Note `spark.sql(...)` on its own is still **lazy**:
  it returns a DataFrame plan, it doesn't run the query.
- **`.show()`** — the **action** that runs the SQL and prints the 7 rows.

!!! tip "Two dialects, one engine"
    `spark.sql("SELECT … WHERE status = 'delivered'")` and
    `df.filter(F.col("status") == "delivered")` compile down to the **same** distributed plan. Use
    SQL when the question reads naturally as SQL; use the DataFrame API when you're chaining steps
    in Python. Mix them freely.

### pandas ⇄ Spark
Move between the two: prototype small in pandas, scale out in Spark, or pull a small Spark result
back to pandas for plotting:

```python
pdf = spark.sql("SELECT * FROM iceberg.gold.daily_sales").toPandas()   # Spark → pandas
type(pdf)                                                              # pandas.DataFrame

sdf = spark.createDataFrame(pdf)                                       # pandas → Spark
```

**Read it step by step:**

- **`.toPandas()`** — an **action**. It runs the query and **collects the whole result** off the
  cluster into a single ordinary pandas DataFrame in this notebook's memory. Now you can plot it,
  use pandas-only libraries, etc. Remember: **pandas is single-machine**, so everything must fit
  here.
- **`type(pdf)`** — confirms you now hold a plain `pandas.DataFrame`, not a Spark one.
- **`spark.createDataFrame(pdf)`** — the return trip: hand a pandas DataFrame back to Spark to
  **scale it out** across the cluster again.

!!! warning "`.toPandas()` pulls everything to one machine"
    It collects the *entire* result into the driver's memory — fine for a small Gold mart, but
    never call it on a billion-row table. Aggregate in Spark first, then `toPandas()` the small
    result.

### "Submitting a Spark job"
Interactive notebook cells are great for exploring. For **production**, the same code is run
non-interactively — a **Spark job** submitted on a schedule. On this stack that's
`spark-submit script.py` against the cluster; in [Unit 5](../unit5/schedule.md) **Airflow** submits
these jobs for you. The *code* is identical — only how it's launched changes.

!!! info "Where `write` fits in"
    A production job's final step is usually **`df.write…`** — the **action** that saves a
    DataFrame's result back to the lakehouse as a table (rather than `show()`-ing it to a human).
    Like every action, `write` is what actually triggers all the upstream lazy transformations to
    run. Unit 4 uses `write` to build the real Silver and Gold tables.

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

    **Read it step by step:** `spark.table("iceberg.silver.orders")` loads the Silver table as a
    DataFrame (lazy) — a shorthand for `spark.sql("SELECT * FROM …")`. The `.filter → .groupBy →
    .agg` chain is all **lazy transformations** — still nothing has run. **`.toPandas()`** is the
    **action** that finally runs the whole distributed aggregation and pulls the small result down,
    where ordinary pandas `.sort_values(...)` orders it.

!!! tip "🎯 The same Spark on Azure, Databricks, Snowflake & Fabric"
    - **Azure Databricks / Microsoft Fabric** — this *is* Apache Spark; the notebook code and
      `spark.sql` run unchanged, and jobs are scheduled as Workflows / pipelines.
    - **Snowflake** — **Snowpark** gives a Spark-like DataFrame API; `.to_pandas()` bridges the same way.
    - **Azure Data Factory** — Mapping Data Flows run on managed Spark under the hood.

    You've now met all the tools; Unit 4 uses Spark to build the real lakehouse.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Spark** | A **distributed** engine that splits work across many machines, so it handles data far bigger than one computer's memory |
| **Distributed** | Work + data are spread over a **cluster** of machines and run in parallel (vs pandas, which is single-machine) |
| **Spark DataFrame** | A table that *looks* like pandas but lives **across the cluster**; pandas-like verbs, cluster scale |
| **SparkSession** (`spark`) | Your handle to the cluster — every DataFrame, `spark.sql`, read and write goes through it |
| **Spark Connect** | Lightweight client that ships your code to a **remote** Spark cluster's Connect server (here, one line: `getOrCreate()`) |
| **Transformation** | A **lazy** step (`select`, `filter`/`where`, `groupBy`, `withColumn`, `join`) — builds the plan, runs nothing |
| **Action** | The step that **triggers** the computation (`show`, `count`, `collect`, `write`, `toPandas`) |
| **Lazy evaluation** | Spark stacks up transformations and only runs when an **action** asks for a result — letting it optimise the whole plan |
| **`spark.sql(...)`** | Run SQL over the `iceberg` catalog; returns a DataFrame (still lazy until an action) |
| **`toPandas()` / `createDataFrame()`** | Spark → pandas (collects to one machine) / pandas → Spark (scales out) |
| **Spark job / `spark-submit`** | Run the same code non-interactively (Airflow schedules it) |

## You can now…
- Connect to Spark from a notebook and run DataFrame ops and `spark.sql`
- See how Spark's verbs mirror pandas — at cluster scale
- Move data between pandas and Spark (and know when *not* to `toPandas()`)
- Understand what "submitting a Spark job" means — the bridge into Unit 4
