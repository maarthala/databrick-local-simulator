from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession

def main():
    conf = SparkConf() \
    .setAppName("spark-airflow-test") \
    .setMaster("spark://spark-master:7077") \
    .set("spark.executor.memory", "1g") \
    .set("spark.driver.memory", "1g") \

    try:
        spark.stop()
    except:
        pass
        
    try:
        spark = SparkSession.builder.config(conf=conf).getOrCreate()
        df = spark.createDataFrame([(1, "Alice"), (2, "Bob")], ["id", "name"])
        df.show()
    except Exception as e:
        print(f"[ERROR] Spark job failed: {e}")
        # Optionally stop Spark to clean up
        try:
            spark.stop()
        except:
            pass
        sys.exit(1)  # Exit with error

    finally:
        if 'spark' in locals():
            spark.stop()

if __name__ == "__main__":
    main()