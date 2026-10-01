"""Airflow UI login (FAB auth manager) — sign in with the lab account (Keycloak).

On when KEYCLOAK_ENABLED=1, otherwise Airflow's normal database login. Users are created
on first sign-in; Keycloak groups map to Airflow roles and are re-synced every login
(instructors → Admin, learners → User). Learners have no email, so the username is the
identity (placeholder <user>@de.lan for FAB's unique-email column).

Endpoints come from Keycloak's discovery document fetched on the INTERNAL address:
Keycloak returns the browser-facing authorize URL plus internal token/keys URLs, and
tokens carry the public issuer — no hosts-file tricks (same as Superset / SQLPad).
"""
import os

from flask_appbuilder.const import AUTH_DB, AUTH_OAUTH

AUTH_TYPE = AUTH_DB
WTF_CSRF_ENABLED = True

if os.environ.get("KEYCLOAK_ENABLED") == "1":
    from airflow.providers.fab.auth_manager.security_manager.override import (
        FabAirflowSecurityManagerOverride,
    )

    _KC = os.environ.get("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080").rstrip("/") + "/realms/de-lab"

    AUTH_TYPE = AUTH_OAUTH
    AUTH_USER_REGISTRATION = True
    AUTH_USER_REGISTRATION_ROLE = "User"
    AUTH_ROLES_MAPPING = {"instructors": ["Admin"], "learners": ["User"]}
    AUTH_ROLES_SYNC_AT_LOGIN = True
    OAUTH_PROVIDERS = [{
        "name": "keycloak",
        "icon": "fa-key",
        "token_key": "access_token",
        "remote_app": {
            "client_id": os.environ.get("KEYCLOAK_CLIENT_ID", "airflow"),
            "client_secret": os.environ.get("KEYCLOAK_CLIENT_SECRET", "airflow-secret"),
            "server_metadata_url": f"{_KC}/.well-known/openid-configuration",
            "api_base_url": f"{_KC}/protocol/openid-connect/",
            "client_kwargs": {"scope": "openid profile"},
        },
    }]

    class LabSecurityManager(FabAirflowSecurityManagerOverride):
        """Username = identity; Keycloak groups → role mapping."""

        def get_oauth_user_info(self, provider, resp):
            me = self.appbuilder.sm.oauth_remotes[provider].get("userinfo").json()
            user = me["preferred_username"]
            return {
                "username": user,
                "first_name": me.get("given_name") or user,
                "last_name": me.get("family_name") or "",
                "email": me.get("email") or f"{user}@de.lan",
                "role_keys": me.get("groups", []),
            }

        oauth_user_info = get_oauth_user_info

    SECURITY_MANAGER_CLASS = LabSecurityManager
