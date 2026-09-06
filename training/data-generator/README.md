# ShopFlow data generator

Creates the "living business" the course is built on: the OLTP database, years of
historical orders in object storage, and a daily simulator for ongoing activity.

## Components
| File | Purpose |
|---|---|
| `seed.sql` | ShopFlow OLTP schema (`customers, products, orders, order_items`) + a tiny seed, loaded into Postgres as database `shopflow`. |
| `load_history.py` | Generates *years* of historical orders and lands them in MinIO/S3 as **date-partitioned Parquet** (`s3://shopflow/history/orders/dt=YYYY-MM-DD/…`). The raw Bronze source. |
| `simulate_day.py` | Generates **one day** of activity — new orders, a few product price changes, and occasionally a **late-arriving** record. Run repeatedly to advance the business. |

## Usage
```bash
# 1. create + seed the OLTP database (into the stack's Postgres)
#    local:  docker exec -i postgres psql -U postgres < seed.sql
#    k8s:    kubectl -n de-stack exec -i deploy/postgres -- psql -U postgres < seed.sql

# 2. land historical orders in the lake (MinIO)
python load_history.py --from 2023-01-01 --to 2024-12-31 --bucket shopflow

# 3. advance the business by one day (run daily, or on demand)
python simulate_day.py --date 2025-01-01
```

`load_history.py` and `simulate_day.py` are Python (pandas + pyarrow + boto3/minio).
They're intentionally small and readable — learners inspect them to understand where
data comes from and why pipelines must handle updates + late data.

> **Design note:** volumes are tuned to be *small enough to run on the local stack*
> but shaped to teach real concepts — date partitioning, incremental loads, and
> late-arriving records. Adjust the row counts at the top of each script.
