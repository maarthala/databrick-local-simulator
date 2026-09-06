# Northwind Data Engineering Challenges

Welcome to the Northwind Data Engineering Simulation! As a Data Engineer at Northwind Corp, your mission is to build, orchestrate, and analyze real-time and batch data pipelines using the provided infrastructure. Each challenge below reflects a real-world business requirement. Use the dashboard tools and sample data to complete each task.

---

## Challenge 1: Real-Time Order Ingestion
**Requirement:**
- Capture new orders generated every second from the Kafka topic and store them in a ClickHouse table (`orders_stream`).
- Ensure the pipeline is robust and can recover from failures.
- Validate that the ClickHouse table is continuously updated with new orders.

## Challenge 2: Product Price Change Tracking
**Requirement:**
- Track all product price changes (randomly updated every 5 minutes) in a separate table (`product_price_history`).
- Build a pipeline to detect and log every price change event, including timestamp, product ID, old price, and new price.
- Visualize price change trends in Superset.

## Challenge 3: Historical Order Analytics
**Requirement:**
- Load historical orders and order details from S3 into ClickHouse or Trino (using the provided Parquet files).
- Create a dashboard in Superset showing total sales, top products, and sales by country.
- Document your ETL process in a Jupyter notebook.

## Challenge 4: Real-Time Sales Dashboard
**Requirement:**
- Build a real-time dashboard in Superset that displays:
  - Number of orders per minute (last 30 minutes)
  - Top 5 selling products (real-time)
  - Average order value (real-time)
- Use streaming data from Kafka and/or ClickHouse as your data source.

## Challenge 5: Data Quality & Monitoring
**Requirement:**
- Implement a data quality check in Airflow to ensure no duplicate orders are ingested and all required fields are present.
- Set up an alert (e.g., email or log) if data quality checks fail.
- Document your approach and results in a Jupyter notebook.

## Challenge 6: Clickstream Analytics from User Flow Events
**Requirement:**
- Ingest user-flow-click events from the Kafka topic into a ClickHouse table (`user_clickstream`).
- Build a pipeline to process and store clickstream data, capturing fields such as user ID, timestamp, page, and action.
- Analyze user navigation patterns: most visited pages, average session length, and common user journeys.
- Create a Superset dashboard to visualize clickstream metrics and trends.
- Document your ETL and analysis process in a Jupyter notebook.

---

**Tips:**
- Use Airflow for orchestration, Spark for ETL, and Superset for analytics.
- All required data and services are available via the dashboard.
- Refer to the README and dashboard documentation for connection details and sample queries.

Good luck, Data Engineer! Your work will help Northwind make smarter, data-driven decisions.
