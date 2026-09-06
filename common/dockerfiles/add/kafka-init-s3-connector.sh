#!/bin/bash

# Step 1: Wait for Kafka broker
echo "Waiting for Kafka broker..."
while ! nc -z kafka 9092; do
  sleep 5
done
echo "Kafka broker is ready."

# Wait for Kafka Connect REST API to be ready
echo "Waiting for Kafka Connect..."
while ! curl -s http://localhost:8083/; do
  sleep 5
done

# sleep 30

# echo "Deploying S3 Sink Connector..."
# curl -X POST -H "Content-Type: application/json" --data '{
#   "name": "clickstream-s3-sink",
#   "config": {
#     "connector.class": "io.confluent.connect.s3.S3SinkConnector",
#     "tasks.max": "1",
#     "topics": "user_clickstream",
#     "s3.bucket.name": "clickstream-bucket",
#     "s3.region": "us-east-1",
#     "aws.region": "us-east-1",
#     "store.url": "http://minio:9000",
#     "s3.path.style.access": "true",
#     "s3.ssl.enabled": "false",
#     "aws.access.key.id": "minioadmin",
#     "aws.secret.access.key": "minioadmin",
#     "format.class": "io.confluent.connect.s3.format.json.JsonFormat",
#     "partitioner.class": "io.confluent.connect.storage.partitioner.DefaultPartitioner",
#     "flush.size": "10",
#     "storage.class": "io.confluent.connect.s3.storage.S3Storage",
#     "key.converter": "org.apache.kafka.connect.json.JsonConverter",
#     "key.converter.schemas.enable": "false",
#     "value.converter": "org.apache.kafka.connect.json.JsonConverter",
#     "value.converter.schemas.enable": "false"
#   }
# }' http://localhost:8083/connectors

# echo "Connector deployed!"
