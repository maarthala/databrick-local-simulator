"""lakehouse — one learner = one Polaris lakehouse. Shared by home-api (first login)
and the JupyterHub spawn hook (every server start).

provision(name)     the learner's own bucket <name>-lake on the object store (RustFS) with a
                    hard quota and a storage policy named after them (their bucket only —
                    instructors: everything), and catalog <name>_lake stored in it
                    (bronze/silver/gold), principal <name>, principal-role <name> owning the
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
QUOTA_MB = int(os.environ.get("LEARNER_QUOTA_MB", "20"))      # per-learner bucket, hard limit
SQLPAD = os.environ.get("SQLPAD_URL", "http://sqlpad:3000")
SQLPAD_ADMIN = os.environ.get("SQLPAD_ADMIN", "admin@de.local:admin1234")
NAMESPACES = ("bronze", "silver", "gold")



def lake_name(username):
    """Keycloak username → a safe Polaris/Iceberg identifier (ravi.k@x → ravi_k_x)."""
    return re.sub(r"[^a-z0-9]+", "_", username.lower()).strip("_") or "learner"


def bucket_name(name):
    """Learner's own bucket. S3 bucket names allow no '_' → ravi_k → ravi-k-lake."""
    return name.replace("_", "-") + "-lake"


def _s3(method, bucket, key="", query=None, body=b"", headers=None, stream=None, length=None):
    """One S3 call to the object store (path-style)."""
    path = "/" + bucket + ("/" + urllib.parse.quote(key, safe="/~") if key else "")
    return _signed(method, path, query, body, headers, stream, length)


def _admin(method, op, query=None, body=b""):
    """Object-store admin API (RustFS speaks MinIO's /minio/admin/v3/…), same SigV4 signing."""
    with _signed(method, f"/minio/admin/v3/{op}", query, body, {"content-type": "application/json"}) as r:
        return r.status


def _signed(method, path, query=None, body=b"", headers=None, stream=None, length=None):
    """Sign with AWS SigV4 (stdlib only) and send. `stream` + `length` send a file-like
    body unsigned (UNSIGNED-PAYLOAD) without buffering it. Returns the open response."""
    host = urllib.parse.urlparse(S3_ENDPOINT).netloc
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    qs = "&".join(f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(str(v), safe='-_.~')}"
                  for k, v in sorted((query or {}).items()))
    payload = "UNSIGNED-PAYLOAD" if stream is not None else hashlib.sha256(body).hexdigest()
    hdrs = {"host": host, "x-amz-content-sha256": payload, "x-amz-date": amz_date}
    hdrs.update({k.lower(): v for k, v in (headers or {}).items()})
    signed = ";".join(sorted(hdrs))
    canonical = "\n".join([method, path, qs, *(f"{k}:{hdrs[k]}" for k in sorted(hdrs)), "", signed, payload])
    scope = f"{day}/{S3_REGION}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = f"AWS4{S3_SECRET}".encode()
    for part in (day, S3_REGION, "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    sig = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    out = {k: v for k, v in hdrs.items() if k != "host"}
    out["Authorization"] = (f"AWS4-HMAC-SHA256 Credential={S3_KEY}/{scope}, "
                            f"SignedHeaders={signed}, Signature={sig}")
    data = stream if stream is not None else (body if method in ("PUT", "POST") else None)
    if stream is not None:
        out["Content-Length"] = str(length)
    req = urllib.request.Request(f"{S3_ENDPOINT}{path}" + (f"?{qs}" if qs else ""),
                                 data=data, method=method, headers=out)
    return urllib.request.urlopen(req, timeout=60)


def create_bucket(bucket):
    """True if created, False if it already exists (ours)."""
    try:
        _s3("PUT", bucket).close()
        return True
    except urllib.error.HTTPError as e:
        if e.code == 409:            # BucketAlreadyOwnedByYou
            return False
        raise RuntimeError(f"create bucket {bucket}: HTTP {e.code} {e.read()[:200]!r}")


def storage_user(name):
    """Keycloak username for a lake name (usernames are a-z0-9- only; lake names use _)."""
    return name.replace("_", "-")


def put_storage_policy(name, admin=False):
    """Policy named after the learner (Keycloak sends the username as the `policy` claim on
    the object-store console login): their own bucket only — or everything for instructors.
    (RustFS doesn't expand ${jwt:…} in resource names, so it's one policy per learner.)"""
    bucket = bucket_name(name)
    doc = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["admin:*"]},
        {"Effect": "Allow", "Action": ["s3:*"], "Resource": ["arn:aws:s3:::*"]}]} if admin else {
        "Version": "2012-10-17", "Statement": [
            {"Effect": "Allow", "Action": ["s3:ListBucket", "s3:GetBucketLocation", "s3:ListBucketMultipartUploads"],
             "Resource": [f"arn:aws:s3:::{bucket}"]},
            {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject",
                                           "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"],
             "Resource": [f"arn:aws:s3:::{bucket}/*"]}]}
    return _admin("PUT", "add-canned-policy", {"name": storage_user(name)}, json.dumps(doc).encode())


def set_quota(bucket, mb=QUOTA_MB):
    """Hard quota: uploads that would exceed it are rejected."""
    return _admin("PUT", "set-bucket-quota", {"bucket": bucket},
                  json.dumps({"quota": mb * 1024 * 1024, "quotatype": "hard"}).encode())


# ---- "My files": the learner's own bucket only (callers pass bucket_name(user)) ----
_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"


def list_dir(bucket, prefix=""):
    """One folder level: ({folders}, [{key,size,modified}]) under `prefix`."""
    import xml.etree.ElementTree as ET
    folders, files, token = [], [], None
    while True:
        q = {"list-type": "2", "delimiter": "/", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        with _s3("GET", bucket, query=q) as r:
            root = ET.fromstring(r.read())
        folders += [p.findtext(f"{_NS}Prefix") for p in root.findall(f"{_NS}CommonPrefixes")]
        for c in root.findall(f"{_NS}Contents"):
            key = c.findtext(f"{_NS}Key")
            if key == prefix:                     # the folder marker itself
                continue
            files.append({"key": key, "size": int(c.findtext(f"{_NS}Size")),
                          "modified": c.findtext(f"{_NS}LastModified")})
        token = root.findtext(f"{_NS}NextContinuationToken")
        if root.findtext(f"{_NS}IsTruncated") != "true":
            return folders, files


def list_all(bucket, prefix):
    """Every key under `prefix` (recursive)."""
    import xml.etree.ElementTree as ET
    keys, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        with _s3("GET", bucket, query=q) as r:
            root = ET.fromstring(r.read())
        keys += [c.findtext(f"{_NS}Key") for c in root.findall(f"{_NS}Contents")]
        token = root.findtext(f"{_NS}NextContinuationToken")
        if root.findtext(f"{_NS}IsTruncated") != "true":
            return keys


def is_table(keys):
    """An Iceberg table folder holds metadata/*.metadata.json."""
    return any("/metadata/" in k and k.endswith(".metadata.json") for k in keys)


def put_object(bucket, key, stream, length, content_type="application/octet-stream"):
    _s3("PUT", bucket, key, stream=stream, length=length, headers={"content-type": content_type}).close()


def get_object(bucket, key):
    return _s3("GET", bucket, key)


def delete_object(bucket, key):
    _s3("DELETE", bucket, key).close()


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


def invite_sqlpad(name, admin=False):
    """Pre-create the learner in SQLPad (user id = Keycloak username). SQLPad's OIDC login
    only auto-creates users whose EMAIL domain is allowed — our learners have no email —
    but it signs in any user that already exists. Instructors are SQLPad admins."""
    user, role = storage_user(name), "admin" if admin else "editor"
    auth = "Basic " + __import__("base64").b64encode(SQLPAD_ADMIN.encode()).decode()
    def req(method, path, body=None):
        r = urllib.request.Request(SQLPAD + path, method=method, headers={
            "Authorization": auth, "Content-Type": "application/json"},
            data=None if body is None else json.dumps(body).encode())
        with urllib.request.urlopen(r, timeout=10) as resp:
            return json.loads(resp.read() or b"null")
    users = {u["email"]: u for u in req("GET", "/api/users")}
    if user not in users:
        req("POST", "/api/users", {"email": user, "name": user, "role": role})
    elif users[user]["role"] != role:
        req("PUT", f"/api/users/{users[user]['id']}", {"role": role})


def provision(name, instructor=False):
    """Create (or confirm) the learner's bucket, storage policy, lakehouse + Polaris identity,
    and their SQLPad account."""
    bucket = bucket_name(name)
    create_bucket(bucket)
    set_quota(bucket)
    put_storage_policy(name, admin=instructor)
    invite_sqlpad(name, admin=instructor)
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
