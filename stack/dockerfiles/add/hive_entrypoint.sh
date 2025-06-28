#!/bin/bash

# Wait for database to be ready
echo "Waiting for DB at $DB_HOST:$DB_PORT..."
until nc -z $DB_HOST $DB_PORT; do
  sleep 2
done

# Initialize schema (idempotent)
echo "Initializing Hive Metastore schema (safe to fail if already exists)..."
schematool -initSchema -dbType $DB_TYPE || echo "Schema already exists."

# Start Hive Metastore service
echo "Starting Hive Metastore..."
exec hive --service metastore
