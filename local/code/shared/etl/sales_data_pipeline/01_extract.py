from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession
import sys

def main():
    conf = SparkConf() \
        .setAppName("Extract Sales Data") \
        .setMaster("spark://spark-master:7077") \
        .set("spark.executor.memory", "1g") \
        .set("spark.driver.memory", "1g")

    try:
        spark.stop()
    except:
        pass
        
    try:
        spark = SparkSession.builder.config(conf=conf).getOrCreate()
        
        print("Hadoop version:", spark.sparkContext._jvm.org.apache.hadoop.util.VersionInfo.getVersion())
        
        # Read CSV from S3
        data_path = "s3a://demo-bucket/northwind/sales/customer_sales_data.csv"
        df = spark.read.csv(data_path, header=True, inferSchema=True)
        
        print("Extracted data preview:")
        df.show()
        
        # Write to PostgreSQL
        jdbc_url = "jdbc:postgresql://postgres:5432/sales_db"
        df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "customer_sales_data") \
            .option("user", "postgres") \
            .option("password", "postgres") \
            .option("driver", "org.postgresql.Driver") \
            .mode("overwrite") \
            .save()
            
        print(f"Successfully loaded {df.count()} records to customer_sales_data table")
        
    except Exception as e:
        print(f"[ERROR] Extract job failed: {e}")
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
