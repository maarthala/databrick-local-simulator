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

bootstrap_servers=os.getenv("DB_HOST", "localhost:5432")

engine = create_engine(f"postgresql+psycopg2://postgres:postgres@{bootstrap_servers}/northwind")

fake = Faker()
Faker.seed(42)

with engine.connect() as conn:
    df = pd.read_sql(text('SELECT "CustomerID" FROM customers'), conn)
    df2 = pd.read_sql(text('SELECT MAX("OrderID") AS max_order_id FROM orders'), conn)

start_order_id = int(df2.loc[0, 'max_order_id'])

customer_ids = df["CustomerID"].tolist()
employee_ids = [f"{i}" for i in range(1, 9)]
product_ids = [f"{i}" for i in range(1, 77)]

def generate_order(order_id):
    customer_id = random.choice(customer_ids)
    employee_id = random.choice(employee_ids)
    
    order_date = fake.date_between(start_date='-30d', end_date='today')
    required_date = order_date + timedelta(days=random.randint(3, 10))
    shipped_date = order_date + timedelta(days=random.randint(1, 5))

    ship_via = random.randint(1, 3)
    freight = round(random.uniform(10, 200), 2)

    ship_name = fake.company()
    ship_address = fake.street_address()
    ship_city = fake.city()
    ship_region = fake.state_abbr()
    ship_postal_code = fake.postcode()
    ship_country = fake.country()

    return({
        "OrderID": order_id,
        "CustomerID": customer_id,
        "EmployeeID": employee_id,
        "OrderDate": order_date.strftime("%Y-%m-%d"),
        "RequiredDate": required_date.strftime("%Y-%m-%d"),
        "ShippedDate": shipped_date.strftime("%Y-%m-%d"),
        "ShipVia": ship_via,
        "Freight": freight,
        "ShipName": ship_name,
        "ShipAddress": ship_address,
        "ShipCity": ship_city,
        "ShipRegion": ship_region,
        "ShipPostalCode": ship_postal_code,
        "ShipCountry": ship_country,
        "OrderDetails": generate_order_details(order_id, num_items=random.randint(1, 5))
    })


def generate_order_details(order_id, num_items=3):
    # Let's assume product IDs range from 1 to 77 in Northwind
    product_ids = list(range(1, 78))
    
    order_details = []
    for _ in range(num_items):
        product_id = random.choice(product_ids)
        unit_price = round(random.uniform(1.0, 100.0), 2)  # price between 1 and 100
        quantity = random.randint(1, 20)                    # quantity between 1 and 20
        discount = random.choice([0, 0.05, 0.1, 0.15, 0.2]) # possible discounts
        
        detail = {
            "OrderID": order_id,
            "ProductID": product_id,
            "UnitPrice": unit_price,
            "Quantity": quantity,
            "Discount": discount
        }
        order_details.append(detail)
    
    return order_details


producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BROKER", "localhost:29092"),
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# # Send events in a loop
while True:
    start_order_id += 1
    event = generate_order(start_order_id)
    producer.send("orders", value=event)
    print(f"Sent: {event}")
    time.sleep(3)

