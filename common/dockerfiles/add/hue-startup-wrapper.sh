#!/bin/sh
set -e

echo "Waiting for Postgres at $POSTGRES_HOST:$POSTGRES_PORT..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
  sleep 2
done

echo "Postgres is ready! Running Hue migrations..."
./build/env/bin/hue migrate   # will exit container if migration fails

echo "Starting Hue server..."
exec ./build/env/bin/supervisor
