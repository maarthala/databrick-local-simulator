"""ShopFlow Silver — clean + join Bronze into one order-line table (Iceberg)."""
import argparse
from pyspark.sql import SparkSession, functions as F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="iceberg")
    ap.add_argument("--date", default=None)
    ap.add_argument("--mode", default="full")
    args = ap.parse_args()
    cat = args.catalog

    spark = SparkSession.builder.appName("shopflow_build_silver").getOrCreate()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {cat}.silver")

    o = (spark.table(f"{cat}.bronze.orders")
         .withColumn("order_date", F.to_date("order_ts"))
         .filter(F.col("order_id").isNotNull() & F.col("customer_id").isNotNull())
         .dropDuplicates(["order_id"]))
    i = (spark.table(f"{cat}.bronze.order_items")
         .withColumn("quantity", F.col("quantity").cast("int"))
         .withColumn("unit_price", F.col("unit_price").cast("decimal(12,2)"))
         .dropDuplicates(["order_id", "product_id"]))
    c = spark.table(f"{cat}.bronze.customers").dropDuplicates(["customer_id"])
    p = spark.table(f"{cat}.bronze.products").dropDuplicates(["product_id"])

    silver = (i.alias("i")
              .join(o.alias("o"), "order_id")
              .join(c.alias("c"), "customer_id", "left")
              .join(p.alias("p"), "product_id", "left")
              .select(
                  F.col("o.order_id"), F.col("o.order_date"), F.col("o.customer_id"),
                  F.col("c.full_name").alias("customer_name"), F.col("c.country"), F.col("o.channel"),
                  F.col("i.product_id"), F.col("p.name").alias("product_name"), F.col("p.category"),
                  F.col("i.quantity"), F.col("i.unit_price"),
                  (F.col("i.quantity") * F.col("i.unit_price")).cast("decimal(12,2)").alias("line_amount"),
                  F.col("o.status")))
    silver.writeTo(f"{cat}.silver.orders").using("iceberg").createOrReplace()
    print("SILVER_ROWS", spark.table(f"{cat}.silver.orders").count())
    spark.stop()


if __name__ == "__main__":
    main()
