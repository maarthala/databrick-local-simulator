import random
import json
import time
from faker import Faker
from datetime import datetime, timedelta
from kafka import KafkaProducer
import os

fake = Faker()

# --- Configuration ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_NAME = os.getenv("TOPIC", "user_clickstream")

NUM_USERS = 10
NUM_PRODUCTS = 77
SESSION_COUNT = 10

# --- Action Flows ---
SESSION_FLOWS = [
    ["view", "click", "add_to_cart", "purchase"],
    ["view", "click", "add_to_cart", "remove_from_cart"],
    ["view", "click", "wishlist"],
    ["view", "click", "rate", "review"],
    ["view", "click"],
    ["view"],
]

# --- Kafka Producer ---
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def generate_session_events(user_id):
    session_id = fake.uuid4()
    product_id = random.randint(1, NUM_PRODUCTS)
    flow = random.choice(SESSION_FLOWS)
    
    timestamp = datetime.utcnow()
    events = []

    for action in flow:
        event = {
            "timestamp": timestamp.isoformat(),
            "user_id": user_id,
            "session_id": str(session_id),
            "product_id": product_id,
            "action": action,
            "referrer": fake.uri_path(),
            "user_agent": fake.user_agent()
        }
        events.append(event)
        timestamp += timedelta(seconds=random.randint(1, 30))

    return events

def stream_sessions_to_kafka_forever(delay=0.2):
    while True:
        user_id = random.randint(1, NUM_USERS)
        events = generate_session_events(user_id)
        for event in events:
            producer.send(TOPIC_NAME, value=event)
            print(f"Sent: {event}")
            time.sleep(delay)
        producer.flush()

if __name__ == "__main__":
    stream_sessions_to_kafka_forever(delay=0.2)
