"""labadmin — the platform manager's learner admin, behind the "Manage learners" page
(home-api /api/admin/*, managers only). Uses home-api's admin logins: Polaris, storage, SQLPad,
plus the Keycloak admin (KEYCLOAK_ADMIN=user:password) and a JupyterHub service token
(HUB_ADMIN_TOKEN) to stop a learner's Jupyter and drop its volume.

  learners()                 lab accounts, their lakehouse and bucket use
  create(user, password)     new lab account + lakehouse, bucket, SQLPad user
  set_password(user, pw)     new password (the learner picks their own at the next sign-in)
  reset_lakehouse(user)      drop every table/view in their catalogs (bronze/silver/gold and the
                             sample table come back); files, catalogs and shares are kept
  wipe(user)                 reset_lakehouse + empty bucket + fresh Jupyter (starter files back)
  delete(user)               remove the account and everything it owns
"""
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

import lakehouse as lh

KEYCLOAK = os.environ.get("KEYCLOAK_URL", "http://keycloak:8080")
REALM = os.environ.get("KEYCLOAK_REALM", "de-lab")
HUB_API = os.environ.get("HUB_API_URL", "http://jupyterhub:8081/hub/api")
USERNAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}$")
_C = "/api/catalog/v1"


class AdminError(Exception):
    """A problem to show the manager (bad input, unknown user …)."""


def _http(method, url, body=None, headers=None, form=None):
    headers, data = dict(headers or {}), None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]


# ---- Keycloak (admin REST API) ----------------------------------------------------------
def _kc(method, path, body=None, token=None):
    return _http(method, KEYCLOAK + path, body, {"Authorization": f"Bearer {token}"})


def _kc_token():
    user, pw = os.environ.get("KEYCLOAK_ADMIN", "admin:admin").split(":", 1)
    st, body = _http("POST", f"{KEYCLOAK}/realms/master/protocol/openid-connect/token", form={
        "grant_type": "password", "client_id": "admin-cli", "username": user, "password": pw})
    if st != 200:
        raise RuntimeError(f"Keycloak admin login: HTTP {st}")
    return body["access_token"]


def _kc_user(user, t):
    st, body = _kc("GET", f"/admin/realms/{REALM}/users?" +
                   urllib.parse.urlencode({"username": user, "exact": "true"}), token=t)
    return body[0] if st == 200 and body else None


# ---- JupyterHub: stop the learner's server and forget them (the spawner drops the volume) --
def _hub(method, path):
    token = os.environ.get("HUB_ADMIN_TOKEN", "")
    return _http(method, HUB_API + path, headers={"Authorization": f"token {token}"}) if token else (0, None)


def _hub_forget(user):
    """Stop the learner's Jupyter and delete them from the Hub — with them goes their work
    volume (Docker volume / PVC), so old notebooks can't sync back into a wiped bucket. The
    Hub re-creates the user (fresh volume) at their next sign-in. False if it didn't work."""
    st, info = _hub("GET", f"/users/{user}")
    if st == 404:
        return True                                   # never opened Jupyter
    if st != 200:
        return False
    if (info or {}).get("servers"):
        _hub("DELETE", f"/users/{user}/server")
        for _ in range(60):                           # stopping is async (202)
            st, info = _hub("GET", f"/users/{user}")
            if st == 200 and not info.get("servers") and not info.get("pending"):
                break
            time.sleep(1)
    st, _ = _hub("DELETE", f"/users/{user}")
    return st in (204, 404)


# ---- Polaris: tables of a catalog -------------------------------------------------------
def _ns_path(ns):
    return urllib.parse.quote("\x1f".join(ns), safe="")


def _namespaces(cat, t, parent=None):
    """Every namespace of `cat`, deepest first (so children are dropped before parents)."""
    q = f"?parent={_ns_path(parent)}" if parent else ""
    st, body = lh._call("GET", f"{_C}/{cat}/namespaces{q}", token=t)
    out = []
    for ns in (body or {}).get("namespaces", []) if st == 200 else []:
        out += _namespaces(cat, t, ns) + [ns]
    return out


def _clear_catalog(cat, t, keep=True):
    """Drop every table and view in `cat`, and every namespace but bronze/silver/gold (all of
    them if not keep). The files are removed from the bucket afterwards."""
    dropped = 0
    for ns in _namespaces(cat, t):
        p = f"{_C}/{cat}/namespaces/{_ns_path(ns)}"
        for kind in ("views", "tables"):
            st, body = lh._call("GET", f"{p}/{kind}", token=t)
            for ident in (body or {}).get("identifiers", []) if st == 200 else []:
                name = urllib.parse.quote(ident["name"], safe="")
                lh._ok(lh._call("DELETE", f"{p}/{kind}/{name}", token=t)[0],
                       f"drop {cat}.{'.'.join(ns)}.{ident['name']}")
                dropped += 1
        if not keep or ns not in [[n] for n in lh.NAMESPACES]:
            lh._ok(lh._call("DELETE", p, token=t)[0], f"drop namespace {cat}.{'.'.join(ns)}")
    return dropped


def _content_token():
    """Polaris token of trino_lab: every learner catalog grants it CATALOG_MANAGE_CONTENT
    (root manages catalogs and grants, but can't drop tables in them)."""
    cid, secret = lh.TRINO_LOGIN.split(":", 1)
    st, tok = lh._call("POST", f"{_C}/oauth/tokens", form={
        "grant_type": "client_credentials", "client_id": cid, "client_secret": secret,
        "scope": "PRINCIPAL_ROLE:ALL"})
    if st != 200:
        raise RuntimeError(f"Polaris login {cid}: HTTP {st}")
    return tok["access_token"]


def _owned_catalogs(name, t):
    return [c["name"] for c in lh._get(f"{lh._M}/catalogs", t)["catalogs"] if lh._owned(name, c["name"], t)]


def _bucket_mb(bucket):
    import xml.etree.ElementTree as ET
    total, token = 0, None
    while True:
        q = {"list-type": "2"}
        if token:
            q["continuation-token"] = token
        with lh._s3("GET", bucket, query=q) as r:
            root = ET.fromstring(r.read())
        total += sum(int(c.findtext(f"{lh._NS}Size") or 0) for c in root.findall(f"{lh._NS}Contents"))
        token = root.findtext(f"{lh._NS}NextContinuationToken")
        if root.findtext(f"{lh._NS}IsTruncated") != "true":
            return round(total / 1e6, 1)


def _empty_prefix(bucket, prefix):
    keys = lh.list_all(bucket, prefix)
    for k in keys:
        lh.delete_object(bucket, k)
    return len(keys)


def _check(user, t=None):
    if not USERNAME.match(user or ""):
        raise AdminError("username: 2-31 characters of a-z, 0-9 and -")
    if t and not _kc_user(user, t):
        raise AdminError(f"no lab account {user}")


# ---- the actions ------------------------------------------------------------------------
def learners():
    t, kc = lh._admin_token(), _kc_token()
    st, users = _kc("GET", f"/admin/realms/{REALM}/users?max=1000&briefRepresentation=true", token=kc)
    st, mgrs = _kc("GET", f"/admin/realms/{REALM}/groups?search=managers", token=kc)
    gid = next((g["id"] for g in mgrs or [] if g["name"] == "managers"), None)
    managers = set()
    if gid:
        _, members = _kc("GET", f"/admin/realms/{REALM}/groups/{gid}/members?max=1000", token=kc)
        managers = {m["username"] for m in members or []}
    out = []
    for u in sorted(users or [], key=lambda u: u["username"]):
        name = lh.lake_name(u["username"])
        try:
            cats = _owned_catalogs(name, t)
        except RuntimeError:
            cats = []
        try:
            mb = _bucket_mb(lh.bucket_name(name))
        except Exception:
            mb = None
        out.append({"user": u["username"], "manager": u["username"] in managers,
                    "enabled": u.get("enabled", True), "created": u.get("createdTimestamp"),
                    "lakehouse": f"{name}_lake" if f"{name}_lake" in cats else None,
                    "catalogs": cats, "bucket": lh.bucket_name(name), "bucket_mb": mb})
    return out


def create(user, password=None):
    _check(user)
    kc, pw = _kc_token(), password or secrets.token_urlsafe(9)
    if _kc_user(user, kc):
        raise AdminError(f"{user} already exists")
    st, body = _kc("POST", f"/admin/realms/{REALM}/users", {
        "username": user, "enabled": True,
        "credentials": [{"type": "password", "value": pw, "temporary": True}]}, token=kc)
    if st != 201:
        raise RuntimeError(f"create {user} in Keycloak: HTTP {st} {body!r}")
    name = lh.lake_name(user)
    lh.provision(name)
    lh.publish_trino_rules()
    return {"user": user, "password": pw, "lakehouse": f"{name}_lake", "bucket": lh.bucket_name(name)}


def set_password(user, password=None):
    kc = _kc_token()
    _check(user, kc)
    pw = password or secrets.token_urlsafe(9)
    st, body = _kc("PUT", f"/admin/realms/{REALM}/users/{_kc_user(user, kc)['id']}/reset-password",
                   {"type": "password", "value": pw, "temporary": True}, token=kc)
    if st != 204:
        raise RuntimeError(f"reset password: HTTP {st} {body!r}")
    return {"user": user, "password": pw}


def _reset(user, prefix):
    """Drop every table/view in the learner's catalogs, empty `prefix` of their bucket, then
    re-provision (bronze/silver/gold, starter files, sample table)."""
    _check(user)
    name, t = lh.lake_name(user), lh._admin_token()
    cats = _owned_catalogs(name, t)
    if not cats:
        raise AdminError(f"{user} has no lakehouse yet (never signed in)")
    for c in cats:
        lh.trino_catalog(c, t)                    # makes sure trino_lab holds its grant
    ct = _content_token()
    dropped = sum(_clear_catalog(c, ct) for c in cats)
    files = _empty_prefix(lh.bucket_name(name), prefix)
    lh.provision(name)
    return {"user": user, "catalogs": cats, "dropped": dropped, "files_removed": files}


def reset_lakehouse(user):
    return _reset(user, "tables/")


def wipe(user):
    jupyter = _hub_forget(user)                   # first: a running Jupyter would sync files back
    out = _reset(user, "")
    out["jupyter_reset"] = jupyter
    return out


def delete(user):
    _check(user)
    name, t, kc = lh.lake_name(user), lh._admin_token(), _kc_token()
    jupyter = _hub_forget(user)
    bucket, cats = lh.bucket_name(name), _owned_catalogs(name, t)
    ct = _content_token() if cats else None
    for cat in cats:                                     # tables, namespaces, roles, catalog
        lh.trino_catalog(cat, t)
        _clear_catalog(cat, ct, keep=False)
        try:
            lh._trino(f"DROP CATALOG IF EXISTS {cat}")
        except Exception as e:
            print(f"[labadmin] trino drop {cat}: {e}", flush=True)
        st, body = lh._call("GET", f"{lh._M}/catalogs/{cat}/catalog-roles", token=t)
        for r in (body or {}).get("roles", []) if st == 200 else []:
            if r["name"] != "catalog_admin":
                lh._call("DELETE", f"{lh._M}/catalogs/{cat}/catalog-roles/{r['name']}", token=t)
        lh._ok(lh._call("DELETE", f"{lh._M}/catalogs/{cat}", token=t)[0], f"delete catalog {cat}")
    lh._call("DELETE", f"{lh._M}/principals/{name}", token=t)
    lh._call("DELETE", f"{lh._M}/principal-roles/{name}", token=t)
    try:                                                 # bucket, its policy and keys
        lh._s3("HEAD", bucket).close()
        _empty_prefix(bucket, "")
        lh._s3("DELETE", bucket).close()
    except urllib.error.HTTPError:
        pass
    who = lh.storage_user(name)
    for key in (f"{who}-files", f"{who}-jobs"):         # only exist once Jupyter / a job used them
        try:
            lh._admin("DELETE", "remove-user", {"accessKey": key})
        except urllib.error.HTTPError:
            pass
    try:
        lh._admin("DELETE", "remove-canned-policy", {"name": who})
    except urllib.error.HTTPError:
        pass
    try:                                                 # SQLPad user + their Trino connection
        _sqlpad_delete(who)
    except Exception as e:
        print(f"[labadmin] sqlpad {who}: {e}", flush=True)
    u = _kc_user(user, kc)
    if u:
        _kc("DELETE", f"/admin/realms/{REALM}/users/{u['id']}", token=kc)
    lh.publish_trino_rules()
    return {"user": user, "catalogs": cats, "bucket": bucket, "jupyter_reset": jupyter}


def _sqlpad_delete(who):
    import base64
    auth = {"Authorization": "Basic " + base64.b64encode(lh.SQLPAD_ADMIN.encode()).decode()}
    _, conns = _http("GET", f"{lh.SQLPAD}/api/connections", headers=auth)
    for c in conns or []:
        if c["name"] == f"Lakehouse (Trino) — {who}":
            _http("DELETE", f"{lh.SQLPAD}/api/connections/{c['id']}", headers=auth)
    _, users = _http("GET", f"{lh.SQLPAD}/api/users", headers=auth)
    for u in users or []:
        if u["email"] == who:
            _http("DELETE", f"{lh.SQLPAD}/api/users/{u['id']}", headers=auth)
