#!/bin/sh
# Seed MinIO with the demo bucket.
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

# SSO policies (MinIO console "Login with SSO" via Keycloak; the token's `policy` claim
# carries the user's group). learners: ONLY their own bucket <username>-lake (created at
# registration by home-api). instructors: everything. Idempotent (create = upsert).
cat > /tmp/learners.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation", "s3:ListBucketMultipartUploads"],
      "Resource": ["arn:aws:s3:::${jwt:preferred_username}-lake"] },
    { "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                 "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"],
      "Resource": ["arn:aws:s3:::${jwt:preferred_username}-lake/*"] }
  ]
}
JSON
cat > /tmp/instructors.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["admin:*"] },
    { "Effect": "Allow", "Action": ["s3:*"], "Resource": ["arn:aws:s3:::*"] }
  ]
}
JSON
mc admin policy create local learners /tmp/learners.json
mc admin policy create local instructors /tmp/instructors.json

echo "Buckets after setup:"
mc ls local/
echo "MinIO setup complete."
