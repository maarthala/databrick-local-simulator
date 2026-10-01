"""ShopFlow Gold — business marts from Silver (Iceberg).

--mart daily_sales | top_products | customer_ltv | all  (default: all)
"""
import argparse
from pyspark.sql import SparkSession, functions as F


def build_daily(spark, cat, S):
    daily = spark.sql(f"""
        SELECT order_date, count(DISTINCT order_id) AS orders,
               sum(line_amount) AS revenue, sum(quantity) AS units
        FROM {S} WHERE status='delivered' GROUP BY order_date""")
    daily.writeTo(f"{cat}.gold.daily_sales").using("iceberg").partitionedBy(F.months("order_date")).createOrReplace()
    print("GOLD_DAYS", spark.table(f"{cat}.gold.daily_sales").count())


def build_top(spark, cat, S):
    top = spark.sql(f"""
        WITH pr AS (SELECT product_id, product_name, category,
                           sum(line_amount) AS revenue, sum(quantity) AS units
                    FROM {S} WHERE status='delivered' GROUP BY product_id, product_name, category)
        SELECT *, rank() OVER (ORDER BY revenue DESC) AS revenue_rank FROM pr""")
    top.writeTo(f"{cat}.gold.top_products").using("iceberg").createOrReplace()
    print("GOLD_TOP_PRODUCTS", spark.table(f"{cat}.gold.top_products").count())


def build_ltv(spark, cat, S):
    ltv = spark.sql(f"""
        SELECT customer_id, customer_name, country,
               count(DISTINCT order_id) AS lifetime_orders, sum(line_amount) AS lifetime_value,
               min(order_date) AS first_order, max(order_date) AS last_order
        FROM {S} WHERE status='delivered' GROUP BY customer_id, customer_name, country""")
    ltv.writeTo(f"{cat}.gold.customer_ltv").using("iceberg").createOrReplace()
    print("GOLD_CUSTOMER_LTV", spark.table(f"{cat}.gold.customer_ltv").count())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="iceberg")
    ap.add_argument("--date", default=None)
    ap.add_argument("--mode", default="full")
    ap.add_argument("--mart", default="all", choices=["daily_sales", "top_products", "customer_ltv", "all"])
    args = ap.parse_args()
    cat = args.catalog

    spark = SparkSession.builder.appName("shopflow_build_gold").getOrCreate()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {cat}.gold")
    S = f"{cat}.silver.orders"

    if args.mart in ("daily_sales", "all"):
        build_daily(spark, cat, S)
    if args.mart in ("top_products", "all"):
        build_top(spark, cat, S)
    if args.mart in ("customer_ltv", "all"):
        build_ltv(spark, cat, S)
    spark.stop()


if __name__ == "__main__":
    main()
