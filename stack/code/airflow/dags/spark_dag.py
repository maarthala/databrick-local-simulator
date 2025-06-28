from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    dag_id='spark_dag',
    default_args=default_args,
    description='Test Spark DAG with Airflow',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['test'],
) as dag:
    
    start = EmptyOperator(task_id="start")

    extract = SparkSubmitOperator(
        task_id="extract_sales_data",
        application="/code/shared/etl/extract.py",
        name="SampleSparkJob",
        verbose=True
    )


    end = EmptyOperator(task_id="end")

    start >> extract >> end


