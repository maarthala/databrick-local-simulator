from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime


with DAG(
    dag_id='run_jupyter_with_papermill', 
    start_date=datetime(2023, 1, 1), 
    schedule=None,
    catchup=False
    ) as dag:
    run_notebook = BashOperator(
        task_id='run_notebook',
        bash_command='papermill /code/notebook/spark-hive-schema-test.ipynb /code/notebook/output.ipynb'
    )
