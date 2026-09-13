# Auto-create a Databricks-style `spark` session in every notebook (IPython startup).
# Uses SPARK_REMOTE (sc://spark-connect:15002) set in the image, so no config needed.
# Wrapped so a down spark-connect doesn't break kernel startup.
try:
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    print(f"✓ `spark` ready via Spark Connect (Spark {spark.version})")
except Exception as _e:  # noqa: BLE001
    print(f"⚠ `spark` not created ({_e}).")
    print("  Start it once spark-connect is up: spark = SparkSession.builder.getOrCreate()")
