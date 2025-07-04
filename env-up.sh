docker compose \
    -f stack/base.yaml \
    -f stack/db.yaml  \
    -f stack/superset.yaml  \
    -f stack/kafka.yaml  \
    -f stack/clickhouse.yaml  \
    -f stack/spark.yaml  \
    -f stack/airflow.yaml  \
    -f stack/jupyter.yaml  \
    -f stack/localstack.yaml  \
    -f stack/app.yaml \
    -f stack/hue.yaml \
    -f stack/home.yaml \
up -d