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

### What a DataFrame is

Before any code, get the two core objects clear in your head — everything else in this lesson is
just a method you call on one of them:

- A **DataFrame** is a **table held in memory**: it has **rows** and **named, typed columns**.
  Think of a spreadsheet or a SQL table that lives inside your Python program. Each column has a
  single **dtype** (data type) — `int64`, `float64`, `object` (text), `bool`, `datetime64`, and so
  on — so pandas knows how to store and operate on it fast.
- A **Series** is a **single column** — one named, typed array of values plus an **index** (the
  row labels). When you pull one column out of a DataFrame, you get a Series. A DataFrame is
  essentially a dict of Series that all share the same index.

!!! info "The index — the row labels"
    Every DataFrame and Series carries an **index**: the labels down the left edge. By default it's
    just the row numbers `0, 1, 2, …`, but it can be any labels. The index is what `loc` uses to
    look rows up, and it's what pandas aligns on when you combine objects. For now: default
    integer index = "row number."

The verbs you already know from SQL all have a pandas twin. Keep this map in mind as you go:

| SQL | pandas |
|---|---|
| `SELECT col` | `df["col"]` |
| `WHERE x > 0` | `df[df["x"] > 0]` |
| `GROUP BY … ` | `df.groupby(…).agg(…)` |
| `JOIN` | `df.merge(other, on=…, how=…)` |
| `ORDER BY` | `df.sort_values(…)` |

First, import the library. The alias **`pd`** is a universal convention — every pandas tutorial,
answer, and codebase uses it, so `pd.something` reads the same everywhere:

```python
import pandas as pd
```

**Read it step by step:**

- **`import pandas`** — load the library.
- **`as pd`** — bind it to the short name `pd`. From now on, `pd.DataFrame`, `pd.cut`, etc.

## Lab

### Create & inspect
A DataFrame is columns of data. Build one, then look at it — **inspection is the first thing you
always do** with any new dataset, so you know its shape, its columns' types, and whether it has
gaps before you trust it.

Here we build a DataFrame **from a dict**: each key becomes a **column name**, and its list of
values becomes that column's cells. All the lists must be the same length — one value per row.
(In real work you'd instead **read** a DataFrame from a file or a database — see the note below —
but a hand-built one is perfect for learning the verbs.)

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

**Read it step by step:**

- **`pd.DataFrame({...})`** — build a table. The dict's **keys** (`"order_id"`, `"country"`, …)
  become the four **column names**; each **value list** becomes that column, top to bottom. Result:
  a **5-row × 4-column** DataFrame with a default index `0…4`.
- **`df.head()`** — show the **first rows** (5 by default; pass a number for more/fewer). Your
  go-to "let me eyeball it" command. Its twin `df.tail()` shows the *last* rows.
- **`df.shape`** — the DataFrame's dimensions as a tuple **`(rows, columns)`** → here `(5, 4)`. Not
  a method call, just an attribute (no parentheses).
- **`df.info()`** — a per-column summary: the column names, each one's **dtype**, and its
  **non-null count** (how many cells are filled). The quickest way to spot missing data and wrong
  types.
- **`df.describe()`** — summary **statistics** (count, mean, std, min, quartiles, max) for the
  **numeric** columns only. Great for a fast sanity check on ranges and outliers.
- **`df.dtypes`** — the **type of each column**. Here `order_id` is `int64`, `amount` is
  `float64`, and the text columns are `object`. An attribute, like `shape`.

!!! info "In real life you *read* a DataFrame, you don't type it"
    You'll rarely hand-build a DataFrame. Instead you load one with a `read_*` function, and pandas
    infers the columns and dtypes for you:

    - **`pd.read_csv("orders.csv")`** — read a CSV file into a DataFrame.
    - **`pd.read_parquet("orders.parquet")`** — read a **Parquet** file (columnar, typed, compressed —
      the format you'll meet in [Unit 4](../unit4/fundamentals.md)). Faster and safer than CSV
      because the types are stored in the file.
    - **`pd.read_sql("SELECT * FROM orders", conn)`** — run SQL against a database connection and
      pull the result straight into a DataFrame.

    Whatever the source, once it's a DataFrame the rest of this lesson is identical.

### Select columns & rows
Picking out pieces of a DataFrame is the pandas equivalent of `SELECT`. There are two axes:
choosing **columns** (with `[]`) and choosing **rows** (with `loc`/`iloc`). Watch the bracket
count — **one** name gives you a Series; a **list** of names gives you a DataFrame.

```python
df["amount"]                      # one column (a Series)
df[["country", "amount"]]         # several columns (a DataFrame)

df.loc[0]                         # a row by label
df.iloc[0:2]                      # rows by position (first two)
df.loc[df["amount"] > 100]        # boolean filter — the pandas WHERE
```

**Read it step by step:**

- **`df["amount"]`** — single square brackets with **one** column name → returns that column as a
  **Series** (a 1-D labelled array). This is `SELECT amount`.
- **`df[["country", "amount"]]`** — **double** brackets = a **list** of columns → returns a
  **DataFrame** with just those columns, in that order. This is `SELECT country, amount`. Remember
  the rule: **list in → DataFrame out; name in → Series out.**
- **`df.loc[0]`** — **`loc`** selects by **label**. Here it grabs the row whose index label is `0`,
  returned as a Series (the row's values, indexed by column name).
- **`df.iloc[0:2]`** — **`iloc`** selects by **integer position**. `0:2` means positions 0 and 1
  (the end is *excluded*, like normal Python slicing) → the first two rows as a DataFrame.
- **`df.loc[df["amount"] > 100]`** — you can pass `loc` a **boolean mask** (see the next block) to
  keep only the rows where the condition is `True`. This is the pandas `WHERE`.

!!! note "`loc` vs `iloc` — label vs position"
    - **`loc`** works with the **index labels** and the **column names** (`df.loc[0, "amount"]`).
      With the default integer index the label happens to equal the position, which is why they
      look alike at first — but reorder or filter the rows and the labels stay attached to their
      data while positions renumber.
    - **`iloc`** works with **integer positions** only (`df.iloc[0, 2]` = row 0, column 2), always
      counting from 0, always end-exclusive.

### Filter (boolean indexing)
**Boolean indexing** is how pandas does `WHERE`, and it's worth understanding the two-step trick
underneath. A comparison like `df["status"] == "delivered"` doesn't return rows — it returns a
**Series of `True`/`False`**, one per row (the **mask**). Putting that mask inside `df[...]` then
keeps only the rows where it's `True`.

```python
delivered = df[df["status"] == "delivered"]
big_us    = df[(df["country"] == "US") & (df["amount"] > 100)]   # & = and, | = or
```

**Read it step by step:**

- **`df["status"] == "delivered"`** — build a boolean mask: `True` for each delivered row, `False`
  otherwise. **`df[...]`** around it keeps the `True` rows → `delivered` is the delivered orders.
- **`(df["country"] == "US") & (df["amount"] > 100)`** — two masks combined with **`&`** (element-wise
  **and**). Both must be `True` for a row to survive → US orders over 100.
- Result grain is unchanged — still one row per order — you just have **fewer rows**.

!!! warning "Use `&` `|` `~` and wrap each condition in parentheses"
    Inside a mask you must use **`&`** (and), **`|`** (or), **`~`** (not) — *not* Python's `and`/
    `or`/`not`, which only work on single `True`/`False` values, not whole Series. And because `&`
    binds tighter than `==`, **each condition needs its own parentheses**:
    `(df["country"] == "US") & (df["amount"] > 100)`. Forget them and you'll get a confusing error.

### Add & transform columns
New columns are computed from existing ones. The key idea is **vectorisation**: an operation like
`df["amount"] * 1.2` runs on the **whole column at once**, not row by row — it's both shorter to
write and far faster than a Python loop.

```python
df["with_tax"]  = df["amount"] * 1.2                 # vectorised arithmetic
df["band"]      = pd.cut(df["amount"], [0, 100, 1000],
                         labels=["small", "large"])   # bucketing
df = df.assign(is_delivered = df["status"] == "delivered")   # assign() returns a new df
```

**Read it step by step:**

- **`df["with_tax"] = df["amount"] * 1.2`** — assigning to a **new column name** creates it.
  The right side multiplies every value in `amount` by 1.2 in one shot (**vectorised arithmetic**).
- **`pd.cut(df["amount"], [0, 100, 1000], labels=[...])`** — **bucket** a numeric column into
  bins. The list `[0, 100, 1000]` defines the bin edges (0–100 and 100–1000); `labels` names them.
  Each row gets the label of the bin its `amount` falls into → a categorical `band` column.
- **`df.assign(is_delivered = ...)`** — **`assign`** adds one or more columns and **returns a new
  DataFrame** (it doesn't modify `df` in place). That's why we catch it with `df = ...`. It's handy
  in method chains because it returns the whole DataFrame to keep chaining on.

!!! note "Two ways to add a column — in place vs. a new frame"
    - **`df["new"] = ...`** mutates `df` directly (in place).
    - **`df.assign(new = ...)`** leaves `df` untouched and hands back a **copy** with the column
      added. Prefer `assign` when you want to keep the original intact or chain several steps.

### Group & aggregate (the pandas GROUP BY)
This is the pandas twin of SQL's `GROUP BY` + `SUM/COUNT/AVG`. **`groupby("country")`** splits the
rows into one bucket per country; **`.agg(...)`** then collapses each bucket into a single summary
row. Read the chain top to bottom — each line is one step.

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

**Read it step by step:**

- **`df[df["status"] == "delivered"]`** — first filter to delivered orders (the `WHERE`, applied
  **before** grouping — same order as SQL).
- **`.groupby("country")`** — bucket the remaining rows by `country`. Nothing is computed yet;
  you've just declared the grouping key.
- **`.agg(revenue=("amount", "sum"), ...)`** — compute one value per bucket. This **named-aggregation**
  form reads `output_name=(source_column, function)`: `revenue` = **sum** of `amount`, `orders` =
  **count** of `order_id`, `avg_order` = **mean** of `amount`. The result has **one row per country**
  — that's the new grain.
- **`.reset_index()`** — after `groupby`, the grouping key (`country`) becomes the **index**.
  `reset_index()` pushes it back to being an ordinary column, so the result is a plain
  0,1,2-indexed DataFrame — usually what you want for further work or export.
- **`.sort_values("revenue", ascending=False)`** — order the summary rows by `revenue`, highest
  first (the `ORDER BY … DESC`).

!!! info "Reading a method chain"
    Wrapping the whole thing in `(...)` lets you put each `.method()` on its own line so the
    pipeline reads like a recipe: **filter → group → aggregate → tidy the index → sort**. Each step
    takes the DataFrame from the step above and passes its result to the next.

### Sort, rename, drop, cast
A grab-bag of everyday reshaping verbs. Note that `sort_values`, `rename`, and `drop` all **return
a new DataFrame** and leave `df` unchanged unless you reassign the result — only the explicit
`df[...] = ...` line below actually mutates `df`.

```python
df.sort_values("amount", ascending=False)
df.rename(columns={"amount": "gross_amount"})
df.drop(columns=["with_tax"])
df["order_id"] = df["order_id"].astype("int64")
df["status"].value_counts()        # counts per distinct value — super handy
```

**Read it step by step:**

- **`df.sort_values("amount", ascending=False)`** — return the rows ordered by `amount`, largest
  first. Drop `ascending=False` (defaults to `True`) for smallest-first. Pass a list of columns to
  sort by several keys.
- **`df.rename(columns={"amount": "gross_amount"})`** — rename columns via an
  `{old: new}` mapping. Only the listed columns change.
- **`df.drop(columns=["with_tax"])`** — remove one or more columns by name.
- **`df["order_id"].astype("int64")`** — **cast** a column to another dtype (here to 64-bit
  integer). Common for fixing columns that loaded as the wrong type. Reassigning it back to
  `df["order_id"]` makes the change stick.
- **`df["status"].value_counts()`** — count how many rows have each **distinct value** of a column,
  sorted most-frequent first. It's `GROUP BY status → COUNT(*)` in a single call — a fast way to
  see the distribution of a categorical column.

### Handle missing data
Real data has gaps. pandas represents a missing value as **`NaN`** / `None` (its `NULL`), and gives
you three tools: **detect** them (`isna`), **drop** the affected rows (`dropna`), or **fill** them
with a default (`fillna`).

```python
df2 = df.copy()
df2.loc[1, "amount"] = None
df2["amount"].isna().sum()                 # how many nulls
df2 = df2.dropna(subset=["amount"])        # drop rows missing amount
df2 = df2.fillna({"country": "unknown"})   # or fill a default
```

**Read it step by step:**

- **`df.copy()`** — make an independent copy so edits to `df2` don't touch the original `df`.
  (Without `.copy()`, `df2` could be a view onto `df` and changes might leak back.)
- **`df2.loc[1, "amount"] = None`** — use `loc[row_label, column]` to set a single cell. Here we
  poke a null into row `1`'s `amount` to have something to clean.
- **`df2["amount"].isna().sum()`** — **`isna()`** returns a boolean mask (`True` where the value is
  missing); summing a boolean mask counts the `True`s → **how many nulls** are in the column.
- **`df2.dropna(subset=["amount"])`** — **drop rows** that have a missing value in the listed
  columns. Without `subset` it drops rows with a null in *any* column.
- **`df2.fillna({"country": "unknown"})`** — **fill** missing values. The dict form fills
  per-column: nulls in `country` become `"unknown"`. Both `dropna` and `fillna` return a new
  DataFrame, hence the `df2 = ...` reassignment.

### Join two DataFrames
**`merge`** is the pandas `JOIN`: it stitches two DataFrames together on a shared **key** column,
exactly like the joins you did in [Unit 2](../unit2/joins-aggregations.md). Here we attach a
`region` to each order by matching on `country`.

```python
countries = pd.DataFrame({"country": ["US", "UK", "DE"],
                          "region":  ["NA", "EU", "EU"]})
enriched = df.merge(countries, on="country", how="left")   # SQL LEFT JOIN
```

**Read it step by step:**

- **`countries = pd.DataFrame({...})`** — a small lookup table mapping each country to a region.
- **`df.merge(countries, ...)`** — join `df` (left) to `countries` (right).
- **`on="country"`** — the **join key**: rows match where their `country` values are equal (the
  pandas `ON o.country = c.country`). The `region` column comes along onto each matched order row.
- **`how="left"`** — a **LEFT JOIN**: keep **every** row of `df`; if a country has no match in
  `countries`, its `region` comes back as `NaN`. Other options are `"inner"` (only matches),
  `"right"`, and `"outer"` (all rows from both) — identical to SQL join types.
- Result: `enriched` has all of `df`'s rows plus the new `region` column.

!!! note "`merge` mirrors SQL joins one-for-one"
    `df.merge(other, on="key", how="left")` **is** `SELECT * FROM df LEFT JOIN other USING(key)`.
    If the key columns have **different names**, use `left_on=` / `right_on=` instead of `on=`.
    Just like SQL, if the key isn't unique on the right side the join **fans out** to more rows —
    watch for that.

### `apply` / `map` — custom row logic
When there's no built-in, apply a Python function (slower — prefer vectorised ops when you can):

```python
df["band2"] = df["amount"].apply(lambda a: "large" if a >= 100 else "small")
```

**Read it step by step:**

- **`df["amount"].apply(func)`** — **`apply`** runs the given function on **each value** of the
  column and collects the results into a new Series.
- **`lambda a: "large" if a >= 100 else "small"`** — an inline one-argument function: `a` is one
  `amount` value; it returns `"large"` or `"small"`. So each row is labelled by its own amount.
- Assigning the result to `df["band2"]` stores it as a new column.

!!! warning "`apply` is your last resort, not your first"
    `apply` calls your Python function once per row, so it's **much slower** than a vectorised
    expression on the whole column. Reach for a built-in / vectorised form first
    (`df["amount"] * 1.2`, `pd.cut(...)`, boolean masks) and use `apply` only when the logic
    genuinely can't be expressed that way.

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
| **DataFrame** | A table in memory: rows + named, typed columns |
| **Series** | A single column — one named, typed array with an index |
| **Index** | The row labels down the left edge (default `0,1,2,…`) |
| **dtype** | A column's type (`int64`, `float64`, `object`, `bool`…) |
| **`read_csv` / `read_parquet` / `read_sql`** | Load a DataFrame from a file / Parquet / a database |
| **`head` / `shape` / `info` / `describe` / `dtypes`** | The inspection toolkit: first rows / (rows,cols) / column summary / stats / types |
| **`df['col']` vs `df[['a','b']]`** | One name → a Series; a list → a DataFrame |
| **Boolean indexing** | `df[df.col > x]` — mask of True/False → the pandas WHERE |
| **`&` `\|` `~`** | Element-wise and / or / not inside a mask (wrap each condition in `()`) |
| **`loc` / `iloc`** | Select by label / by integer position |
| **Vectorised op** | An operation on a whole column at once (fast) vs a Python loop |
| **`assign`** | Return a new DataFrame with column(s) added |
| **`pd.cut`** | Bucket a numeric column into labelled bins |
| **`groupby().agg()`** | Group + aggregate (the GROUP BY); `reset_index()` un-nests the key |
| **`merge`** | Join two DataFrames on a key (`how='left'/'inner'/…`) = SQL JOIN |
| **`sort_values`** | Order rows by one or more columns (the ORDER BY) |
| **`rename` / `drop` / `astype`** | Rename columns / drop columns / cast a column's type |
| **`value_counts`** | Count rows per distinct value (GROUP BY + COUNT in one) |
| **`isna` / `dropna` / `fillna`** | Detect / drop / fill missing values (`NaN`) |
| **`apply` / `map`** | Run a custom Python function per value (last resort — slower) |
| **Grain** | What one output row represents (per order, per country…) |

## You can now…
- Create and **inspect** DataFrames (`head/info/describe/dtypes/shape`)
- Select, filter, add, and transform columns
- Group & aggregate, sort, join, and handle missing data
- Recognise how every pandas verb maps to SQL and to Spark
