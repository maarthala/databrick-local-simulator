from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta


# Default arguments
default_args = {
    'owner': 'data-engineer',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}
#  schedule="*/5 * * * *",
# Create DAG
with DAG(
    dag_id='sales_data_pipeline',
    default_args=default_args,
    description='Prepare financial sales data and upload to customer shared folder in aws s3',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['sales','etl','spark'],
) as dag:

    # Extract task
    start = EmptyOperator(task_id="start")


    extract_task = SparkSubmitOperator(
            task_id="extract_sales_data",
            application="/code/shared/etl/sales_data_pipeline/01_extract.py",
            name="ExtractSparkJob",
            verbose=True
        )


    transform_task = SparkSubmitOperator(
            task_id="transform_sales_data",
            application="/code/shared/etl/sales_data_pipeline/02_transform.py",
            name="TransformSalesData",
            verbose=True
        )


    load_task = SparkSubmitOperator(
            task_id="load_sales_data",
            application="/code/shared/etl/sales_data_pipeline/03_load_finance.py",
            name="loadSalesData",
            verbose=True
        )


    end = EmptyOperator(task_id="end")

    # Set task dependencies
    start >> extract_task >> transform_task >> load_task  >> end
