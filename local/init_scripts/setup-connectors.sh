#!/usr/bin/env bash
#
# Set up the Kafka Connect sink connectors used by the streaming challenges.
#
#   1. Waits for Kafka Connect (http://localhost:8083) to be ready.
#   2. Creates the ClickHouse `user_clickstream` table (idempotent).
#   3. Registers the Kafka -> ClickHouse and Kafka -> S3 sink connectors.
#
# Safe to run more than once: existing connectors are left in place.
# Run after the stack is up:  make connectors   (or: bash stack/init_scripts/setup-connectors.sh)

set -euo pipefail

CONNECT_URL="${CONNECT_URL:-http://localhost:8083}"
CLICKHOUSE_URL="${CLICKHOUSE_URL:-http://localhost:8123}"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-default}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-default}"

# Resolve connector configs relative to this script so it works from any CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRINO_DIR="$SCRIPT_DIR/../code/trino"

wait_for() {
  local name="$1" url="$2" tries="${3:-60}"
  echo "⏳ Waiting for $name ($url) ..."
  for ((i = 1; i <= tries; i++)); do
    if curl -sf -o /dev/null "$url"; then
      echo "✅ $name is ready"
      return 0
    fi
    sleep 3
  done
  echo "❌ $name did not become ready after $((tries * 3))s" >&2
  return 1
}

create_clickhouse_table() {
  echo "🧱 Creating ClickHouse table default.user_clickstream (if not exists) ..."
  curl -sf "$CLICKHOUSE_URL/?user=$CLICKHOUSE_USER&password=$CLICKHOUSE_PASSWORD" \
    --data-binary @- <<'SQL'
CREATE TABLE IF NOT EXISTS default.user_clickstream
(
    timestamp   DateTime64(6),
    user_id     UInt32,
    session_id  String,
    product_id  UInt32,
    action      String,
    referrer    String,
    user_agent  String
) ENGINE = MergeTree()
ORDER BY timestamp;
SQL
  echo "✅ ClickHouse table ready"
}

register_connector() {
  local config_file="$1"
  local name
  name="$(grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' "$config_file" | head -1 | sed 's/.*"\([^"]*\)"$/\1/')"

  if curl -sf -o /dev/null "$CONNECT_URL/connectors/$name"; then
    echo "ℹ️  Connector '$name' already exists — skipping"
    return 0
  fi

  echo "🔌 Registering connector '$name' from $(basename "$config_file") ..."
  curl -sf -X POST -H "Content-Type: application/json" \
    --data @"$config_file" "$CONNECT_URL/connectors" >/dev/null
  echo "✅ Connector '$name' registered"
}

main() {
  wait_for "Kafka Connect" "$CONNECT_URL/connectors"
  wait_for "ClickHouse" "$CLICKHOUSE_URL/ping"
  create_clickhouse_table
  register_connector "$TRINO_DIR/kafka-clickhouse-sink.json"
  register_connector "$TRINO_DIR/kafka-s3-sink.json"

  echo
  echo "🎉 Done. Configured connectors:"
  curl -s "$CONNECT_URL/connectors"
  echo
}

main "$@"
