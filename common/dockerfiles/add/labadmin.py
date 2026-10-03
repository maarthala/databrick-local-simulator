"""labadmin — the platform manager's toolkit. Runs inside the home-api container (it already
holds the Polaris / storage / SQLPad admin logins); the Keycloak admin login is passed in as
KEYCLOAK_ADMIN=user:password for the one call (local: admin:admin).

  python /app/labadmin.py list                       learners, their lakehouse and bucket use
  python /app/labadmin.py create <user> [password]   new lab account + lakehouse, ready to use
  python /app/labadmin.py password <user> [password] new password (changed at the next sign-in)
  python /app/labadmin.py reset-lakehouse <user>     drop every table in the learner's catalogs
                                                     (bronze/silver/gold + sample table come back)
  python /app/labadmin.py wipe <user>                reset-lakehouse + empty their bucket
                                                     (starter files come back)
  python /app/labadmin.py delete <user> --yes        remove the account and everything it owns

No password given → a random one is printed. Accounts, catalogs and shares are kept by
reset-lakehouse / wipe. Wrappers: `make learner-…` (local), k8s/lab-admin.sh (Kubernetes).
"""
import inspect
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

import lakehouse as lh

KEYCLOAK = os.environ.get("KEYCLOAK_URL", "http://keycloak:8080")
REALM = os.environ.get("KEYCLOAK_REALM", "de-lab")
USERNAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}$")
_C = "/api/catalog/v1"


# ---- Keycloak (admin REST API) ----------------------------------------------------------
def _kc(method, path, body=None, token=None, form=None):
    headers, data = {}, None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(KEYCLOAK + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200]


def _kc_token():
    user, pw = os.environ.get("KEYCLOAK_ADMIN", "admin:admin").split(":", 1)
    st, body = _kc("POST", "/realms/master/protocol/openid-connect/token", form={
        "grant_type": "password", "client_id": "admin-cli", "username": user, "password": pw})
    if st != 200:
        sys.exit(f"Keycloak admin login failed (HTTP {st}) — check KEYCLOAK_ADMIN")
    return body["access_token"]


def _kc_user(user, t):
    st, body = _kc("GET", f"/admin/realms/{REALM}/users?" +
                   urllib.parse.urlencode({"username": user, "exact": "true"}), token=t)
    return body[0] if st == 200 and body else None


def _password(pw):
    return pw or secrets.token_urlsafe(9)


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


def _clear_catalog(cat, t):
    """Drop every table and view in `cat`; drop namespaces other than bronze/silver/gold."""
    dropped = 0
    for ns in _namespaces(cat, t):
        p = f"{_C}/{cat}/namespaces/{_ns_path(ns)}"
        for kind in ("views", "tables"):          # files: removed from the bucket afterwards
            st, body = lh._call("GET", f"{p}/{kind}", token=t)
            for ident in (body or {}).get("identifiers", []) if st == 200 else []:
                name = urllib.parse.quote(ident["name"], safe="")
                lh._ok(lh._call("DELETE", f"{p}/{kind}/{name}", token=t)[0],
                       f"drop {cat}.{'.'.join(ns)}.{ident['name']}")
                dropped += 1
        if ns not in [[n] for n in lh.NAMESPACES]:
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


def _empty_prefix(bucket, prefix):
    keys = lh.list_all(bucket, prefix)
    for k in keys:
        lh.delete_object(bucket, k)
    return len(keys)


# ---- commands ---------------------------------------------------------------------------
def cmd_list():
    t, kc = lh._admin_token(), _kc_token()
    st, users = _kc("GET", f"/admin/realms/{REALM}/users?max=500", token=kc)
    print(f"{'user':<20} {'lakehouse':<24} {'catalogs':>8} {'bucket MB':>9}")
    for u in sorted(users or [], key=lambda u: u["username"]):
        name = lh.lake_name(u["username"])
        try:
            cats = _owned_catalogs(name, t)
        except RuntimeError:
            cats = []
        try:
            mb = sum(int(o["size"]) for o in _sizes(lh.bucket_name(name))) / 1e6
            size = f"{mb:9.1f}"
        except Exception:
            size = f"{'—':>9}"
        lake = f"{name}_lake" if f"{name}_lake" in cats else "— (not signed in yet)"
        print(f"{u['username']:<20} {lake:<24} {len(cats):>8} {size}")


def _sizes(bucket):
    import xml.etree.ElementTree as ET
    out, token = [], None
    while True:
        q = {"list-type": "2"}
        if token:
            q["continuation-token"] = token
        with lh._s3("GET", bucket, query=q) as r:
            root = ET.fromstring(r.read())
        out += [{"size": c.findtext(f"{lh._NS}Size")} for c in root.findall(f"{lh._NS}Contents")]
        token = root.findtext(f"{lh._NS}NextContinuationToken")
        if root.findtext(f"{lh._NS}IsTruncated") != "true":
            return out


def cmd_create(user, pw=None):
    if not USERNAME.match(user):
        sys.exit("username: 2-31 of a-z, 0-9, - (starting with a letter or digit)")
    kc, pw = _kc_token(), _password(pw)
    if _kc_user(user, kc):
        sys.exit(f"{user} already exists — use `password` to give them a new one")
    st, body = _kc("POST", f"/admin/realms/{REALM}/users", {
        "username": user, "enabled": True,
        "credentials": [{"type": "password", "value": pw, "temporary": True}]}, token=kc)
    if st != 201:
        sys.exit(f"create {user} in Keycloak: HTTP {st} {body!r}")
    lh.provision(lh.lake_name(user))
    lh.publish_trino_rules()
    print(f"created {user}: lakehouse {lh.lake_name(user)}_lake, bucket {lh.bucket_name(lh.lake_name(user))}")
    print(f"first-sign-in password (they choose a new one): {pw}")


def cmd_password(user, pw=None):
    kc, pw = _kc_token(), _password(pw)
    u = _kc_user(user, kc)
    if not u:
        sys.exit(f"no lab account {user}")
    st, body = _kc("PUT", f"/admin/realms/{REALM}/users/{u['id']}/reset-password",
                   {"type": "password", "value": pw, "temporary": True}, token=kc)
    if st != 204:
        sys.exit(f"reset password: HTTP {st} {body!r}")
    print(f"{user}: new password (they choose their own at the next sign-in): {pw}")


def _reset(user, prefix):
    """Drop every table/view in the learner's catalogs, empty `prefix` of their bucket, then
    re-provision (bronze/silver/gold, starter files, sample table)."""
    name, t = lh.lake_name(user), lh._admin_token()
    cats = _owned_catalogs(name, t)
    if not cats:
        sys.exit(f"{user} has no lakehouse yet (never signed in)")
    for c in cats:
        lh.trino_catalog(c, t)                    # makes sure trino_lab holds its grant
    ct = _content_token()
    dropped = sum(_clear_catalog(c, ct) for c in cats)
    files = _empty_prefix(lh.bucket_name(name), prefix)
    lh.provision(name)
    return cats, dropped, files


def cmd_reset_lakehouse(user):
    cats, dropped, files = _reset(user, "tables/")
    print(f"{user}: {dropped} table(s)/view(s) dropped in {', '.join(cats)}; {files} table file(s) removed")


def cmd_wipe(user):
    cats, dropped, files = _reset(user, "")
    print(f"{user}: {dropped} table(s)/view(s) dropped in {', '.join(cats)}; bucket emptied "
          f"({files} file(s)), starter files restored")


def _best_effort(what, fn):
    try:
        fn()
    except Exception as e:
        print(f"  ({what}: {e})")


def _sqlpad(method, path):
    import base64
    auth = "Basic " + base64.b64encode(lh.SQLPAD_ADMIN.encode()).decode()
    r = urllib.request.Request(lh.SQLPAD + path, method=method, headers={"Authorization": auth})
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read() or b"null")


def cmd_delete(user, confirm=None):
    if confirm != "--yes":
        sys.exit(f"this removes {user}'s account, catalogs, tables and bucket — add --yes")
    name, t, kc = lh.lake_name(user), lh._admin_token(), _kc_token()
    bucket, cats = lh.bucket_name(name), _owned_catalogs(name, t)
    ct = _content_token() if cats else None
    for cat in cats:                                     # tables, namespaces, roles, catalog
        lh.trino_catalog(cat, t)
        _clear_catalog(cat, ct)
        for ns in lh.NAMESPACES:
            lh._call("DELETE", f"{_C}/{cat}/namespaces/{ns}", token=ct)
        _best_effort(f"trino {cat}", lambda: lh._trino(f"DROP CATALOG IF EXISTS {cat}"))
        st, body = lh._call("GET", f"{lh._M}/catalogs/{cat}/catalog-roles", token=t)
        for r in (body or {}).get("roles", []) if st == 200 else []:
            if r["name"] != "catalog_admin":
                lh._call("DELETE", f"{lh._M}/catalogs/{cat}/catalog-roles/{r['name']}", token=t)
        lh._ok(lh._call("DELETE", f"{lh._M}/catalogs/{cat}", token=t)[0], f"delete catalog {cat}")
    lh._call("DELETE", f"{lh._M}/principals/{name}", token=t)
    lh._call("DELETE", f"{lh._M}/principal-roles/{name}", token=t)
    if _bucket_exists(bucket):                           # bucket, its policy and keys
        _empty_prefix(bucket, "")
        _best_effort("bucket", lambda: lh._s3("DELETE", bucket).close())
    who = lh.storage_user(name)
    for key in (f"{who}-files", f"{who}-jobs"):         # only exist once Jupyter / a job used them
        try:
            lh._admin("DELETE", "remove-user", {"accessKey": key})
        except urllib.error.HTTPError:
            pass
    _best_effort("storage policy", lambda: lh._admin("DELETE", "remove-canned-policy", {"name": who}))
    def sqlpad():                                        # SQLPad user + their Trino connection
        for c in _sqlpad("GET", "/api/connections"):
            if c["name"] == f"Lakehouse (Trino) — {who}":
                _sqlpad("DELETE", f"/api/connections/{c['id']}")
        for u in _sqlpad("GET", "/api/users"):
            if u["email"] == who:
                _sqlpad("DELETE", f"/api/users/{u['id']}")
    _best_effort("sqlpad", sqlpad)
    u = _kc_user(user, kc)
    if u:
        _kc("DELETE", f"/admin/realms/{REALM}/users/{u['id']}", token=kc)
    lh.publish_trino_rules()
    print(f"{user}: deleted (account, {len(cats)} catalog(s), bucket {bucket})")


def _bucket_exists(bucket):
    try:
        lh._s3("HEAD", bucket).close()
        return True
    except urllib.error.HTTPError:
        return False


COMMANDS = {"list": cmd_list, "create": cmd_create, "password": cmd_password,
            "reset-lakehouse": cmd_reset_lakehouse, "wipe": cmd_wipe, "delete": cmd_delete}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    fn, args = COMMANDS[sys.argv[1]], sys.argv[2:]
    try:
        inspect.signature(fn).bind(*args)
    except TypeError:
        sys.exit(__doc__)
    fn(*args)
