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
  "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-4.0_2.13/1.11.0/iceberg-spark-runtime-4.0_2.13-1.11.0.jar"
  "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.11.0/iceberg-aws-bundle-1.11.0.jar"
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
