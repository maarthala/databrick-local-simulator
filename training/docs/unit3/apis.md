# 3.5 Consuming APIs with `requests`

## Concept
Not all data lives in your database. **APIs** (web services you call over HTTP) are a major
source: exchange rates, weather, payment providers, marketing platforms, shipping trackers.
Pulling from an API is a classic **ingest** step ([1.1](../unit1/what-is-de.md)). In Python the
standard tool is the **`requests`** library.

A real, ShopFlow-shaped need: orders arrive in **different currencies** (`USD`, `GBP`, `EUR`,
`INR`). To report total revenue you need **FX rates** — which come from an API. We'll use the
free, no-key [Frankfurter](https://frankfurter.app) API.

```python
import requests
```

!!! note "This lab needs outbound internet"
    Unlike the rest of the course (which runs against the local stack), calling a public API
    needs the notebook to reach the internet. Everything else here — Postgres, Trino, Spark — is
    local.

## Lab

### A basic GET request
```python
resp = requests.get("https://api.frankfurter.app/latest",
                    params={"from": "USD", "to": "GBP,EUR,INR"},
                    timeout=10)

resp.status_code        # 200 means OK
resp.url                # see how params became a query string
data = resp.json()      # parse the JSON body into a Python dict
data
# {'amount':1.0,'base':'USD','date':'...','rates':{'GBP':0.78,'EUR':0.91,'INR':83.2}}
```

### Always check for errors
Networks and services fail — handle it instead of trusting the response:

```python
def get_rates(base="USD", symbols="GBP,EUR,INR"):
    try:
        r = requests.get("https://api.frankfurter.app/latest",
                         params={"from": base, "to": symbols}, timeout=10)
        r.raise_for_status()             # raise if status is 4xx/5xx
        return r.json()["rates"]
    except requests.RequestException as e:
        print("API call failed:", e)
        return {}

rates = get_rates()
print(rates)
```

### Headers & authentication (the shape you'll meet often)
Most real APIs need a key in a header. The pattern (Frankfurter needs none, so this is illustrative):

```python
headers = {"Authorization": "Bearer <token>", "Accept": "application/json"}
# requests.get(url, headers=headers, params=..., timeout=10)
```

### Load the response into pandas
API JSON → DataFrame is the everyday move — now it's tabular and joinable:

```python
import pandas as pd

rates = get_rates()
fx = (pd.DataFrame(rates.items(), columns=["currency", "rate_per_usd"])
        .assign(base="USD"))
fx
```

### Put it together — convert ShopFlow revenue to USD
Combine the API rates with an orders DataFrame (the kind of enrichment you'll do for real):

```python
orders = pd.DataFrame({
    "order_id": [1, 2, 3, 4],
    "currency": ["USD", "GBP", "EUR", "INR"],
    "amount":   [120.0, 90.0, 100.0, 5000.0],
})
fx_all = pd.concat([fx, pd.DataFrame([{"currency": "USD", "rate_per_usd": 1.0, "base": "USD"}])])

usd = orders.merge(fx_all, on="currency", how="left")
usd["amount_usd"] = (usd["amount"] / usd["rate_per_usd"]).round(2)
usd[["order_id", "currency", "amount", "amount_usd"]]
```

### Pagination (when results come in pages)
Big APIs return data in pages; loop until there's no "next":

```python
# Pattern (pseudocode-ish): keep fetching until the API says there's no more
all_rows, page = [], 1
while True:
    r = requests.get("https://example.com/api/orders",
                     params={"page": page, "per_page": 100}, timeout=10)
    batch = r.json().get("data", [])
    if not batch:
        break
    all_rows.extend(batch)
    page += 1
```

## Challenge
Write `to_usd(orders_df)` that fetches live rates with `get_rates()`, joins them to an orders
DataFrame, and returns it with an `amount_usd` column — defaulting the rate to `1.0` for any
currency the API didn't return (so a missing rate never drops a row).

??? note "Solution"
    ```python
    def to_usd(orders_df):
        rates = get_rates()
        rates["USD"] = 1.0
        fx = pd.DataFrame(rates.items(), columns=["currency", "rate_per_usd"])
        out = orders_df.merge(fx, on="currency", how="left")
        out["rate_per_usd"] = out["rate_per_usd"].fillna(1.0)   # never drop a row
        out["amount_usd"] = (out["amount"] / out["rate_per_usd"]).round(2)
        return out

    to_usd(orders)
    ```

!!! tip "🎯 The same pattern on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** ingested data from a REST API and shaped it for joining.

    - **Azure Data Factory** — the **REST / HTTP connector** (Copy activity) pulls APIs no-code,
      with built-in pagination rules.
    - **Azure Databricks / Fabric** — call `requests` in a notebook exactly like this, or use a
      connector; land the result as a Bronze table.
    - **Snowflake** — **external access integrations** let Snowpark Python call APIs; or stage the
      pulled files and `COPY INTO`.

    "Pull from an API, handle errors, page through results, land it as a table" is universal.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **`requests.get(url, params=…)`** | Make an HTTP GET; `params` become the query string |
| **`status_code` / `raise_for_status()`** | Check success; raise on 4xx/5xx |
| **`.json()`** | Parse the JSON body into a Python dict/list |
| **Headers / Bearer token** | How APIs carry auth and content negotiation |
| **Pagination** | Loop pages until the API returns no more |
| **`timeout`** | Never let a call hang forever |

## You can now…
- Call a REST API with `requests`, pass params, and parse JSON
- Handle failures with `raise_for_status` and `try/except`
- Load an API response into pandas and join it to your data
- Recognise the pagination pattern for large result sets
