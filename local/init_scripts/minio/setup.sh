#!/bin/sh
# Seed the object store (RustFS, S3-compatible; MinIO's mc works against it) with the demo bucket.
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

# Learner access: home-api / JupyterHub create, per learner, the bucket <user>-lake with a
# hard quota and a storage policy named after the user (only that bucket; instructors:
# everything) — RustFS doesn't expand ${jwt:…} in resources, so there's no shared policy.

echo "Buckets after setup:"
mc ls local/
echo "MinIO setup complete."
