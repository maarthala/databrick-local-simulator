#!/bin/bash
# Create + load the AdventureWorks (OLTP) sample database.
#
# The data (fixed CSVs + install.sql) is staged into ./adventureworks by
# `make init` and mounted here at /docker-entrypoint-initdb.d/adventureworks.
# Runs once, on first Postgres init. Skips gracefully if the data isn't staged
# (e.g. `make init` wasn't run, or ruby was missing) so the stack still starts.
set -e

AW="/docker-entrypoint-initdb.d/adventureworks"

if [ ! -f "$AW/install.sql" ]; then
  echo "AdventureWorks data not staged at $AW — run 'make init' before 'make up' to enable it. Skipping."
  exit 0
fi

echo "Creating + loading the 'adventureworks' database ..."
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -c 'CREATE DATABASE adventureworks;'

# install.sql uses \copy FROM './*.csv' (relative), so run psql from the data dir.
cd "$AW"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d adventureworks -f install.sql >/dev/null

echo "✅ AdventureWorks loaded (68 tables across person/sales/production/purchasing/humanresources)."
