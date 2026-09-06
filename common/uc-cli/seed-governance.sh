#!/usr/bin/env bash
# Stack-admin seed: provision a GOVERNED Unity Catalog for the training course.
# Run once by whoever operates the stack (e.g. `make uc-seed` in local/) — NOT by learners.
# Learners then browse/inspect it container-free with the `uc` CLI + login.sh + the UC web UI.
#
# Creates the `shopflow` UC catalog with bronze/silver/gold schemas and the medallion
# access policy for the three fixed personas (see training/docs/setup/personas.md):
#   analyst  -> reads gold only            (BI / analytics)
#   engineer -> works in silver, reads gold (builds the pipeline)
#   lead     -> full access to every layer  (data lead / owner)
set -euo pipefail

SRV="${UC_URL:-http://localhost:8081}"
# The admin (bootstrap) token lives inside the unity-catalog container; the operator reads it here.
ADMIN="$(docker exec unity-catalog cat etc/conf/token.txt)"
u() { uc --server "$SRV" --auth_token "$ADMIN" "$@"; }
grant() { u permission create --securable_type "$1" --name "$2" --privilege "$3" --principal "$4" 2>/dev/null || true; }

echo "Creating the persona UC users (matched to Keycloak by email)…"
u user create --name "Ava Analyst"    --email analyst@dev-epireum.com  2>/dev/null || true
u user create --name "Eddie Engineer" --email engineer@dev-epireum.com 2>/dev/null || true
u user create --name "Lena Lead"      --email lead@dev-epireum.com     2>/dev/null || true

echo "Provisioning governed 'shopflow' catalog…"
u catalog create --name shopflow                         2>/dev/null || true
for s in bronze silver gold; do
  u schema create --catalog shopflow --name "$s"         2>/dev/null || true
done

echo "Granting the medallion access policy…"
# --- analyst: read gold only ---
grant catalog shopflow      "USE CATALOG" analyst@dev-epireum.com
grant schema  shopflow.gold "USE SCHEMA"  analyst@dev-epireum.com
grant schema  shopflow.gold "SELECT"      analyst@dev-epireum.com

# --- engineer: work in silver (read + create), read gold ---
grant catalog shopflow        "USE CATALOG" engineer@dev-epireum.com
grant schema  shopflow.silver "USE SCHEMA"  engineer@dev-epireum.com
grant schema  shopflow.silver "SELECT"      engineer@dev-epireum.com
grant schema  shopflow.silver "CREATE TABLE" engineer@dev-epireum.com
grant schema  shopflow.gold   "USE SCHEMA"  engineer@dev-epireum.com
grant schema  shopflow.gold   "SELECT"      engineer@dev-epireum.com

# --- lead: full access to every layer (owner) ---
grant catalog shopflow "USE CATALOG" lead@dev-epireum.com
for s in bronze silver gold; do
  grant schema "shopflow.$s" "USE SCHEMA"   lead@dev-epireum.com
  grant schema "shopflow.$s" "SELECT"       lead@dev-epireum.com
  grant schema "shopflow.$s" "CREATE TABLE" lead@dev-epireum.com
done

echo "Done. Browse it: uc --server $SRV --auth_token \$(common/uc-cli/login.sh analyst) catalog list"
