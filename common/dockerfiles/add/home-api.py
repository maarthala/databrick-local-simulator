"""home-api — the landing page's tiny backend (behind oauth2-proxy).

GET /api/me  → who is logged in (from the headers oauth2-proxy sets after the Keycloak
               login) and, on first call, provisions that learner's own lakehouse in
               Polaris: catalog <name>_lake (bronze/silver/gold), principal <name>,
               principal-role <name> owning the catalog, plus read access to the shared
               lake. Idempotent — every step accepts "already exists" (409).

Only reachable through oauth2-proxy (it is not published), so the identity headers can
be trusted. Standard library only.
"""
import json
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

POLARIS = os.environ.get("POLARIS_URL", "http://polaris:8181")
ADMIN = os.environ.get("POLARIS_ADMIN", "root:s3cr3t")
REALM = os.environ.get("POLARIS_REALM", "POLARIS")
SHARED = os.environ.get("SHARED_CATALOG", "polaris_lake")
S3_ENDPOINT = os.environ.get("LAKE_S3_ENDPOINT", "http://minio:9000")
LAKE_BASE = os.environ.get("LAKE_BASE", "s3://demo-bucket/lakes")
NAMESPACES = ("bronze", "silver", "gold")

_ready = set()            # learners already provisioned since start (skip the API calls)
_lock = threading.Lock()


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


def provision(name):
    """Create (or confirm) the learner's lakehouse + identity in Polaris."""
    cid, secret = ADMIN.split(":", 1)
    st, tok = _call("POST", "/api/catalog/v1/oauth/tokens", form={
        "grant_type": "client_credentials", "client_id": cid, "client_secret": secret,
        "scope": "PRINCIPAL_ROLE:ALL"})
    if st != 200:
        raise RuntimeError(f"Polaris admin login: HTTP {st}")
    t = tok["access_token"]
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


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            return self._json(200, {"ok": True})
        if self.path != "/api/me":
            return self._json(404, {"error": "not found"})
        h = self.headers
        user = h.get("X-Forwarded-Preferred-Username") or h.get("X-Forwarded-User")
        if not user:
            return self._json(401, {"error": "not logged in"})
        name = lake_name(user)
        me = {"user": user, "email": h.get("X-Forwarded-Email", ""),
              # oauth2-proxy's keycloak provider adds roles as "role:…" — keep real groups only
              "groups": [g for g in (h.get("X-Forwarded-Groups") or "").split(",") if g and not g.startswith("role:")],
              "lakehouse": f"{name}_lake", "principal": name}
        try:
            with _lock:
                if name not in _ready:
                    provision(name)
                    _ready.add(name)
            me["status"] = "ready"
        except Exception as e:                       # show it on the page, don't crash
            me["status"], me["detail"] = "error", str(e)
        return self._json(200, me)

    def log_message(self, fmt, *args):               # quieter logs: one line per request
        print(f"[home-api] {self.address_string()} {fmt % args}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"[home-api] listening on :{port}, Polaris {POLARIS}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
