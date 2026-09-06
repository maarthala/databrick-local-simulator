"""Generate fake Northwind order events and stream them to Kafka.

Reads existing customer IDs and the current max OrderID from Postgres, then
emits a new order (with nested order details) to the configured Kafka topic
every few seconds.
"""

import json
import logging
import os
import random
import time
from datetime import timedelta

from faker import Faker
from kafka import KafkaProducer
from sqlalchemy import create_engine, text
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("orders-generator")

# --- Configuration (env vars are set in stack/app.yaml) ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:29092")
TOPIC_NAME = os.getenv("TOPIC_NAME", "orders")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_URL = f"postgresql+psycopg2://postgres:postgres@{DB_HOST}/northwind"
SEND_INTERVAL_SECONDS = int(os.getenv("SEND_INTERVAL_SECONDS", "3"))

fake = Faker()
Faker.seed(42)


def connect_db(retries=30, delay=2):
    """Wait for Postgres to accept connections, then return an engine."""
    engine = create_engine(DB_URL)
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("Connected to Postgres at %s", DB_HOST)
            return engine
        except Exception as exc:  # noqa: BLE001 - retry on any connection error
            log.warning("Postgres not ready (%s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to Postgres at {DB_HOST} after {retries} tries")


def connect_kafka(retries=30, delay=2):
    """Wait for Kafka to be reachable, then return a producer."""
    for attempt in range(1, retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            log.info("Connected to Kafka at %s", KAFKA_BROKER)
            return producer
        except Exception as exc:  # noqa: BLE001 - retry on any broker/connection error
            log.warning("Kafka not ready (%s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to Kafka at {KAFKA_BROKER} after {retries} tries")


def generate_order_details(order_id, num_items=3):
    product_ids = list(range(1, 78))  # Northwind product IDs run 1..77
    order_details = []
    for _ in range(num_items):
        order_details.append({
            "OrderID": order_id,
            "ProductID": random.choice(product_ids),
            "UnitPrice": round(random.uniform(1.0, 100.0), 2),
            "Quantity": random.randint(1, 20),
            "Discount": random.choice([0, 0.05, 0.1, 0.15, 0.2]),
        })
    return order_details


def generate_order(order_id, customer_ids):
    order_date = fake.date_between(start_date="-30d", end_date="today")
    required_date = order_date + timedelta(days=random.randint(3, 10))
    shipped_date = order_date + timedelta(days=random.randint(1, 5))
    return {
        "OrderID": order_id,
        "CustomerID": random.choice(customer_ids),
        "EmployeeID": str(random.randint(1, 8)),
        "OrderDate": order_date.strftime("%Y-%m-%d"),
        "RequiredDate": required_date.strftime("%Y-%m-%d"),
        "ShippedDate": shipped_date.strftime("%Y-%m-%d"),
        "ShipVia": random.randint(1, 3),
        "Freight": round(random.uniform(10, 200), 2),
        "ShipName": fake.company(),
        "ShipAddress": fake.street_address(),
        "ShipCity": fake.city(),
        "ShipRegion": fake.state_abbr(),
        "ShipPostalCode": fake.postcode(),
        "ShipCountry": fake.country(),
        "OrderDetails": generate_order_details(order_id, num_items=random.randint(1, 5)),
    }


def main():
    engine = connect_db()
    with engine.connect() as conn:
        customer_ids = pd.read_sql(text('SELECT "CustomerID" FROM customers'), conn)["CustomerID"].tolist()
        max_order = pd.read_sql(text('SELECT MAX("OrderID") AS max_order_id FROM orders'), conn)
    order_id = int(max_order.loc[0, "max_order_id"])

    producer = connect_kafka()
    log.info("Streaming orders to topic '%s' every %ss", TOPIC_NAME, SEND_INTERVAL_SECONDS)
    while True:
        order_id += 1
        event = generate_order(order_id, customer_ids)
        producer.send(TOPIC_NAME, value=event)
        log.info("Sent OrderID %s", order_id)
        time.sleep(SEND_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
