#!/usr/bin/env bash
# Create the platform's admin/service secrets for a TEAM stack — once, with random values.
# Nothing here is published: the platform manager reads a value when needed, e.g.
#   kubectl -n de-stack get secret de-stack-secrets -o jsonpath='{.data.polaris-root-secret}' | base64 -d
# Idempotent: an existing secret is left untouched (re-running never rotates anything).
#   NAMESPACE=de-stack KUBECTL="kubectl" bash k8s/create-secrets.sh
set -euo pipefail
NAMESPACE="${NAMESPACE:-de-stack}"
KUBECTL="${KUBECTL:-kubectl}"
NAME="${SECRET_NAME:-de-stack-secrets}"

if $KUBECTL -n "$NAMESPACE" get secret "$NAME" >/dev/null 2>&1; then
  echo "secret $NAME exists — left as is"; exit 0
fi
rand() { openssl rand -hex 16; }   # 32 hex chars, no pipe (pipefail-safe)
args=()
for key in \
    postgres-password pg-airflow-password pg-polaris-password pg-keycloak-password pg-superset-password \
    polaris-root-secret polaris-persona-secret trino-lab-secret storage-root-password \
    keycloak-admin-password manager-password sqlpad-admin-password superset-admin-password airflow-admin-password; do
  args+=("--from-literal=$key=$(rand)")
done
$KUBECTL -n "$NAMESPACE" create secret generic "$NAME" "${args[@]}" >/dev/null
echo "secret $NAME created (14 random values)"
