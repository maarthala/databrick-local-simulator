"""Superset configuration for the DE training stack.

Loaded automatically because it sits on PYTHONPATH (/app/pythonpath) in the official image.

The key fix: store Superset's OWN metadata (dashboards, charts, saved queries, connections)
in **Postgres**, not the default in-container SQLite — so nothing is lost on a container
restart/rebuild. (The `DATABASE_URL` / `*_ENABLED` env vars in the compose file are NOT
Superset config keys, so they were being ignored; these settings are the real thing.)
"""
import os

# Persist metadata in the Postgres `superset` database (created by the postgres init script).
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_METADATA_DB_URI",
    "postgresql+psycopg2://superset:superset@postgres:5432/superset",
)

# Stable secret so encrypted fields (e.g. saved DB passwords) survive restarts.
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me-for-real-deployments")

# Course/dev quality-of-life (these ARE real config keys).
WTF_CSRF_ENABLED = False
TALISMAN_ENABLED = False
