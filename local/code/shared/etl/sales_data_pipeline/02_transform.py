from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp
import sys

def main():
    conf = SparkConf() \
        .setAppName("Transform Sales Data") \
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
        
        # Read customer sales data
        print("Reading customer_sales_data...")
        customer_sales_df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "customer_sales_data") \
            .option("user", "postgres") \
            .option("password", "postgres") \
            .option("driver", "org.postgresql.Driver") \
            .load()

        # Read regional commission data
        print("Reading regional_commision...")
        regional_commission_df = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "regional_commision") \
            .option("user", "postgres") \
            .option("password", "postgres") \
            .option("driver", "org.postgresql.Driver") \
            .load()

        # Perform join transformation
        print("Performing join transformation...")
        transformed_df = customer_sales_df.alias("csd") \
            .join(regional_commission_df.alias("rc"), 
                  customer_sales_df.region == regional_commission_df.region_name) \
            .select("csd.customer_id", "csd.customer_name", "csd.region", 
                    "csd.sale_date", "csd.sale_amount", "csd.product", 
                    "rc.sale_commision") \
            .withColumn("last_updated", current_timestamp())

        print("Transformed data preview:")
        transformed_df.show()

        # Write transformed data to PostgreSQL
        print("Writing transformed data to tmp_customer_sales_with_commission...")
        transformed_df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "tmp_customer_sales_with_commission") \
            .option("user", "postgres") \
            .option("password", "postgres") \
            .option("driver", "org.postgresql.Driver") \
            .mode("overwrite") \
            .save()

        print("Transformation completed successfully!")
        
    except Exception as e:
        print(f"[ERROR] Transform job failed: {e}")
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
