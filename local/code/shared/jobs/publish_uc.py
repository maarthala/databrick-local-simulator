"""Publish the Iceberg medallion into the GOVERNED Unity Catalog `lakehouse`.

Reads the existing `iceberg.<layer>.<table>` tables and writes them as Delta
tables in UC's `lakehouse` catalog, on MinIO, so Spark can query them THROUGH
Unity Catalog with per-user RBAC (see common/uc-spark/).

Run it with common/uc-spark/publish-medallion-uc.sh, which wires BOTH catalogs
(iceberg to read, lakehouse=UCSingleCatalog to write) and passes the write token.

NOTE: writes run as the pipeline/admin principal — per-user writes hit a
UC-server authorization limit on OSS (generateTemporaryPathCredentials 403), so
the pipeline writes; humans get governed *reads*.
"""
import argparse
from pyspark.sql import SparkSession

# (layer, table) pairs mirrored from Iceberg into the UC lakehouse.
MEDALLION = [
    ("bronze", "customers"), ("bronze", "orders"),
    ("bronze", "order_items"), ("bronze", "products"),
    ("silver", "orders"),
    ("gold", "daily_sales"), ("gold", "top_products"), ("gold", "customer_ltv"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warehouse", default="s3://demo-bucket/lakehouse",
                    help="base storage path for the UC lakehouse tables")
    ap.add_argument("--only", default="", help="comma-separated layer.table subset (optional)")
    args = ap.parse_args()

    spark = SparkSession.builder.getOrCreate()
    want = set(args.only.split(",")) if args.only else None

    def clear(loc):
        # External tables keep their files after DROP; the UC connector also rejects
        # REPLACE-with-LOCATION. So wipe the path via Hadoop FS to keep this idempotent.
        jvm = spark.sparkContext._jvm
        hconf = spark.sparkContext._jsc.hadoopConfiguration()
        p = jvm.org.apache.hadoop.fs.Path(loc)
        fs = p.getFileSystem(hconf)
        if fs.exists(p):
            fs.delete(p, True)

    for layer, tbl in MEDALLION:
        fq = f"{layer}.{tbl}"
        if want and fq not in want:
            continue
        src = f"iceberg.{layer}.{tbl}"
        dst = f"lakehouse.{layer}.{tbl}"
        loc = f"{args.warehouse}/{layer}/{tbl}"
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS lakehouse.{layer}")
        spark.sql(f"DROP TABLE IF EXISTS {dst}")   # clear UC metadata
        clear(loc)                                 # clear the physical Delta files
        spark.sql(f"CREATE TABLE {dst} USING delta LOCATION '{loc}' AS SELECT * FROM {src}")
        n = spark.sql(f"SELECT count(*) c FROM {dst}").collect()[0][0]
        print(f"PUBLISHED {dst} rows={n}")


if __name__ == "__main__":
    main()
