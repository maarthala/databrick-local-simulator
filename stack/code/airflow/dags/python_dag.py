import json
import pendulum 


from airflow.decorators import dag, task

@dag(
    dag_id='sample_python_operator_dag',
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=['example'],
)
def tutorial_taskflow_api():

    @task()
    def extract():
        return {'key1': 1, 'key2': 2}
    
    @task(multiple_outputs=True)
    def transform(data: dict):
        return {"total_order_value": 100}
    
    @task()
    def load(data: int):
        print(f"Data loaded: {data}")

    value = extract()
    transformed_value = transform(value)
    load(transformed_value)

tutorial_taskflow_api()