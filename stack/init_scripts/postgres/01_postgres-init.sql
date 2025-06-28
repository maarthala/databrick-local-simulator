-- init-airflow.sql

-- Create airflow user
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;

-- Create superset user
CREATE USER superset WITH PASSWORD 'superset';
CREATE DATABASE superset OWNER superset;

-- create hive user
CREATE USER hive WITH PASSWORD 'hive';
CREATE DATABASE metastore OWNER hive;


-- Optional: Connect to the new database and create schema
-- \connect airflow

-- Create a custom schema if needed
-- CREATE SCHEMA IF NOT EXISTS airflow_schema AUTHORIZATION airflow;
