#!/usr/bin/env bash
# Run a PySpark job against Unity Catalog's GOVERNED `lakehouse` catalog, as a
# specific user (per-user RBAC is enforced by UC — the engine queries THROUGH UC).
#
# Usage:
#   T=$(common/uc-cli/login.sh analyst)          # the user's UC token (Keycloak)
#   common/uc-spark/run-uc-spark.sh "$T" myjob.py
#
# Auto-detects the stack: compose (docker exec spark-master) if it's running,
# else k8s (kubectl exec the spark-master pod). Requires the patched Spark image
# (UC connector + Delta baked into /opt/spark/jars — see Dockerfile.spark) and the
# patched UC server (static credential vending — see common/uc-server/).
set -euo pipefail

TOKEN="${1:?usage: run-uc-spark.sh <uc-token> <script.py>}"
SCRIPT="${2:?usage: run-uc-spark.sh <uc-token> <script.py>}"

# Shared Spark confs: map the `lakehouse` Spark catalog to UC, Delta as the default
# table provider, and S3A → MinIO (UC vends the creds; these are the fallback).
CONF=(
  --master 'local[*]'
  --conf spark.sql.catalogImplementation=in-memory
  --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension
  --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog
  --conf spark.sql.catalog.lakehouse=io.unitycatalog.spark.UCSingleCatalog
  --conf spark.sql.catalog.lakehouse.uri=http://unity-catalog:8080
  --conf spark.sql.catalog.lakehouse.token="$TOKEN"
  --conf spark.sql.defaultCatalog=lakehouse
  --conf spark.hadoop.fs.s3.impl=org.apache.hadoop.fs.s3a.S3AFileSystem
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000
  --conf spark.hadoop.fs.s3a.access.key=minioadmin
  --conf spark.hadoop.fs.s3a.secret.key=minioadmin
  --conf spark.hadoop.fs.s3a.path.style.access=true
)

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx spark-master; then
  # --- compose ---
  docker cp "$SCRIPT" spark-master:/tmp/uc_job.py
  docker exec spark-master env HOME=/tmp /opt/spark/bin/spark-submit "${CONF[@]}" /tmp/uc_job.py
else
  # --- k8s ---
  NS="${NS:-de-stack}"
  POD=$(kubectl -n "$NS" get pods -l app.kubernetes.io/name=spark-master --no-headers | awk '{print $1}' | head -1)
  kubectl -n "$NS" cp "$SCRIPT" "$POD":/tmp/uc_job.py
  kubectl -n "$NS" exec "$POD" -- env HOME=/tmp /opt/spark/bin/spark-submit "${CONF[@]}" /tmp/uc_job.py
fi
