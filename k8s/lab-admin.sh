#!/usr/bin/env bash
# The platform manager's toolkit on Kubernetes — runs labadmin.py inside the home-api pod
# (it holds the Polaris / storage / SQLPad admin logins; the Keycloak admin password is read
# from de-stack-secrets for this one call).
#   bash k8s/lab-admin.sh list
#   bash k8s/lab-admin.sh create <user> [password]      new lab account + lakehouse
#   bash k8s/lab-admin.sh password <user> [password]    new password (changed at next sign-in)
#   bash k8s/lab-admin.sh reset-lakehouse <user>        drop every table in their catalogs
#   bash k8s/lab-admin.sh wipe <user>                   tables + bucket + Jupyter files → fresh start
#   bash k8s/lab-admin.sh delete <user> --yes           remove the account and everything it owns
# On the node: KUBECTL="microk8s kubectl" bash lab-admin.sh …
set -euo pipefail
NAMESPACE="${NAMESPACE:-de-stack}"
KUBECTL="${KUBECTL:-kubectl}"
k() { $KUBECTL -n "$NAMESPACE" "$@"; }

if { [ "${1:-}" = wipe ] || { [ "${1:-}" = delete ] && [ "${3:-}" = --yes ]; }; } && [ -n "${2:-}" ]; then
  # their Jupyter volume would sync the old notebooks back into the bucket: stop the server, drop it
  k delete pod "jupyter-$2" --ignore-not-found --wait=true
  k delete pvc "claim-$2" --ignore-not-found --wait=true
fi
KC_PW=$(k get secret de-stack-secrets -o jsonpath='{.data.keycloak-admin-password}' | base64 -d)
k exec deploy/home-api -- env KEYCLOAK_ADMIN="admin:$KC_PW" python /app/labadmin.py "$@"
