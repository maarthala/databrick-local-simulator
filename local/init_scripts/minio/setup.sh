#!/bin/sh
# Seed MinIO with the demo buckets and sample Northwind data.
# Runs as a one-shot container (minio-init) after MinIO starts.
set -e

ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}"
SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}"

# Wait until MinIO answers, then register it as the 'local' alias.
echo "Waiting for MinIO at $ENDPOINT ..."
until mc alias set local "$ENDPOINT" "$ACCESS_KEY" "$SECRET_KEY" >/dev/null 2>&1; do
  sleep 2
done
echo "MinIO is ready."

# Buckets (idempotent).
mc mb --ignore-existing local/demo-bucket
mc mb --ignore-existing local/clickstream-bucket

# Upload the sample Northwind parquet/CSV data.
mc cp --recursive /code/shared/testdata/ local/demo-bucket/northwind/

# Pre-create the prefixes Hive/Iceberg expect (S3 has no real folders; markers suffice).
printf '' | mc pipe local/demo-bucket/hive/default/.keep
printf '' | mc pipe local/demo-bucket/warehouse/.keep
printf '' | mc pipe local/demo-bucket/iceberg/.keep

echo "Buckets after setup:"
mc ls local/
echo "MinIO setup complete."
