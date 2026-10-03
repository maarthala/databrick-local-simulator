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

# ---- Sign in with the lab account (Keycloak realm de-lab, client `superset`) ----------
# On when KEYCLOAK_ENABLED=1. Users are created on first sign-in; Keycloak groups map to
# Superset roles (managers → Admin, learners → Alpha) and are re-synced every login.
# Endpoints come from Keycloak's discovery document fetched on the INTERNAL address:
# Keycloak returns the browser-facing authorize URL and internal token/keys URLs, and
# tokens carry the public issuer — no hosts-file tricks.
if os.environ.get("KEYCLOAK_ENABLED") == "1":
    from flask_appbuilder.security.manager import AUTH_OAUTH
    from superset.security import SupersetSecurityManager

    _KC = os.environ.get("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080").rstrip("/") + "/realms/de-lab"

    AUTH_TYPE = AUTH_OAUTH
    AUTH_USER_REGISTRATION = True
    AUTH_USER_REGISTRATION_ROLE = "Alpha"
    AUTH_ROLES_MAPPING = {"managers": ["Admin"], "learners": ["Alpha"]}
    AUTH_ROLES_SYNC_AT_LOGIN = True
    OAUTH_PROVIDERS = [{
        "name": "keycloak",
        "icon": "fa-key",
        "token_key": "access_token",
        "remote_app": {
            "client_id": os.environ.get("KEYCLOAK_CLIENT_ID", "superset"),
            "client_secret": os.environ.get("KEYCLOAK_CLIENT_SECRET", "superset-secret"),
            "server_metadata_url": f"{_KC}/.well-known/openid-configuration",
            "api_base_url": f"{_KC}/protocol/openid-connect/",
            "client_kwargs": {"scope": "openid profile"},
        },
    }]

    from flask import request
    from flask_appbuilder import expose
    from flask_appbuilder.security.views import AuthOAuthView

    class LabAuthOAuthView(AuthOAuthView):
        """Straight to the lab sign-in (the only provider) instead of a "Sign in with keycloak"
        page — already signed in to the lab, the user lands in Superset. /login/?local=1 shows it."""

        @expose("/login/")
        @expose("/login/<provider>")
        def login(self, provider=None):
            if provider is None and request.args.get("local") != "1":
                provider = "keycloak"
            return super().login(provider)

    class LabSecurityManager(SupersetSecurityManager):
        """Learners have no email: username is the identity; groups → role mapping."""
        authoauthview = LabAuthOAuthView

        def oauth_user_info(self, provider, response=None):
            me = self.appbuilder.sm.oauth_remotes[provider].get("userinfo").json()
            user = me["preferred_username"]
            return {
                "username": user,
                "first_name": me.get("given_name") or user,
                "last_name": me.get("family_name") or "",
                "email": me.get("email") or f"{user}@de.lan",   # Superset needs a unique email
                "role_keys": me.get("groups", []),
            }

    CUSTOM_SECURITY_MANAGER = LabSecurityManager

    def FLASK_APP_MUTATOR(app):
        """Superset 6 serves its own React login page at /login/ (ahead of the OAuth view) — send
        it straight to the lab sign-in as well; /login/?local=1 still shows the page."""
        from flask import redirect

        @app.before_request
        def _straight_to_lab_login():
            if request.path == "/login/" and request.args.get("local") != "1":
                return redirect("/login/keycloak" + ("?" + request.query_string.decode() if request.query_string else ""))
