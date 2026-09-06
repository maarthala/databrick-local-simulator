"""Randomly update product prices in Postgres to simulate catalog changes.

Every few minutes this picks a random product and sets a new UnitPrice. It is
the source of the "product price change" business event used by the challenges.
"""

import logging
import os
import random
import time

from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("product-price-generator")

# --- Configuration (env vars are set in stack/app.yaml) ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_URL = f"postgresql+psycopg2://postgres:postgres@{DB_HOST}/northwind"
UPDATE_INTERVAL_SECONDS = int(os.getenv("UPDATE_INTERVAL_SECONDS", "300"))

PRODUCT_IDS = list(range(1, 78))  # Northwind product IDs run 1..77


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


def update_random_product_price(engine):
    product_id = random.choice(PRODUCT_IDS)
    new_price = round(random.uniform(10, 200), 2)
    update_sql = text(
        'UPDATE products SET "UnitPrice" = :new_price WHERE "ProductID" = :product_id'
    )
    with engine.connect() as conn:
        result = conn.execute(update_sql, {"new_price": new_price, "product_id": product_id})
        conn.commit()
    log.info("Updated ProductID %s -> UnitPrice %s (%s row(s))",
             product_id, new_price, result.rowcount)


def main():
    engine = connect_db()
    log.info("Updating a random product price every %ss", UPDATE_INTERVAL_SECONDS)
    while True:
        try:
            update_random_product_price(engine)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive on transient errors
            log.error("Price update failed: %s", exc)
        time.sleep(UPDATE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
