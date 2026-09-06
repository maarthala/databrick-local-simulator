# 3.2 pandas — the data engineer's Swiss army knife

## Concept
**pandas** is Python's in-memory table library. Its **DataFrame** is a spreadsheet-in-code:
named, typed columns you can filter, transform, group, and join — the same operations you did in
SQL, now in Python. It's the tool you reach for to inspect data, prototype transforms, clean a
file, or reshape an API response before loading it.

!!! note "pandas vs Spark — when to use which"
    pandas runs **on one machine, in memory** — perfect up to ~a few million rows. When data is
    too big for one machine, you use **Spark** ([Unit 4](../unit4/fundamentals.md)), whose
    DataFrame API is deliberately pandas-like. Learn the shapes here; they carry over.

```python
import pandas as pd
```

## Lab

### Create & inspect
A DataFrame is columns of data. Build one, then look at it — **inspection is the first thing you
always do**:

```python
df = pd.DataFrame({
    "order_id":  [1, 2, 3, 4, 5],
    "country":   ["US", "UK", "US", "DE", "UK"],
    "amount":    [120.0, 40.0, 300.0, 90.0, 55.0],
    "status":    ["delivered", "cancelled", "delivered", "delivered", "delivered"],
})

df.head()          # first rows
df.shape           # (rows, cols) → (5, 4)
df.info()          # columns, dtypes, non-null counts
df.describe()      # summary stats for numeric columns
df.dtypes          # the type of each column
```

### Select columns & rows
```python
df["amount"]                      # one column (a Series)
df[["country", "amount"]]         # several columns (a DataFrame)

df.loc[0]                         # a row by label
df.iloc[0:2]                      # rows by position (first two)
df.loc[df["amount"] > 100]        # boolean filter — the pandas WHERE
```

### Filter (boolean indexing)
```python
delivered = df[df["status"] == "delivered"]
big_us    = df[(df["country"] == "US") & (df["amount"] > 100)]   # & = and, | = or
```

### Add & transform columns
```python
df["with_tax"]  = df["amount"] * 1.2                 # vectorised arithmetic
df["band"]      = pd.cut(df["amount"], [0, 100, 1000],
                         labels=["small", "large"])   # bucketing
df = df.assign(is_delivered = df["status"] == "delivered")   # assign() returns a new df
```

### Group & aggregate (the pandas GROUP BY)
```python
# revenue & order count per country, delivered only
(df[df["status"] == "delivered"]
   .groupby("country")
   .agg(revenue=("amount", "sum"),
        orders=("order_id", "count"),
        avg_order=("amount", "mean"))
   .reset_index()
   .sort_values("revenue", ascending=False))
```

### Sort, rename, drop, cast
```python
df.sort_values("amount", ascending=False)
df.rename(columns={"amount": "gross_amount"})
df.drop(columns=["with_tax"])
df["order_id"] = df["order_id"].astype("int64")
df["status"].value_counts()        # counts per distinct value — super handy
```

### Handle missing data
```python
df2 = df.copy()
df2.loc[1, "amount"] = None
df2["amount"].isna().sum()                 # how many nulls
df2 = df2.dropna(subset=["amount"])        # drop rows missing amount
df2 = df2.fillna({"country": "unknown"})   # or fill a default
```

### Join two DataFrames
```python
countries = pd.DataFrame({"country": ["US", "UK", "DE"],
                          "region":  ["NA", "EU", "EU"]})
enriched = df.merge(countries, on="country", how="left")   # SQL LEFT JOIN
```

### `apply` / `map` — custom row logic
When there's no built-in, apply a Python function (slower — prefer vectorised ops when you can):

```python
df["band2"] = df["amount"].apply(lambda a: "large" if a >= 100 else "small")
```

## Challenge
From `df`, build a **country scorecard**: per country, total delivered revenue, delivered order
count, and average delivered order value — sorted by revenue, highest first. (This is the pandas
version of the Unit 2 "revenue by country".)

??? note "Solution"
    ```python
    scorecard = (
        df[df["status"] == "delivered"]
        .groupby("country")
        .agg(revenue=("amount", "sum"),
             orders=("order_id", "count"),
             avg_order=("amount", "mean"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    scorecard
    ```

!!! tip "🎯 The same shapes on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** filtered, transformed, grouped, and joined DataFrames.

    - **Azure Databricks / Microsoft Fabric** — run pandas directly in notebooks; and Spark's
      DataFrame API (`.filter/.groupBy/.join`) mirrors these shapes at scale — plus
      **pandas API on Spark** (`import pyspark.pandas as ps`) is pandas that runs distributed.
    - **Snowflake** — **Snowpark**'s DataFrame API mirrors pandas; `to_pandas()` bridges them.
    - **Azure Data Factory** — the no-code Mapping Data Flow expresses the same filter/derive/
      aggregate/join steps as visual transformations.

    pandas is the universal prototyping tool; these verbs reappear in every DataFrame API.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **DataFrame / Series** | A table / a single column |
| **`head`/`info`/`describe`/`dtypes`/`shape`** | The inspection toolkit |
| **Boolean indexing** | `df[df.col > x]` — the pandas WHERE |
| **`loc` / `iloc`** | Select by label / by position |
| **`groupby().agg()`** | Group + aggregate (the GROUP BY) |
| **`merge`** | Join two DataFrames (`how='left'/'inner'/…`) |
| **`assign` / `apply` / `map`** | Add columns / run custom logic |
| **`fillna` / `dropna` / `isna`** | Handle missing values |
| **`value_counts` / `sort_values` / `astype`** | Count / sort / cast |

## You can now…
- Create and **inspect** DataFrames (`head/info/describe/dtypes/shape`)
- Select, filter, add, and transform columns
- Group & aggregate, sort, join, and handle missing data
- Recognise how every pandas verb maps to SQL and to Spark
