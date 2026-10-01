"""JupyterHub for the local stack: Keycloak login, one Jupyter container per learner,
and every learner's `iceberg` catalog pointed at their OWN Polaris lakehouse.

Spawn hook (every server start): make sure <name>_lake exists (lakehouse.provision),
give principal <name> a fresh random client secret (lakehouse.reset_secret) and hand it
ONLY to that learner's container as LAKE_* env; the IPython startup (00-spark.py)
applies it to the Spark session. Same idea on k8s via the Zero-to-JupyterHub chart.

Keycloak hostnames: the browser goes to the PUBLIC login URL, the Hub calls Keycloak's
token/userinfo on the internal address (as oauth2-proxy does) — no hosts-file tricks.
"""
import os

from lakehouse import bucket_name, lake_name, provision, reset_secret, storage_key

env = os.environ
c = get_config()  # noqa: F821

# ---- login: Keycloak (realm de-lab, client jupyterhub) -----------------------------
KC_PUBLIC = env["KEYCLOAK_PUBLIC_URL"].rstrip("/")      # http://localhost:8180 | http://auth.de.lan
KC_INTERNAL = env["KEYCLOAK_INTERNAL_URL"].rstrip("/")  # http://keycloak:8080
REALM = env.get("KEYCLOAK_REALM", "de-lab")
c.JupyterHub.authenticator_class = "generic-oauth"
c.GenericOAuthenticator.client_id = env.get("OAUTH_CLIENT_ID", "jupyterhub")
c.GenericOAuthenticator.client_secret = env["OAUTH_CLIENT_SECRET"]
c.GenericOAuthenticator.oauth_callback_url = env["HUB_PUBLIC_URL"].rstrip("/") + "/hub/oauth_callback"
c.GenericOAuthenticator.authorize_url = f"{KC_PUBLIC}/realms/{REALM}/protocol/openid-connect/auth"
c.GenericOAuthenticator.token_url = f"{KC_INTERNAL}/realms/{REALM}/protocol/openid-connect/token"
c.GenericOAuthenticator.userdata_url = f"{KC_INTERNAL}/realms/{REALM}/protocol/openid-connect/userinfo"
c.GenericOAuthenticator.scope = ["openid", "profile"]
c.GenericOAuthenticator.username_claim = "preferred_username"
c.GenericOAuthenticator.login_service = "Epireum's Data Engineering Lab"
c.GenericOAuthenticator.allow_all = True                        # everyone in the realm
c.GenericOAuthenticator.manage_groups = True                     # Keycloak groups → Hub groups
c.GenericOAuthenticator.auth_state_groups_key = "oauth_user.groups"
c.GenericOAuthenticator.admin_groups = {"instructors"}          # Hub admin page
c.Authenticator.auto_login = True                               # straight to Keycloak (SSO → silent)
# Follow the Keycloak session: keep the tokens and re-check them every minute. After a
# logout / switching user on the home page, the old token is rejected → the Hub signs
# you in again as whoever is logged in to Keycloak now (not the previous user).
c.GenericOAuthenticator.enable_auth_state = True
c.Authenticator.auth_refresh_age = 60
c.Authenticator.refresh_pre_spawn = True

# ---- one container per learner ------------------------------------------------------
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"
c.DockerSpawner.image = env.get("SINGLEUSER_IMAGE", "local-jupyter:latest")
c.DockerSpawner.network_name = env.get("DOCKER_NETWORK", "local_sparknet")
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True                                   # containers are disposable…
c.DockerSpawner.volumes = {"jupyterhub-user-{username}": "/home/jovyan/work"}  # …work isn't
c.DockerSpawner.notebook_dir = "/home/jovyan/work"
c.DockerSpawner.name_template = "jupyter-{username}"
c.DockerSpawner.mem_limit = env.get("SINGLEUSER_MEM", "1G")
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = env.get("HUB_CONNECT_IP", "jupyterhub")

# env every learner container gets (Spark Connect, MinIO, notebook auto-push)
PASS = ["SPARK_REMOTE", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION",
        "AWS_REGION", "AWS_S3_ENDPOINT", "GIT_AUTOPUSH", "GIT_REPO_URL", "GIT_BRANCH",
        "GIT_USERNAME", "GIT_TOKEN"]
c.DockerSpawner.environment = {k: env[k] for k in PASS if env.get(k)}


async def pre_spawn(spawner):
    """Learner's own lakehouse + a fresh Polaris secret, handed only to their server."""
    name = lake_name(spawner.user.name)
    provision(name, instructor=any(g.name == "instructors" for g in spawner.user.groups))
    secret = reset_secret(name)
    s3_key, s3_secret = storage_key(name)      # own-bucket-only key for the "my bucket" drive
    spawner.environment.update({
        "LAKE_USER": name,
        "LAKE_WAREHOUSE": f"{name}_lake",
        "LAKE_CREDENTIAL": f"{name}:{secret}",
        "LAKE_BUCKET": bucket_name(name),
        "LAKE_S3_KEY": s3_key,
        "LAKE_S3_SECRET": s3_secret,
        # %%sql materialized-view pipeline files go to the learner's own bucket too
        "MV_PIPELINE_STORAGE": f"s3a://{bucket_name(name)}/pipelines/mv",
        "GIT_AUTHOR_NAME": spawner.user.name,
        "GIT_AUTHOR_EMAIL": f"{spawner.user.name}@de.lan",
    })
    spawner.log.info("lakehouse %s_lake ready for %s", name, spawner.user.name)


c.Spawner.pre_spawn_hook = pre_spawn

# ---- housekeeping -------------------------------------------------------------------
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/data/jupyterhub.sqlite"
c.JupyterHub.cookie_secret_file = "/srv/jupyterhub/data/jupyterhub_cookie_secret"
# stop idle learner servers after an hour (frees memory; work is in their volume)
c.JupyterHub.load_roles = [{
    "name": "idle-culler",
    "scopes": ["list:users", "read:users:activity", "read:servers", "delete:servers"],
    "services": ["idle-culler"],
}]
c.JupyterHub.services = [{
    "name": "idle-culler",
    "command": ["python3", "-m", "jupyterhub_idle_culler", "--timeout=3600"],
}]
