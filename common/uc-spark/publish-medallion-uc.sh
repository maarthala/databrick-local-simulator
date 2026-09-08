#!/usr/bin/env bash
# Publish the Iceberg medallion into the GOVERNED Unity Catalog `lakehouse`
# (Delta on MinIO), so Spark can query it through UC with per-user RBAC.
#
# Runs local[*] on the spark-master container with BOTH catalogs wired:
#   iceberg (read the existing medallion) + lakehouse=UCSingleCatalog (write Delta).
# Writes use the UC bootstrap admin token — per-user writes are a UC-server limit
# on OSS (generateTemporaryPathCredentials 403), so the pipeline writes as admin.
#
# Usage:  common/uc-spark/publish-medallion-uc.sh            # all layers
#         common/uc-spark/publish-medallion-uc.sh gold.daily_sales,silver.orders
set -euo pipefail

ONLY="${1:-}"
JOB="local/code/shared/jobs/publish_uc.py"
[ -f "$JOB" ] || JOB="code/shared/jobs/publish_uc.py"   # if run from local/

# The only principal UC authorizes to WRITE new table paths is the bootstrap admin.
ADMIN=$(docker exec unity-catalog cat etc/conf/token.txt)

docker cp "$JOB" spark-master:/tmp/publish_uc.py
docker exec spark-master env HOME=/tmp /opt/spark/bin/spark-submit --master 'local[*]' \
  --conf spark.sql.catalogImplementation=in-memory \
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
  --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
  --conf spark.sql.catalog.lakehouse=io.unitycatalog.spark.UCSingleCatalog \
  --conf spark.sql.catalog.lakehouse.uri=http://unity-catalog:8080 \
  --conf spark.sql.catalog.lakehouse.token="$ADMIN" \
  --conf spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.iceberg.type=rest \
  --conf spark.sql.catalog.iceberg.uri=http://iceberg-rest:8181 \
  --conf spark.sql.catalog.iceberg.warehouse=s3://demo-bucket/iceberg/ \
  --conf spark.sql.catalog.iceberg.io-impl=org.apache.iceberg.aws.s3.S3FileIO \
  --conf spark.sql.catalog.iceberg.s3.endpoint=http://minio:9000 \
  --conf spark.sql.catalog.iceberg.s3.path-style-access=true \
  --conf spark.sql.catalog.iceberg.s3.access-key-id=minioadmin \
  --conf spark.sql.catalog.iceberg.s3.secret-key=minioadmin \
  --conf spark.hadoop.fs.s3.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=minioadmin \
  --conf spark.hadoop.fs.s3a.secret.key=minioadmin \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  /tmp/publish_uc.py ${ONLY:+--only "$ONLY"}
