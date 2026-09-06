# 2.7 Semi-structured data (JSON)

## Concept
Not all data arrives as neat rows and columns. APIs, application logs, and — most importantly
for ShopFlow — the **event stream** (the clickstream from
[the schema page](../unit0/schema.md#the-event-stream-clickstream)) arrive as **JSON**: nested,
flexible, and schema-light. A huge part of data engineering is **parsing (flattening)** that
JSON into typed columns you can join and aggregate.

This is **schema-on-read** ([1.2](../unit1/lakehouse.md)) in action: the JSON has no fixed
shape until *you* impose one at query time. Trino's JSON functions do the work:

- **`json_extract_scalar(json, path)`** — pull one leaf value out as text.
- **`json_extract(json, path)`** — pull a sub-object/array (still JSON).
- **`CAST(… AS <type>)` / `TRY_CAST`** — turn the extracted text into a real number/date.
- Path syntax: `$.field`, nested `$.a.b`, array element `$.items[0].sku`.

## Lab
> Run these in the **Trino CLI** or **Superset SQL Lab** (see [2.1](intro.md)). The write
> steps use the `iceberg` catalog (fully qualified).

**Parse fields straight out of a JSON string:**

```sql
SELECT
  json_extract_scalar('{"event":"add_to_cart","product_id":42,"qty":3}', '$.event')      AS event_type,
  CAST(json_extract('{"event":"add_to_cart","product_id":42,"qty":3}', '$.qty') AS integer) AS qty;
```

**Model the ShopFlow event stream** — raw events land as JSON text; flatten them into columns:

```sql
CREATE SCHEMA IF NOT EXISTS iceberg.sandbox;

DROP TABLE IF EXISTS iceberg.sandbox.raw_events;
CREATE TABLE iceberg.sandbox.raw_events (event_id int, payload varchar);

INSERT INTO iceberg.sandbox.raw_events VALUES
  (1, '{"type":"page_view","customer_id":10,"product_id":42,"channel":"web"}'),
  (2, '{"type":"add_to_cart","customer_id":10,"product_id":42,"qty":2,"channel":"web"}'),
  (3, '{"type":"search","customer_id":null,"term":"keyboard","channel":"app"}');
```

**Flatten JSON → typed columns** (the raw → Bronze/Silver move for events):

```sql
SELECT event_id,
       json_extract_scalar(payload, '$.type')                        AS event_type,
       TRY_CAST(json_extract_scalar(payload, '$.customer_id') AS integer) AS customer_id,
       TRY_CAST(json_extract_scalar(payload, '$.product_id')  AS integer) AS product_id,
       TRY_CAST(json_extract_scalar(payload, '$.qty')         AS integer) AS qty,
       json_extract_scalar(payload, '$.channel')                     AS channel,
       json_extract_scalar(payload, '$.term')                        AS search_term
FROM iceberg.sandbox.raw_events
ORDER BY event_id;
```

Notice `search_term` is `NULL` for non-search events and `qty` is `NULL` where absent —
exactly the ragged shape semi-structured data produces, handled cleanly by `TRY_CAST`.

**Nested objects and arrays** — reach deeper with the path:

```sql
SELECT
  json_extract_scalar('{"items":[{"sku":"A"},{"sku":"B"}]}', '$.items[1].sku') AS second_sku,
  json_array_length('[1,2,3,4]')                                                AS n_items;
```

**Aggregate the flattened events** — e.g. events per type (a real analytics question over
the stream):

```sql
SELECT json_extract_scalar(payload, '$.type') AS event_type,
       count(*) AS events
FROM iceberg.sandbox.raw_events
GROUP BY json_extract_scalar(payload, '$.type')
ORDER BY events DESC;
```

!!! tip "Parse once, store typed"
    Extracting JSON on every query is slow and repetitive. In a real pipeline you **flatten
    once** — parse the raw JSON into a typed Silver table (`event_type`, `customer_id`, …) —
    then everyone queries clean columns. That's the [Medallion](../unit1/medallion.md) idea
    applied to the event stream.

## Challenge
From `iceberg.sandbox.raw_events`, produce one row per event with `event_id`, `event_type`,
`customer_id`, and a derived `is_anonymous` flag (`true` when `customer_id` is `NULL`). Then
count how many events are anonymous vs. known.

??? note "Solution"
    ```sql
    -- per-event, with the anonymous flag
    SELECT event_id,
           json_extract_scalar(payload, '$.type') AS event_type,
           TRY_CAST(json_extract_scalar(payload, '$.customer_id') AS integer) AS customer_id,
           json_extract_scalar(payload, '$.customer_id') IS NULL AS is_anonymous
    FROM iceberg.sandbox.raw_events
    ORDER BY event_id;

    -- the summary
    SELECT CASE WHEN json_extract_scalar(payload, '$.customer_id') IS NULL
                THEN 'anonymous' ELSE 'known' END AS who,
           count(*) AS events
    FROM iceberg.sandbox.raw_events
    GROUP BY 1
    ORDER BY events DESC;
    ```

!!! tip "🎯 The same idea on Azure, Databricks, Snowflake & Fabric"
    Every platform parses JSON — but the **function names differ** (this is the one place SQL
    isn't copy-paste portable), so learn the *concept* here and swap the syntax there:

    - **Azure Databricks** — the `payload:type` colon syntax, or `get_json_object` / `from_json`
      with a schema; explode arrays with `explode()`.
    - **Snowflake** — load JSON into a `VARIANT` column, navigate with `payload:type`, and
      expand arrays with `FLATTEN`.
    - **Microsoft Fabric** — `JSON_VALUE` / `OPENJSON` (T-SQL) in the Warehouse; `from_json`
      in a Spark Lakehouse.
    - **Azure Data Factory** — the **Flatten** transformation in a Mapping Data Flow.

    The *skill* — flatten semi-structured data into typed columns — is identical everywhere.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Semi-structured data** | Data with a flexible/nested shape (JSON, logs, events) |
| **Schema-on-read** | Impose structure at query time, not on ingest |
| **`json_extract_scalar`** | Pull one leaf value out of JSON as text |
| **`json_extract`** | Pull a sub-object/array (still JSON) |
| **JSON path** | `$.a.b`, `$.items[0].sku` — how you address a field |
| **Flatten** | Turn nested JSON into flat, typed columns |
| **`VARIANT`** | (Snowflake) a column type that stores JSON natively |

## You can now…
- Explain semi-structured data and schema-on-read
- Extract leaf values, nested fields, and array elements from JSON
- Flatten a JSON event payload into typed columns with `json_extract_scalar` + `TRY_CAST`
- Aggregate over parsed JSON, and name the equivalent functions on each cloud platform
