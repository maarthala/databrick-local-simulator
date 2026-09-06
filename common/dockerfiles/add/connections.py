"""Seed Superset's database connections for the training course.

Runs at container startup. Idempotent: it UPSERTS the wanted connections (so a fixed URI
takes effect on restart) and REMOVES stale/broken ones.

Two Trino connections, one engine, two data tiers:
  - "shopflow"          -> the raw OLTP source        (Unit 2 SQL Lab)
  - "ShopFlow Lakehouse"-> the governed Gold lakehouse (Unit 7 dashboards)
"""
from superset.app import create_app
from superset import db

WANT = [
    {"database_name": "shopflow",
     "sqlalchemy_uri": "trino://trino@trino:8080/shopflow/public"},
    {"database_name": "ShopFlow Lakehouse",
     "sqlalchemy_uri": "trino://trino@trino:8080/iceberg"},
]
# old defaults that are wrong/broken on this stack (dead hive catalog, disabled clickhouse)
REMOVE = ["trino", "clickhouse"]

app = create_app()
with app.app_context():
    from superset.models.core import Database

    for name in REMOVE:
        obj = db.session.query(Database).filter_by(database_name=name).first()
        if obj:
            db.session.delete(obj)
            print(f"removed stale connection: {name}")

    for c in WANT:
        obj = db.session.query(Database).filter_by(database_name=c["database_name"]).first()
        if obj:
            obj.sqlalchemy_uri = c["sqlalchemy_uri"]          # keep the URI current
            print(f"updated connection: {c['database_name']}")
        else:
            db.session.add(Database(database_name=c["database_name"],
                                    sqlalchemy_uri=c["sqlalchemy_uri"], extra="{}"))
            print(f"added connection: {c['database_name']}")

    db.session.commit()
    print("Superset connections seeded.")
