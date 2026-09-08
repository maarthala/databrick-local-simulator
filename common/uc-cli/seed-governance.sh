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

echo "Provisioning the GOVERNED 'lakehouse' catalog (Spark-through-UC, per-user reads)…"
# Unlike 'shopflow' (governance metadata only), 'lakehouse' holds real Delta tables
# that Spark reads THROUGH Unity Catalog with per-user RBAC enforced at query time
# (see common/uc-spark/run-uc-spark.sh). Populate the tables with
# common/uc-spark/publish-medallion-uc.sh (writes run as the pipeline/admin
# principal — per-user WRITES are a UC-server limitation on OSS).
u catalog create --name lakehouse                        2>/dev/null || true
for s in bronze silver gold; do
  u schema create --catalog lakehouse --name "$s"        2>/dev/null || true
done
# Medallion access policy (READS enforced per-user via the Spark UC connector):
grant catalog lakehouse       "USE CATALOG"  analyst@dev-epireum.com
grant schema  lakehouse.gold  "USE SCHEMA"   analyst@dev-epireum.com
grant schema  lakehouse.gold  "SELECT"       analyst@dev-epireum.com
grant catalog lakehouse       "USE CATALOG"  engineer@dev-epireum.com
for s in silver gold; do
  grant schema "lakehouse.$s" "USE SCHEMA"   engineer@dev-epireum.com
  grant schema "lakehouse.$s" "SELECT"       engineer@dev-epireum.com
done
grant schema  lakehouse.silver "CREATE TABLE" engineer@dev-epireum.com
grant catalog lakehouse       "USE CATALOG"  lead@dev-epireum.com
for s in bronze silver gold; do
  grant schema "lakehouse.$s" "USE SCHEMA"   lead@dev-epireum.com
  grant schema "lakehouse.$s" "SELECT"       lead@dev-epireum.com
  grant schema "lakehouse.$s" "CREATE TABLE" lead@dev-epireum.com
done

echo "Granting the admin identity catalog-creation rights (Unit 6 self-serve lab)…"
# The `admin` Keycloak user (email admin@dev-epireum.com) maps to this UC user; a
# metastore-level CREATE CATALOG grant lets it create catalogs from the UI/CLI —
# without ever needing the container-bound bootstrap token.
u user create --name "Admin User" --email admin@dev-epireum.com 2>/dev/null || true
MID=$(u metastore get 2>/dev/null | awk -F'│' '/METASTORE_ID/{gsub(/ /,"",$3); print $3; exit}')
[ -n "$MID" ] && grant metastore "$MID" "CREATE CATALOG" admin@dev-epireum.com

echo "Done. Browse it: uc --server $SRV --auth_token \$(common/uc-cli/login.sh analyst) catalog list"
