from faker import Faker
from kafka import KafkaProducer
import json
import random
import time
from datetime import datetime, timedelta
import os

from sqlalchemy import create_engine, text
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import logging


bootstrap_servers=os.getenv("DB_HOST", "localhost:5432")

engine = create_engine(f"postgresql+psycopg2://postgres:postgres@{bootstrap_servers}/northwind")


product_ids = list(range(1, 78))


def update_specific_product_price():

    product_id = random.choice(product_ids)
    price = round(random.uniform(10, 200), 2)

    logging.info(f"\n--- Updating ProductID {product_id} to new price {price} ---")
    try:
        with engine.connect() as conn:
            # SQL UPDATE statement with parameter binding
            # :new_price and :product_id are placeholders for parameters
            update_sql = text("""
                UPDATE products
                SET "UnitPrice" = :new_price
                WHERE "ProductID" = :product_id;
            """)
            
            # Execute the update with parameters
            result = conn.execute(update_sql, {"new_price": price, "product_id": product_id})
            
            # Commit the transaction to save changes to the database
            conn.commit()
            logging.info(f"Successfully updated {result.rowcount} row(s) for ProductID {product_id}.")
    except Exception as e:
        logging.error(f"An error occurred during update: {e}")

while True:
    with engine.connect() as conn:
        update_specific_product_price()
        logging.info(f"Sent: Update")
        time.sleep(300)
