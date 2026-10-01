"""lakehouse — one learner = one Polaris lakehouse. Shared by home-api (first login)
and the JupyterHub spawn hook (every server start).

provision(name)     the learner's own MinIO bucket <name>-lake, and catalog <name>_lake stored in
                    it (bronze/silver/gold), principal <name>, principal-role <name> owning the
                    catalog, read-only on the shared lake. Idempotent (also moves an older
                    catalog's default location into the learner's bucket).
reset_secret(name)  give principal <name> a fresh random client secret; returns it. The Hub
                    calls this on each spawn and hands the secret only to that learner's server.
Standard library only.
"""
import json
import os
import datetime
import hashlib
import hmac
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
S3_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin")
S3_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin")
S3_REGION = os.environ.get("AWS_REGION", "us-east-1")
NAMESPACES = ("bronze", "silver", "gold")



def lake_name(username):
    """Keycloak username → a safe Polaris/Iceberg identifier (ravi.k@x → ravi_k_x)."""
    return re.sub(r"[^a-z0-9]+", "_", username.lower()).strip("_") or "learner"


def bucket_name(name):
    """Learner's own bucket. S3 bucket names allow no '_' → ravi_k → ravi-k-lake."""
    return name.replace("_", "-") + "-lake"


def create_bucket(bucket):
    """PUT /<bucket> on MinIO (S3 API, path-style), signed with AWS SigV4 — stdlib only.
    True if created, False if it already exists (ours)."""
    host = urllib.parse.urlparse(S3_ENDPOINT).netloc
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    payload = hashlib.sha256(b"").hexdigest()
    canonical = "\n".join(["PUT", f"/{bucket}", "", f"host:{host}", f"x-amz-content-sha256:{payload}",
                           f"x-amz-date:{amz_date}", "", "host;x-amz-content-sha256;x-amz-date", payload])
    scope = f"{day}/{S3_REGION}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = f"AWS4{S3_SECRET}".encode()
    for part in (day, S3_REGION, "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(f"{S3_ENDPOINT}/{bucket}", method="PUT", data=b"", headers={
        "x-amz-date": amz_date, "x-amz-content-sha256": payload,
        "Authorization": f"AWS4-HMAC-SHA256 Credential={S3_KEY}/{scope}, "
                         f"SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature={sig}"})
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except urllib.error.HTTPError as e:
        if e.code == 409:            # BucketAlreadyOwnedByYou
            return False
        raise RuntimeError(f"create bucket {bucket}: HTTP {e.code} {e.read()[:200]!r}")


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
    bucket = bucket_name(name)
    create_bucket(bucket)
    t = _admin_token()
    m, cat = "/api/management/v1", f"{name}_lake"
    loc = f"s3://{bucket}"
    _ok(_call("POST", f"{m}/catalogs", {"catalog": {
        "name": cat, "type": "INTERNAL",
        "properties": {"default-base-location": loc, "polaris.config.drop-with-purge.enabled": "true"},
        "storageConfigInfo": {"storageType": "S3", "allowedLocations": [loc], "endpoint": S3_ENDPOINT,
                              "pathStyleAccess": True, "region": "us-east-1"}}}, t)[0], "create catalog")
    _move_into_bucket(cat, loc, t)
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


def _move_into_bucket(cat, loc, t):
    """Catalogs created before per-learner buckets stored under s3://demo-bucket/lakes/…:
    make the learner's bucket the default location (old tables keep theirs — still allowed)."""
    st, c = _call("GET", f"/api/management/v1/catalogs/{cat}", token=t)
    if st != 200 or c["properties"].get("default-base-location") == loc:
        return
    storage = c["storageConfigInfo"]
    storage["allowedLocations"] = sorted(set(storage.get("allowedLocations", [])) | {loc})
    props = dict(c["properties"], **{"default-base-location": loc})
    _ok(_call("PUT", f"/api/management/v1/catalogs/{cat}", {
        "currentEntityVersion": c["entityVersion"], "properties": props,
        "storageConfigInfo": storage}, t)[0], f"move {cat} into {loc}")


def reset_secret(name):
    """New random client secret for principal <name> (client id = name). Returns it."""
    new = secrets.token_urlsafe(24)
    st, _ = _call("POST", f"/api/management/v1/principals/{name}/reset",
                  {"clientId": name, "clientSecret": new}, _admin_token())
    if st != 200:
        raise RuntimeError(f"reset secret for {name}: HTTP {st}")
    return new
