from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum, col
from datetime import datetime
import sys

def main():
    conf = SparkConf() \
        .setAppName("Load Finance Data") \
        .setMaster("spark://spark-master:7077") \
        .set("spark.executor.memory", "1g") \
        .set("spark.driver.memory", "1g")

    try:
        spark.stop()
    except:
        pass
        
    try:
        spark = SparkSession.builder.config(conf=conf).getOrCreate()
        
        jdbc_url = "jdbc:postgresql://postgres:5432/sales_db"
        
        # Read transformed data
        print("Reading tmp_customer_sales_with_commission...")
        df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "tmp_customer_sales_with_commission") \
            .option("user", "postgres") \
            .option("password", "postgres") \
            .option("driver", "org.postgresql.Driver") \
            .load()

        df.show()

        # Create aggregated DataFrame: region and total commission amount
        commission_df = df.select("region", "sale_amount", "sale_commision") \
            .withColumn("commission_amt", col("sale_amount") * col("sale_commision")) \
            .groupBy("region") \
            .agg(spark_sum("commission_amt").alias("sales_commission_amt"))

        print("Commission by Region:")
        commission_df.show()

        # Save commission DataFrame to S3 with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        commission_data_path = f"s3a://demo-bucket/northwind/sales_commision/{timestamp}.csv"

        print(f"Saving commission data to: {commission_data_path}")
        commission_df.coalesce(1).write.mode("overwrite").option("header", "true").csv(commission_data_path)
        print("Commission data saved successfully!")
        
    except Exception as e:
        print(f"[ERROR] Load job failed: {e}")
        try:
            spark.stop()
        except:
            pass
        sys.exit(1)

    finally:
        if 'spark' in locals():
            spark.stop()

if __name__ == "__main__":
    main()
