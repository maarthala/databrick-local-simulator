#!/usr/bin/env bash
# Run a PySpark job against Unity Catalog's GOVERNED `lakehouse` catalog, as a
# specific user (per-user RBAC is enforced by UC).
#
# Usage:
#   T=$(tools/uc-cli/login.sh analyst)        # get the analyst's UC token (Keycloak)
#   tools/uc-spark/run-uc-spark.sh "$T" myjob.py
#
# Requires the patched Spark image (connectors baked into /opt/spark/jars — see
# stack/dockerfiles/Dockerfile.spark + stack/dockerfiles/uc-jars/) and the patched
# Unity Catalog server (static credential vending — see tools/uc-server/).
set -euo pipefail

TOKEN="${1:?usage: run-uc-spark.sh <uc-token> <script.py>}"
SCRIPT="${2:?usage: run-uc-spark.sh <uc-token> <script.py>}"
NS="${NS:-de-stack}"
POD=$(kubectl -n "$NS" get pods -l app.kubernetes.io/name=spark-master --no-headers | awk '{print $1}' | head -1)

kubectl -n "$NS" cp "$SCRIPT" "$POD":/tmp/uc_job.py
kubectl -n "$NS" exec "$POD" -- env HOME=/tmp /opt/spark/bin/spark-submit \
  --master 'local[*]' --conf spark.jars.ivy=/tmp/.ivy2 \
  --packages "io.delta:delta-spark_4.0_2.13:4.3.1,io.unitycatalog:unitycatalog-spark_4.0_2.13:0.5.0,io.unitycatalog:unitycatalog-hadoop:0.5.0" \
  --conf spark.sql.catalogImplementation=in-memory \
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
  --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
  --conf spark.sql.catalog.lakehouse=io.unitycatalog.spark.UCSingleCatalog \
  --conf spark.sql.catalog.lakehouse.uri=http://unity-catalog:8080 \
  --conf spark.sql.catalog.lakehouse.token="$TOKEN" \
  --conf spark.sql.defaultCatalog=lakehouse \
  --conf spark.hadoop.fs.s3.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=minioadmin \
  --conf spark.hadoop.fs.s3a.secret.key=minioadmin \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  /tmp/uc_job.py

# NOTE: the UC connector jars are baked into the image (system classpath) so the
# S3A vended-credential provider resolves. The 0.5.0 coords in --packages only pull
# transitive deps; the baked 0.7.0-SNAPSHOT classes win via parent-first loading.
