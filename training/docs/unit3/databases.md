# 3.6 SQL from Python — Postgres & the lakehouse

## Concept
You've run SQL in the Trino CLI and Superset ([Unit 2](../unit2/intro.md)). But the everyday
data-engineering move is to run SQL **from Python** and pull the result straight into a pandas
DataFrame — so you can then transform it, call an API, or load it somewhere else. Two connections
matter, both on our stack:

- **Postgres** — the raw ShopFlow OLTP source (`customers`, `products`, `orders`, `order_items`).
- **Trino → the `iceberg` lakehouse** — the Bronze/Silver/Gold tables (once built in Unit 4).

```python
import pandas as pd
```

## Lab

### Postgres, via SQLAlchemy + pandas
`pandas.read_sql` runs a query and hands you a DataFrame. Point a **SQLAlchemy engine** at the
ShopFlow database:

```python
from sqlalchemy import create_engine

pg = create_engine("postgresql+psycopg2://postgres:postgres@postgres:5432/shopflow")

# Run SQL, get a DataFrame back
customers = pd.read_sql("SELECT * FROM customers LIMIT 5", pg)
customers
```

Push heavy work **down into the database** (filter/aggregate in SQL, return only the small
result) — don't pull whole tables into pandas:

```python
by_country = pd.read_sql("""
    SELECT c.country,
           count(DISTINCT o.order_id)       AS orders,
           sum(oi.quantity * oi.unit_price) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN customers   c  ON c.customer_id = o.customer_id
    WHERE o.status = 'delivered'
    GROUP BY c.country
    ORDER BY revenue DESC
""", pg)
by_country
```

### Parameterised queries (never format user input into SQL)
```python
country = "US"
df = pd.read_sql(
    "SELECT * FROM customers WHERE country = %(c)s LIMIT 10",
    pg, params={"c": country},
)
```

### Write a DataFrame back to Postgres
`to_sql` creates/loads a table — handy for staging a computed result:

```python
by_country.to_sql("country_revenue_scratch", pg,
                  if_exists="replace", index=False)
pd.read_sql("SELECT * FROM country_revenue_scratch", pg)
```

### Query the lakehouse via Trino
The same `read_sql`, but through a **Trino** connection — so you can query the governed
`iceberg` tables (built in [Unit 4](../unit4/spark-sql-gold.md)) from Python:

```python
from trino.dbapi import connect

trino_conn = connect(host="trino", port=8080, user="learner", catalog="iceberg")

# the Gold mart you'll build in Unit 4
daily = pd.read_sql(
    "SELECT * FROM iceberg.gold.daily_sales ORDER BY order_date DESC LIMIT 14",
    trino_conn,
)
daily
```

!!! tip "Postgres vs Trino from Python — which connection?"
    Use the **Postgres** engine to read the *raw source*; use the **Trino** connection to read
    the *lakehouse* (`iceberg.bronze/silver/gold`) — one Python skill, two data tiers. Both return
    ordinary DataFrames you can then transform with [pandas](pandas.md).

## Challenge
Using the **Postgres** connection, pull *delivered revenue per product category* into a
DataFrame, then (in pandas) add a `pct_of_total` column showing each category's share of overall
revenue. Sort by revenue, highest first.

??? note "Solution"
    ```python
    cat = pd.read_sql("""
        SELECT p.category, sum(oi.quantity * oi.unit_price) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products    p  ON p.product_id = oi.product_id
        WHERE o.status = 'delivered'
        GROUP BY p.category
    """, pg)

    cat["pct_of_total"] = (cat["revenue"] / cat["revenue"].sum() * 100).round(1)
    cat.sort_values("revenue", ascending=False)
    ```
    Note the split of labour: the **join + aggregate** runs in the database (fast, less data
    moved); the **share-of-total** is a quick pandas step on the small result.

!!! tip "🎯 The same pattern on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** ran SQL from Python and moved results in/out as DataFrames.

    - **Azure Databricks** — `spark.read.jdbc(...)` / `spark.sql(...)`, or `pd.read_sql`; results
      to Spark or pandas.
    - **Snowflake** — the **Snowflake Connector for Python** / Snowpark: `session.sql(...).to_pandas()`.
    - **Microsoft Fabric** — notebooks read the Lakehouse SQL endpoint or run `spark.sql`.
    - **Azure Data Factory** — the **Copy activity** moves data between a database and the lake
      no-code (the managed version of these reads/writes).

    "Run SQL, get a DataFrame, transform, write it back" is the daily rhythm everywhere.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **SQLAlchemy engine** | A reusable DB connection factory (`create_engine(uri)`) |
| **`pd.read_sql`** | Run a query → DataFrame |
| **`to_sql`** | Write a DataFrame → a database table |
| **Parameterised query** | Pass values via `params=` (never string-format them in) |
| **Pushdown** | Do filter/aggregate in the DB; return only the small result |
| **Trino DBAPI** | `trino.dbapi.connect(...)` — query the lakehouse from Python |

## You can now…
- Run SQL against Postgres from Python and get a DataFrame (`pd.read_sql`)
- Write a DataFrame back to a database (`to_sql`)
- Query the `iceberg` lakehouse via a Trino connection from Python
- Split work sensibly between the database (heavy SQL) and pandas (light shaping)
