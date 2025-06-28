CREATE DATABASE IF NOT EXISTS default;

CREATE TABLE IF NOT EXISTS default.dummy_table (
    id UInt64,
    name String,
    created_at DateTime
) ENGINE = MergeTree()
ORDER BY id;
