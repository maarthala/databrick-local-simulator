
# Kafka Sink Connectors
To make this connector work, you need schema & tables

## Quick setup (automated)

The ClickHouse table creation and both connector registrations are scripted.
After the stack is up, run:

```sh
bash stack/init_scripts/setup-connectors.sh   # or: make connectors
```

It waits for Kafka Connect + ClickHouse, creates `default.user_clickstream`,
and registers both sink connectors (safe to re-run). The manual steps below are
kept for reference / troubleshooting.

## Setup schema & tables


### kafka-clickhouse-sink
To make this connector work, you need a table in clickhouse. using Hue query, go to Clickhouse and create table as below

```
CREATE TABLE default.user_clickstream
(
    timestamp DateTime64(6),
    user_id UInt32,
    session_id String,
    product_id UInt32,
    action String,
    referrer String,
    user_agent String
) ENGINE = MergeTree()
ORDER BY timestamp;

```

### create kafka-clickhouse connector

```
curl -X POST -H "Content-Type: application/json" \
     --data @stack/code/trino/kafka-clickhouse-sink.json \
     http://localhost:8083/connectors
```

### kafka-s3-sink

configure connector to the kafka

```
curl -X POST -H "Content-Type: application/json" \
     --data @stack/code/trino/kafka-s3-sink.json \
     http://localhost:8083/connectors

```

connector push the data from kafka to s3 bucket `s3://clickstream-bucket/topics/user_clickstream/partition=0/`

```
aws --endpoint-url=http://localhost:9002 s3 ls s3://clickstream-bucket/topics/user_clickstream/partition=0/
```

To query data  created by kafka connector in s3 using Trino, first we need to create schema and tables in clickhouse

using Hue query, go to Trino and create schema under Trino and table as below

```
# create schema

CREATE SCHEMA hive.clickstream WITH (location = 's3a://demo-bucket/clicks/');

# create table

CREATE TABLE hive.clickstream.user_clicks (
    referrer VARCHAR,
    user_id INTEGER,
    product_id INTEGER,
    session_id VARCHAR,
    action VARCHAR,
    user_agent VARCHAR,
    timestamp VARCHAR,
    partition INTEGER
)
WITH (
    format = 'JSON',
    partitioned_by = ARRAY['partition'],
    external_location = 's3a://clickstream-bucket/topics/user_clickstream/'
);

# sync partition info
CALL system.sync_partition_metadata('clickstream', 'user_clicks', 'ADD');


# to find number of particians
SELECT * FROM hive.clickstream."user_clicks$partitions";

# Select table from partition = 0

SELECT * FROM hive.clickstream.user_clicks WHERE partition = 0;

# Query all data in the partician

SELECT * FROM hive.clickstream.user_clicks;

```


## To list the number of connectors configured

```
curl http://localhost:8083/connectors

# output
["clickstream-s3-sink","clickhouse-sink"]
```

### To Delete Sink connector

```
curl -X DELETE http://localhost:8083/connectors/<connector-name>
# Example 
curl -X DELETE http://localhost:8083/connectors/clickhouse-sink
```

### To View Connector status

```
curl http://localhost:8083/connectors/{connector-name}/status

curl http://localhost:8083/connectors/clickhouse-sink/status
```

### To View Config

```
curl http://localhost:8083/connectors/{connector-name}/config
```
