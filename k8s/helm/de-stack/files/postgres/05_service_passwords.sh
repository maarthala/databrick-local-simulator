#!/usr/bin/env bash
# Team stack: the service users get the passwords from the de-stack-secrets Secret (passed in
# as env), not the well-known defaults 01_postgres-init.sql created them with. Users of
# services this stack no longer runs can't log in at all. Runs once, on a fresh database.
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres \
  -v pa="$PG_AIRFLOW_PASSWORD" -v pp="$PG_POLARIS_PASSWORD" \
  -v pk="$PG_KEYCLOAK_PASSWORD" -v ps="$PG_SUPERSET_PASSWORD" <<'SQL'
ALTER USER airflow  PASSWORD :'pa';
ALTER USER polaris  PASSWORD :'pp';
ALTER USER keycloak PASSWORD :'pk';
ALTER USER superset PASSWORD :'ps';
ALTER USER hive NOLOGIN;
ALTER USER hue NOLOGIN;
ALTER USER ucuser NOLOGIN;
SQL
