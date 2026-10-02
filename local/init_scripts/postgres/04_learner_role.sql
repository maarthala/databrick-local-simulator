-- The learners' PostgreSQL login: learner / learner — the course databases only.
--   * reads every table in shopflow and adventureworks (the shared OLTP sources)
--   * creates (and owns) its own tables in shopflow.public (Unit 3 write-back, reverse ETL)
--   * can't change the shared tables, can't open the platform databases (Polaris, Keycloak,
--     Airflow, Superset …) — the superuser `postgres` is for the platform only.
-- Idempotent: also run against an existing stack (psql -U postgres -f …).

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'learner') THEN
    CREATE ROLE learner LOGIN PASSWORD 'learner' NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

-- platform databases: only their own service user (the owner) may connect
DO $$ DECLARE d text; BEGIN
  FOR d IN SELECT datname FROM pg_database
           WHERE NOT datistemplate AND datname NOT IN ('shopflow', 'adventureworks') LOOP
    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', d);
  END LOOP;
END $$;
GRANT CONNECT ON DATABASE shopflow TO learner;

\connect shopflow
DO $$ DECLARE s text; BEGIN
  FOR s IN SELECT nspname FROM pg_namespace
           WHERE nspname NOT LIKE 'pg\_%' AND nspname <> 'information_schema' LOOP
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO learner', s);
    EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO learner', s);
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA %I GRANT SELECT ON TABLES TO learner', s);
  END LOOP;
END $$;
GRANT CREATE ON SCHEMA public TO learner;

-- adventureworks may not exist yet (k8s loads it later — its loader runs this part again)
SELECT 'adventureworks' AS db WHERE EXISTS (SELECT FROM pg_database WHERE datname = 'adventureworks') \gset
\if :{?db}
GRANT CONNECT ON DATABASE adventureworks TO learner;
\connect adventureworks
DO $$ DECLARE s text; BEGIN
  FOR s IN SELECT nspname FROM pg_namespace
           WHERE nspname NOT LIKE 'pg\_%' AND nspname <> 'information_schema' LOOP
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO learner', s);
    EXECUTE format('GRANT SELECT ON ALL TABLES IN SCHEMA %I TO learner', s);
    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA %I GRANT SELECT ON TABLES TO learner', s);
  END LOOP;
END $$;
\endif
