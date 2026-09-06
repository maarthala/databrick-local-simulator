# 3.1 Python & notebooks for data engineering

## Concept
SQL ([Unit 2](../unit2/intro.md)) answers questions once the data is in tables. But a data
engineer also needs a **general-purpose language** to glue systems together: pull from an API,
reshape a file, call a database, kick off a Spark job, add custom logic SQL can't express.
That language is **Python** — the lingua franca of data engineering — and you'll write it in a
**notebook**.

### Why notebooks?
A **Jupyter notebook** runs code in **cells** you execute one at a time, seeing the output
immediately below each. That tight feedback loop is perfect for exploring data. Open Jupyter at
[http://localhost:8008](http://localhost:8008) (token `123456`) and make a new notebook.

- **Shift+Enter** runs a cell.
- The result of the **last expression** in a cell is printed automatically.
- Variables persist across cells (top-to-bottom is the intended order).

```python
1 + 1          # a cell whose last expression is shown → 2
```

### Python you'll actually use
You don't need deep Python — just the everyday building blocks. The essentials:

```python
# Variables & types
name = "ShopFlow"        # str
orders = 40000           # int
aov = 84.50              # float
is_live = True           # bool
nothing = None           # null

# f-strings — the standard way to build text
print(f"{name} has {orders:,} orders, AOV ${aov:.2f}")

# Lists (ordered), dicts (key→value), sets (unique)
countries = ["US", "UK", "DE", "US"]
prices = {"keyboard": 89.0, "hub": 39.5}
unique_countries = set(countries)          # {'US','UK','DE'}

print(len(countries), prices["keyboard"], len(unique_countries))
```

**Control flow & functions** — the logic you'll wrap around data:

```python
def revenue_band(amount):
    if amount >= 1000:
        return "large"
    elif amount >= 100:
        return "medium"
    return "small"

for amt in [50, 250, 5000]:
    print(amt, "→", revenue_band(amt))
```

**Comprehensions** — the Pythonic one-liner for transforming a collection (you'll see this
everywhere):

```python
amounts = [50, 250, 5000, 80]
big = [a for a in amounts if a >= 100]          # filter → [250, 5000]
bands = [revenue_band(a) for a in amounts]       # map    → ['small','medium','large','small']
print(big, bands)
```

**Handling errors** — real pipelines hit bad data; catch it instead of crashing:

```python
def to_float(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None          # a "TRY_CAST" in Python (like Unit 2.5)

print(to_float("12.5"), to_float("oops"))       # 12.5 None
```

## Lab
In a Jupyter cell, build a tiny "orders" dataset as a list of dicts (the shape data often
arrives in from an API) and summarise it with plain Python:

```python
orders = [
    {"order_id": 1, "country": "US", "amount": 120.0, "status": "delivered"},
    {"order_id": 2, "country": "UK", "amount": 40.0,  "status": "cancelled"},
    {"order_id": 3, "country": "US", "amount": 300.0, "status": "delivered"},
    {"order_id": 4, "country": "DE", "amount": 90.0,  "status": "delivered"},
]

# total delivered revenue
delivered = [o for o in orders if o["status"] == "delivered"]
total = sum(o["amount"] for o in delivered)
print(f"delivered revenue: ${total:,.2f}")

# revenue per country (a dict accumulator — the manual version of GROUP BY)
by_country = {}
for o in delivered:
    by_country[o["country"]] = by_country.get(o["country"], 0) + o["amount"]
print(by_country)
```

That `by_country` loop is a **GROUP BY** done by hand. It works — but it's verbose and slow on
real volumes. In [3.2](pandas.md) you'll do the same thing in one line with **pandas**, and in
Spark ([Unit 4](../unit4/fundamentals.md)) at any scale.

## Challenge
Write a function `summarise(orders)` that returns a dict with `count`, `delivered_revenue`, and
`top_country` (the country with the most delivered revenue). Test it on the sample above.

??? note "Solution"
    ```python
    def summarise(orders):
        delivered = [o for o in orders if o["status"] == "delivered"]
        by_country = {}
        for o in delivered:
            by_country[o["country"]] = by_country.get(o["country"], 0) + o["amount"]
        top = max(by_country, key=by_country.get) if by_country else None
        return {
            "count": len(orders),
            "delivered_revenue": sum(o["amount"] for o in delivered),
            "top_country": top,
        }

    print(summarise(orders))
    # {'count': 4, 'delivered_revenue': 510.0, 'top_country': 'US'}
    ```

!!! tip "🎯 The same Python runs on Azure, Databricks, Snowflake & Fabric"
    Notebooks and Python are universal: **Databricks**, **Microsoft Fabric**, and **Azure
    Synapse** all give you Jupyter-style notebooks running the same Python; **Snowflake** runs
    Python in **Snowpark**/Snowsight notebooks. The language you learn here is 100% portable —
    only the data connectors differ.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Notebook / cell** | Interactive doc; run code in chunks, see output inline |
| **list / dict / set** | Ordered items / key→value map / unique items |
| **f-string** | `f"{var}"` — the standard way to build text |
| **Comprehension** | `[f(x) for x in xs if cond]` — filter+map in one line |
| **`try/except`** | Catch errors instead of crashing (Python's TRY_CAST) |
| **Function** | Reusable named block of logic |

## You can now…
- Run code in Jupyter cells and read inline output
- Use Python's core types, f-strings, comprehensions, functions, and error handling
- Do a GROUP-BY-by-hand — and see why pandas/Spark will replace it next
