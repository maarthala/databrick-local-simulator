from superset.app import create_app
from superset import db

# --- Connection settings ---
connections = [
    {
        "database_name": "trino",
        "sqlalchemy_uri": "trino://trino@trino:8080/hive/default",
        "extra": "{}"
    },
    {
        "database_name": "clickhouse",
        "sqlalchemy_uri": "clickhouse+native://default:default@clickhouse:9000/default",
        "extra": "{}"
    }
]



app = create_app()
with app.app_context():
    from superset.models.core import Database 

    for conn in connections:
        existing = db.session.query(Database).filter_by(database_name=conn["database_name"]).first()
        if not existing:
            db.session.add(Database(
                database_name=conn["database_name"],
                sqlalchemy_uri=conn["sqlalchemy_uri"],
                extra=conn["extra"]
            ))
            print(f"Added database connection: {conn['database_name']}")
        else:
            print(f"Database connection already exists: {conn['database_name']}")

    db.session.commit()
    print("All done!")
