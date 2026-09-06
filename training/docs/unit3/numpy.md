# 3.3 NumPy — fast numeric arrays

## Concept
**NumPy** is the numerical foundation Python data work is built on — **pandas itself stores its
columns as NumPy arrays**, and so do scikit-learn, PyArrow, and most of the ecosystem. Its core
object is the **`ndarray`**: a typed, fixed-size array that supports **vectorised** operations —
math applied to the whole array at once, in fast C code, with no Python loop.

You won't write huge amounts of NumPy as a data engineer, but you need to *read* it and reach for
it for numeric transforms, and understanding it explains *why* pandas/Spark are fast.

```python
import numpy as np
```

## Lab

### Arrays and vectorised math
The whole point: operate on an entire array at once — no `for` loop.

```python
amounts = np.array([120.0, 40.0, 300.0, 90.0, 55.0])

amounts * 1.2            # add 20% tax to every element at once
amounts.sum()            # 605.0
amounts.mean()           # 121.0
amounts.max(), amounts.min()
amounts.dtype            # float64  (arrays are typed)
amounts.shape            # (5,)
```

Compare to plain Python — same result, but NumPy does it in one vectorised step instead of a loop:

```python
# plain Python (a loop)      vs      NumPy (vectorised)
taxed_loop = [a * 1.2 for a in amounts]
taxed_np   = amounts * 1.2
```

### Boolean masks & `where`
Vectorised filtering and conditionals — the pattern pandas uses under the hood:

```python
mask = amounts > 100            # array([ True, False,  True, False, False])
amounts[mask]                   # array([120., 300.]) — keep matching elements

# np.where(cond, if_true, if_false) — vectorised CASE WHEN
band = np.where(amounts >= 100, "large", "small")
```

### Aggregations & simple stats
```python
np.round(amounts, 2)
np.percentile(amounts, 50)      # median
np.cumsum(amounts)              # running total (like SQL SUM() OVER)
```

### 2-D arrays (a matrix) & axes
```python
grid = np.array([[1, 2, 3],
                 [4, 5, 6]])
grid.shape          # (2, 3)
grid.sum(axis=0)    # column sums → [5, 7, 9]
grid.sum(axis=1)    # row sums    → [6, 15]
```

### Reproducible random data (handy for tests/samples)
```python
rng = np.random.default_rng(seed=42)   # seed → same numbers every run
rng.integers(1, 100, size=5)
```

### NumPy ⇄ pandas
They're two sides of one coin — a pandas column *is* a NumPy array:

```python
import pandas as pd
s = pd.Series(amounts)
s.to_numpy()               # pandas → NumPy
pd.Series(np.arange(5))    # NumPy → pandas
```

## Challenge
Given `amounts = np.array([120., 40., 300., 90., 55.])`, use NumPy (no loops) to compute: the
**share of total** each amount represents (as percentages, rounded to 1 decimal), and a label
array marking each as `"above"` or `"below"` the mean.

??? note "Solution"
    ```python
    amounts = np.array([120., 40., 300., 90., 55.])
    share = np.round(amounts / amounts.sum() * 100, 1)     # [19.8, 6.6, 49.6, 14.9, 9.1]
    label = np.where(amounts > amounts.mean(), "above", "below")
    print(share)
    print(label)
    ```

!!! tip "🎯 The same NumPy on Azure, Databricks, Snowflake & Fabric"
    NumPy is pure Python numerics — it runs identically in **Databricks**, **Fabric**, and
    **Synapse** notebooks and in **Snowpark** Python. At scale, the *vectorised* idea reappears:
    Spark and Snowflake execute column operations in bulk (like NumPy) instead of row-by-row —
    which is exactly why they're fast.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **`ndarray`** | A typed, fixed-size numeric array |
| **Vectorised op** | Math on a whole array at once (no Python loop) |
| **dtype** | The element type (`float64`, `int64`, …) |
| **Boolean mask** | `arr[arr > x]` — keep matching elements |
| **`np.where`** | Vectorised if/else (CASE WHEN) |
| **axis** | Which dimension to aggregate over (0=cols, 1=rows) |

## You can now…
- Create arrays and run vectorised math and aggregations (no loops)
- Filter with boolean masks and branch with `np.where`
- Explain why NumPy underlies pandas — and why vectorisation makes engines fast
