#!/bin/bash
# Starts the Hive Metastore and HiveServer2 in one container (Hive 4.x).
# The service launch flags mirror the image's native entrypoint:
#   --skiphadoopversion  skips a Hadoop version probe that otherwise hangs HS2
#   --skiphbasecp        skips HBase classpath resolution (unused here)
# and Tez is placed on HADOOP_CLASSPATH, which HiveServer2 requires.
set -e

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_TYPE="${DB_TYPE:-postgres}"

wait_for() {  # host port label
  echo "Waiting for $3 at $1:$2 ..."
  until bash -c "echo > /dev/tcp/$1/$2" 2>/dev/null; do
    sleep 2
  done
  echo "$3 is up."
}

# Clear stale pid files so a container restart doesn't refuse to start with
# "HiveServer2 running as process 1. Stop it first."
export HIVE_PID_DIR="${HIVE_PID_DIR:-/tmp/hive-pids}"
mkdir -p "$HIVE_PID_DIR"
rm -f "$HIVE_PID_DIR"/*.pid /tmp/*.pid 2>/dev/null || true

wait_for "$DB_HOST" "$DB_PORT" "database"

# Initialise the schema on a fresh DB, or upgrade an older one (e.g. 3.1.0 -> 4.0.0).
echo "Initializing/upgrading Hive Metastore schema ($DB_TYPE) ..."
schematool -dbType "$DB_TYPE" -initOrUpgradeSchema \
  || echo "schematool reported an issue (continuing; schema may already be current)."

# Metastore thrift server in the background.
echo "Starting Hive Metastore ..."
hive --skiphadoopversion --skiphbasecp --service metastore &

wait_for "localhost" "9083" "metastore thrift"

# HiveServer2 in the foreground (needs Tez on the classpath).
echo "Starting HiveServer2 ..."
export HADOOP_CLASSPATH="$TEZ_HOME/*:$TEZ_HOME/lib/*:$HADOOP_CLASSPATH"
exec hive --skiphadoopversion --skiphbasecp --service hiveserver2
