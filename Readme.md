# databrick-local-simulator
Running Notebook 



## LocalStack

aws --endpoint-url=http://localhost:4566 s3 ls

aws --endpoint-url=http://localhost:4566 s3 cp testfile.txt s3://my-test-bucket/

aws --endpoint-url=http://localhost:4566 s3 cp s3://my-test-bucket/testfile.txt downloaded.txt


Kafka

http://localhost:8081/

Superset
http://localhost:8088/superset/welcome/


Clickhouse
http://localhost:8123/?query=SELECT+1+FORMAT+JSON



## Docker Container Port Mapping Table

| Container Name   | Host Port(s)      | Container Port(s)   | Service / Notes        | Credentials (user/pass)    |
|------------------|-------------------|---------------------|------------------------|----------------------------|
| home(nginx)      | 8000              | 80                  | Home Url               | N/A                        |
| airflow          | 8001              | 8080                | Airflow API Server     | airflow / airflow          |
| spark-master     | 8002, 7077        | 8080, 7077          | Spark Master           | N/A                        |
| kafka-ui         | 8003              | 8080                | Kafka UI               | admin / admin              |
| superset         | 8004              | 8088                | Superset               | admin / admin              |
| tabix            | 8005              | 80                  | Tabix                  | N/A                        |
| clickhouse-ui    | 8006              | 8080                | Clickhouse UI          | default / default          |
| trino            | 8007              | 8080                | Trino                  | N/A                        |
| jupyter          | 8008              | 8888                | Jupyter                |                      |
| kafka            | 9092, 29092       | 9092, 29092         | Kafka                  | N/A                        |
| clickhouse       | 8123, 9000        | 8123, 9000          | Clickhouse             | default / default / default|
| localstack       | 4566              | 4566                | LocalStack             | N/A                        |
| postgres         | 5432              | 5432                | Postgres               | postgres / postgres        |
| redis            |                   | 6379                | Redis                  | N/A                        |


**Note:**  
- Host ports are shown as published on the host (e.g., `0.0.0.0:8088->8088/tcp` means host port 8088 maps to container port 8088).
- Some containers do not expose ports to the host.
- For containers with multiple ports, all mapped ports are listed.
- Use `docker ps` to see the current mappings.


### Localstack (AWS S3)


install aws cli and use localstack just like AWS S3


To Create a bucket
aws --endpoint-url=http://localhost:4566 s3 mb s3://test-folder

To List Bucket
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 s3 ls s3://test-folder/

You can also view navigate using UI localstack cloud ui. Navigate to https://app.localstack.cloud/ and create a account. Once login, you can find your local instance visible.

To query S3 data like Athena, we use Trino running at localhost:8007

Run queries using Trino
./trino --server localhost:8007 --catalog hive --schema default


CREATE SCHEMA hive.default;


### Superset
user: admin/admin

```
Connect Clickhouse using below config
host: clickhouse
port: 8123
username: default
password: default
db: default
```

clickhouse+native://default:default@clickhouse:9000/default

clickhouse+http://default:default@clickhouse:8123/default

pip install "SQLAlchemy>=1.4,<2" "clickhouse-sqlalchemy<0.2.0"

### Airflow

Default connection to spark cluster is created. 
```
spark://spark-master:7077
```

You can also create other connections using
docker exec -it airflow-apiserver airflow connections add 'spark_default_2' --conn-type 'spark' --conn-host 'spark://spark-master' --conn-port 7077


### Jupyter
Token: 123456




### Clickhouse

docker exec -it clickhouse clickhouse-client --user=default --password=default --database=default




### Localstack


Run Queries using Tabix

Visualized Clickhouse Metadata using 


## Spark
To run spark using CLI
````
spark-submit --master spark://spark-master:7077 /data/etl/extract.py
````




# For local development
docker compose \
    -f stack/base.yaml \
    -f stack/db.yaml \
    -f stack/localstack.yaml \
    -f stack/spark.yaml \
    -f stack/juypter.yaml \
up --build



parquet-tools show --endpoint-url=http://localhost:4566   s3://demo-bucket/northwind/orders.parquet





/opt/spark/bin/spark-submit /data/tmp/test1.py


/opt/spark/bin/spark-submit \
  --jars /opt/spark/jars/hadoop-aws-3.4.1.jar,/opt/spark/jars/bundle-2.24.6.jar \
  /data/tmp/test1.py

docker system prune -a --volumes



  ### Known Issues





