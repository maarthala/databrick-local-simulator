# 3.4 PyArrow — Parquet & the columnar bridge

## Concept
**Apache Arrow** is a language-agnostic **columnar in-memory format**, and **PyArrow** is its
Python library. You rarely program *directly* against it, but it's quietly everywhere in data
engineering — and worth understanding because it does two jobs no other tool does as well:

1. **It reads and writes Parquet.** The [columnar file format from 1.3](../unit1/formats.md) —
   the one the lakehouse stores everything in — is read/written by Arrow. `pandas.read_parquet`
   is PyArrow under the hood.
2. **It's the zero-copy bridge between tools.** pandas, Spark (`toPandas()`), Trino, DuckDB, and
   Snowflake all speak Arrow to hand data to each other *without re-serializing* — it's the
   lingua franca that makes moving data between engines fast.

Think of it this way: **Parquet is Arrow written to disk; Arrow is Parquet loaded into memory.**

```python
import pyarrow as pa
import pyarrow.parquet as pq
```

## Lab

### An Arrow Table
Arrow's table is columnar and **strongly typed** (every column has an explicit type — unlike a
loose Python list):

```python
import pandas as pd

df = pd.DataFrame({
    "order_id": [1, 2, 3],
    "country":  ["US", "UK", "DE"],
    "amount":   [120.0, 40.0, 300.0],
})

table = pa.Table.from_pandas(df)   # pandas → Arrow
print(table.schema)                # typed columns: order_id: int64, country: string, amount: double
print(table.num_rows, table.num_columns)
```

### Write & read Parquet
This is the everyday use — persist a DataFrame as Parquet and read it back:

```python
pq.write_table(table, "/tmp/orders.parquet")           # write Parquet
back = pq.read_table("/tmp/orders.parquet")            # read it back (Arrow Table)
back.to_pandas()                                       # Arrow → pandas

# pandas' own helpers use PyArrow underneath:
df.to_parquet("/tmp/orders2.parquet")
pd.read_parquet("/tmp/orders2.parquet")
```

### Column projection — the columnar win
Because Parquet stores each column separately, you can read **only the columns you need** — far
less I/O than reading the whole file (the same idea as Trino's projection pushdown in Unit 2):

```python
pq.read_table("/tmp/orders.parquet", columns=["order_id", "amount"]).to_pandas()
```

### Inspect Parquet without loading it
Read just the metadata — schema, row counts, row groups — instantly, without scanning data:

```python
meta = pq.read_metadata("/tmp/orders.parquet")
print(meta.num_rows, meta.num_row_groups)
print(pq.read_schema("/tmp/orders.parquet"))
```

### Partitioned datasets + predicate pushdown
Real lakehouse data is **partitioned** into folders (like the `dt=…` history in Unit 4). PyArrow's
`dataset` API reads a whole partitioned tree and pushes filters down so it skips folders it
doesn't need:

```python
import pyarrow.dataset as ds

# write a partitioned dataset (partition folders by country)
pq.write_to_dataset(table, root_path="/tmp/orders_ds", partition_cols=["country"])

dataset = ds.dataset("/tmp/orders_ds", format="parquet", partitioning="hive")
# read only US rows, only two columns — Arrow prunes partitions + columns
dataset.to_table(filter=ds.field("country") == "US",
                 columns=["order_id", "amount"]).to_pandas()
```

!!! tip "Why this matters for the lakehouse"
    Every Parquet file in `iceberg.bronze/silver/gold` (Unit 4) is Arrow-on-disk. When Spark does
    `.toPandas()` or Trino returns rows to the Python client, Arrow is the wire format. Learning
    it explains *why* columnar + partition pruning make the whole lakehouse fast.

## Challenge
Write the 3-row `df` to `/tmp/shopflow.parquet`, then use PyArrow to (a) print the schema and row
count from the **metadata only** (without reading the data), and (b) read back **only** the
`country` and `amount` columns.

??? note "Solution"
    ```python
    import pyarrow as pa, pyarrow.parquet as pq
    pq.write_table(pa.Table.from_pandas(df), "/tmp/shopflow.parquet")

    # (a) metadata only — no data scan
    meta = pq.read_metadata("/tmp/shopflow.parquet")
    print("rows:", meta.num_rows)
    print(pq.read_schema("/tmp/shopflow.parquet"))

    # (b) column projection
    pq.read_table("/tmp/shopflow.parquet", columns=["country", "amount"]).to_pandas()
    ```

!!! tip "🎯 The same Arrow/Parquet on Azure, Databricks, Snowflake & Fabric"
    Arrow and Parquet are **industry standards**, not a local quirk:

    - **Azure Databricks / Microsoft Fabric** — Delta/Parquet on ADLS/OneLake *is* this format;
      Spark uses Arrow for `toPandas()` and Python UDF transport.
    - **Snowflake** — Iceberg tables store Parquet; the Python connector returns results as Arrow
      (`fetch_arrow_all` / `to_pandas`).
    - **Azure Data Factory** — reads/writes Parquet natively as a Copy source/sink.

    Parquet-on-storage + Arrow-in-transit is the same everywhere — this knowledge is fully portable.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Apache Arrow** | Language-agnostic *columnar in-memory* format |
| **PyArrow** | Python library for Arrow + Parquet |
| **Arrow Table** | A typed, columnar in-memory table |
| **Parquet** | Columnar *on-disk* format (Arrow written to storage) |
| **Column projection** | Read only the columns you need |
| **`dataset` + filter** | Read a partitioned tree with partition/predicate pruning |
| **Zero-copy bridge** | Hand data between engines (pandas/Spark/Trino) without re-serializing |

## You can now…
- Convert between pandas and Arrow, and read/write **Parquet** with PyArrow
- Read only the columns you need (projection) and inspect metadata without a scan
- Read partitioned datasets with partition + predicate pruning
- Explain how Arrow/Parquet make pandas, Spark, and the lakehouse interoperate fast
