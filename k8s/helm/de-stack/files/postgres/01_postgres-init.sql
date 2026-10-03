-- init-airflow.sql

-- Create airflow user
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;

-- Create superset user
CREATE USER superset WITH PASSWORD 'superset';
CREATE DATABASE superset OWNER superset;

-- Apache Polaris metastore (relational-jdbc persistence)
CREATE USER polaris WITH PASSWORD 'polaris';
CREATE DATABASE polarisdb OWNER polaris;
-- Polaris 1.8+ no longer creates its schema: the admin tool/server select
-- currentSchema=POLARIS_SCHEMA and expect it to exist ("no schema has been selected
-- to create in" otherwise). Older Polaris created this same schema itself.
\connect polarisdb
CREATE SCHEMA IF NOT EXISTS polaris_schema AUTHORIZATION polaris;
\connect postgres

-- Keycloak (learner logins / registration — the home page's front door)
CREATE USER keycloak WITH PASSWORD 'keycloak';
CREATE DATABASE keycloak OWNER keycloak;

-- Optional: Connect to the new database and create schema
-- \connect airflow

-- Create a custom schema if needed
-- CREATE SCHEMA IF NOT EXISTS airflow_schema AUTHORIZATION airflow;
