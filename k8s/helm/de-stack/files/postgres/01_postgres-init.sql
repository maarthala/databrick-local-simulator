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

-- create hue user
CREATE USER hue WITH PASSWORD 'hue';
CREATE DATABASE hue OWNER hue;

-- create unity-catalog user (UC metadata store — replaces embedded H2)
CREATE USER ucuser WITH PASSWORD 'ucuser';
CREATE DATABASE ucdb OWNER ucuser;

-- Apache Polaris metastore (relational-jdbc persistence)
CREATE USER polaris WITH PASSWORD 'polaris';
CREATE DATABASE polarisdb OWNER polaris;

-- Optional: Connect to the new database and create schema
-- \connect airflow

-- Create a custom schema if needed
-- CREATE SCHEMA IF NOT EXISTS airflow_schema AUTHORIZATION airflow;
