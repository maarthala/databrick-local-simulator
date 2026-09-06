"""Generate fake user clickstream sessions and stream them to Kafka.

Each session is a short sequence of actions (view -> click -> add_to_cart ...)
for a random user/product, emitted event-by-event to the configured topic.
"""

import json
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone

from faker import Faker
from kafka import KafkaProducer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("user-click-sessions")

# --- Configuration (env vars are set in stack/app.yaml) ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:29092")
TOPIC_NAME = os.getenv("TOPIC_NAME", "user_clickstream")
SEND_DELAY_SECONDS = float(os.getenv("SEND_DELAY_SECONDS", "0.2"))

NUM_USERS = 10
NUM_PRODUCTS = 77

# --- Action flows a session can take ---
SESSION_FLOWS = [
    ["view", "click", "add_to_cart", "purchase"],
    ["view", "click", "add_to_cart", "remove_from_cart"],
    ["view", "click", "wishlist"],
    ["view", "click", "rate", "review"],
    ["view", "click"],
    ["view"],
]

fake = Faker()


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


def generate_session_events(user_id):
    session_id = str(fake.uuid4())
    product_id = random.randint(1, NUM_PRODUCTS)
    flow = random.choice(SESSION_FLOWS)
    timestamp = datetime.now(timezone.utc)

    events = []
    for action in flow:
        events.append({
            "timestamp": timestamp.isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "product_id": product_id,
            "action": action,
            "referrer": fake.uri_path(),
            "user_agent": fake.user_agent(),
        })
        timestamp += timedelta(seconds=random.randint(1, 30))
    return events


def main():
    producer = connect_kafka()
    log.info("Streaming clickstream to topic '%s'", TOPIC_NAME)
    while True:
        user_id = random.randint(1, NUM_USERS)
        for event in generate_session_events(user_id):
            producer.send(TOPIC_NAME, value=event)
            log.info("Sent user %s action '%s'", event["user_id"], event["action"])
            time.sleep(SEND_DELAY_SECONDS)
        producer.flush()


if __name__ == "__main__":
    main()
