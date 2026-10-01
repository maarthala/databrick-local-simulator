"""lakehouse — one learner = one Polaris lakehouse. Shared by home-api (first login)
and the JupyterHub spawn hook (every server start).

provision(name)     catalog <name>_lake (bronze/silver/gold), principal <name>, principal-role
                    <name> owning the catalog, read-only on the shared lake. Idempotent.
reset_secret(name)  give principal <name> a fresh random client secret; returns it. The Hub
                    calls this on each spawn and hands the secret only to that learner's server.
Standard library only.
"""
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request

POLARIS = os.environ.get("POLARIS_URL", "http://polaris:8181")
ADMIN = os.environ.get("POLARIS_ADMIN", "root:s3cr3t")
REALM = os.environ.get("POLARIS_REALM", "POLARIS")
SHARED = os.environ.get("SHARED_CATALOG", "polaris_lake")
S3_ENDPOINT = os.environ.get("LAKE_S3_ENDPOINT", "http://minio:9000")
LAKE_BASE = os.environ.get("LAKE_BASE", "s3://demo-bucket/lakes")
NAMESPACES = ("bronze", "silver", "gold")



def lake_name(username):
    """Keycloak username → a safe Polaris/Iceberg identifier (ravi.k@x → ravi_k_x)."""
    return re.sub(r"[^a-z0-9]+", "_", username.lower()).strip("_") or "learner"


def _call(method, path, body=None, token=None, form=None):
    headers = {"Polaris-Realm": REALM}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(POLARIS + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def _ok(status, what):
    if status not in (200, 201, 204, 409):          # 409 = already exists → fine
        raise RuntimeError(f"{what}: HTTP {status}")


def _admin_token():
    cid, secret = ADMIN.split(":", 1)
    st, tok = _call("POST", "/api/catalog/v1/oauth/tokens", form={
        "grant_type": "client_credentials", "client_id": cid, "client_secret": secret,
        "scope": "PRINCIPAL_ROLE:ALL"})
    if st != 200:
        raise RuntimeError(f"Polaris admin login: HTTP {st}")
    return tok["access_token"]


def provision(name):
    """Create (or confirm) the learner's lakehouse + identity in Polaris."""
    t = _admin_token()
    m, cat = "/api/management/v1", f"{name}_lake"
    loc = f"{LAKE_BASE}/{name}"
    _ok(_call("POST", f"{m}/catalogs", {"catalog": {
        "name": cat, "type": "INTERNAL",
        "properties": {"default-base-location": loc, "polaris.config.drop-with-purge.enabled": "true"},
        "storageConfigInfo": {"storageType": "S3", "allowedLocations": [loc], "endpoint": S3_ENDPOINT,
                              "pathStyleAccess": True, "region": "us-east-1"}}}, t)[0], "create catalog")
    for ns in NAMESPACES:
        _ok(_call("POST", f"/api/catalog/v1/{cat}/namespaces", {"namespace": [ns]}, t)[0], f"namespace {ns}")
    _ok(_call("POST", f"{m}/principals", {"principal": {"name": name}}, t)[0], "principal")
    _ok(_call("POST", f"{m}/principal-roles", {"principalRole": {"name": name}}, t)[0], "principal-role")
    _ok(_call("PUT", f"{m}/principals/{name}/principal-roles", {"principalRole": {"name": name}}, t)[0], "assign role")
    # owner of their own lake
    _ok(_call("POST", f"{m}/catalogs/{cat}/catalog-roles", {"catalogRole": {"name": "owner"}}, t)[0], "owner role")
    _ok(_call("PUT", f"{m}/catalogs/{cat}/catalog-roles/owner/grants",
              {"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}}, t)[0], "owner grant")
    _ok(_call("PUT", f"{m}/principal-roles/{name}/catalog-roles/{cat}", {"catalogRole": {"name": "owner"}}, t)[0],
        "attach owner")
    # read-only on the shared lake (skipped if it hasn't been seeded yet)
    if _call("GET", f"{m}/catalogs/{SHARED}", token=t)[0] == 200:
        _ok(_call("POST", f"{m}/catalogs/{SHARED}/catalog-roles", {"catalogRole": {"name": "learner_reader"}}, t)[0],
            "reader role")
        for ns in NAMESPACES:
            for priv in ("TABLE_LIST", "TABLE_READ_DATA"):
                _ok(_call("PUT", f"{m}/catalogs/{SHARED}/catalog-roles/learner_reader/grants",
                          {"grant": {"type": "namespace", "namespace": [ns], "privilege": priv}}, t)[0], "reader grant")
        _ok(_call("PUT", f"{m}/principal-roles/{name}/catalog-roles/{SHARED}",
                  {"catalogRole": {"name": "learner_reader"}}, t)[0], "attach reader")


def reset_secret(name):
    """New random client secret for principal <name> (client id = name). Returns it."""
    new = secrets.token_urlsafe(24)
    st, _ = _call("POST", f"/api/management/v1/principals/{name}/reset",
                  {"clientId": name, "clientSecret": new}, _admin_token())
    if st != 200:
        raise RuntimeError(f"reset secret for {name}: HTTP {st}")
    return new
