#!/bin/bash
set -e

# Target download directory
TARGET_DIR="../common/dockerfiles/tmp"
mkdir -p "$TARGET_DIR"

# List of files (deduplicated)
URLS=(
  "https://jdbc.postgresql.org/download/postgresql-42.6.0.jar"
  "https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.24.6/bundle-2.24.6.jar"
  "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.1/hadoop-aws-3.4.1.jar"
  "https://repo1.maven.org/maven2/javax/activation/javax.activation-api/1.2.0/javax.activation-api-1.2.0.jar"
  "https://repo1.maven.org/maven2/javax/xml/bind/jaxb-api/2.3.1/jaxb-api-2.3.1.jar"
  "https://repo1.maven.org/maven2/com/sun/xml/bind/jaxb-impl/2.3.1/jaxb-impl-2.3.1.jar"
  "https://archive.apache.org/dist/spark/spark-4.0.0/spark-4.0.0-bin-hadoop3.tgz"
  "https://repo1.maven.org/maven2/org/apache/hive/hcatalog/hive-hcatalog-core/3.1.2/hive-hcatalog-core-3.1.2.jar"
  "https://repo1.maven.org/maven2/org/apache/hive/hive-exec/3.1.3/hive-exec-3.1.3.jar"
  # Iceberg runtime MUST match the Spark above (4.0.0). Iceberg 1.10.0 is the last
  # release built for Spark 4.0.0; 1.11.0+ target Spark 4.1 and reference a class
  # (SupportsV1OverwriteWithSaveAsTable) missing from 4.0.0 -> NoClassDefFoundError on
  # DataFrame writes. If you bump this, bump Spark to the matching 4.0.x/4.1 too.
  "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-4.0_2.13/1.10.0/iceberg-spark-runtime-4.0_2.13-1.10.0.jar"
  "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.0/iceberg-aws-bundle-1.10.0.jar"
)


echo "Downloading files to $TARGET_DIR ..."

for url in "${URLS[@]}"; do
  filename=$(basename "$url")
  filepath="$TARGET_DIR/$filename"

  if [ -f "$filepath" ]; then
    echo "✅ $filename already exists, skipping."
  else
    echo "⬇️  Downloading $filename ..."
    curl --max-time 300 -L --progress-bar -o "$filepath" "$url"
  fi
done

echo "🎉 All downloads complete. Files saved in $TARGET_DIR"

# ---------------------------------------------------------------------------
# AdventureWorks (OLTP) sample database for the local Postgres.
# Downloads the Microsoft OLTP CSVs + the lorint Postgres port, fixes the CSVs
# for Postgres (needs `ruby` — ships with macOS), and stages them where the
# Postgres init script (03_adventureworks.sh) loads them into the
# `adventureworks` database on first `make up`. Staged data is gitignored
# (~110 MB). Skips if already prepared.
# ---------------------------------------------------------------------------
AW_DIR="init_scripts/postgres/adventureworks"
if [ -f "$AW_DIR/install.sql" ] && ls "$AW_DIR"/*.csv >/dev/null 2>&1; then
  echo "✅ AdventureWorks sample already prepared in $AW_DIR, skipping."
elif ! command -v ruby >/dev/null 2>&1; then
  echo "⚠️  ruby not found — skipping AdventureWorks prep (it fixes the CSVs)."
  echo "    Install ruby and re-run 'make init' to enable the adventureworks DB."
else
  echo "⬇️  Preparing AdventureWorks (Postgres) sample database ..."
  mkdir -p "$AW_DIR"
  tmp="$(mktemp -d)"
  curl --max-time 300 -L --progress-bar -o "$tmp/data.zip" \
    "https://github.com/microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorks-oltp-install-script.zip"
  curl --max-time 120 -L --progress-bar -o "$tmp/script.zip" \
    "https://github.com/lorint/AdventureWorks-for-Postgres/archive/master.zip"
  unzip -oq "$tmp/data.zip"  -d "$AW_DIR"        # OLTP CSVs land directly in AW_DIR
  unzip -oq "$tmp/script.zip" -d "$tmp/script"
  cp "$tmp"/script/AdventureWorks-for-Postgres-master/install.sql     "$AW_DIR"/
  cp "$tmp"/script/AdventureWorks-for-Postgres-master/update_csvs.rb  "$AW_DIR"/
  ( cd "$AW_DIR" && ruby update_csvs.rb >/dev/null )   # fix CSVs for Postgres COPY
  rm -f "$AW_DIR/update_csvs.rb"; rm -rf "$tmp"
  echo "🎉 AdventureWorks prepared in $AW_DIR ($(ls "$AW_DIR"/*.csv | wc -l | tr -d ' ') CSVs)."
fi
