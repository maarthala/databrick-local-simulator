#!/bin/sh

set -e  # Exit on any error

echo "Downloading files..."

# Move to a temporary directory
cd /tmp

# Define URL and target directory
SPARK_URL="https://downloads.apache.org/spark/spark-4.0.0/spark-4.0.0-bin-hadoop3.tgz"
SPARK_TGZ="spark-4.0.0-bin-hadoop3.tgz"
TARGET_DIR="/downloads"

# Clean up if file already exists
[ -f "$SPARK_TGZ" ] && rm -f "$SPARK_TGZ"

# Download the file with retry
wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -t 3 "$SPARK_URL" -O "$SPARK_TGZ"

# Ensure the target directory exists
mkdir -p "$TARGET_DIR"

# Extract and rename
tar -xzf "$SPARK_TGZ" -C "$TARGET_DIR"
mv "$TARGET_DIR/spark-4.0.0-bin-hadoop3" "$TARGET_DIR/spark"

# Clean up
rm -f "$SPARK_TGZ"

JARS_DIR="/downloads/spark/jars"

for URL in \
  "https://jdbc.postgresql.org/download/postgresql-42.6.0.jar" \
  "https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.24.6/bundle-2.24.6.jar" \
  "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.1/hadoop-aws-3.4.1.jar" \
  "https://repo1.maven.org/maven2/javax/activation/javax.activation-api/1.2.0/javax.activation-api-1.2.0.jar" \
  "https://repo1.maven.org/maven2/javax/xml/bind/jaxb-api/2.3.1/jaxb-api-2.3.1.jar" \
  "https://repo1.maven.org/maven2/com/sun/xml/bind/jaxb-impl/2.3.1/jaxb-impl-2.3.1.jar"
do
  FILENAME=$(basename "$URL")
  echo "Downloading $FILENAME..."
  wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -t 3 "$URL" -O "$JARS_DIR/$FILENAME"
done

echo "All JARs downloaded successfully."

# Optional: loosen permissions (commented out)
chmod 777 "$TARGET_DIR/spark/jars/"*.jar

echo "Download and extraction complete!"
