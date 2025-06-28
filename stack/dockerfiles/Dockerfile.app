FROM python:3.11-slim
WORKDIR /app
RUN pip install kafka-python faker pandas sqlalchemy psycopg2-binary pyarrow
CMD ["sh", "-c", "while true; do sleep 3600; done"]