"""home-api — the landing page's tiny backend (behind oauth2-proxy).

GET /api/me  → who is logged in (from the headers oauth2-proxy sets after the Keycloak
               login) and, on first call, provisions that learner's own lakehouse in
               Polaris: catalog <name>_lake (bronze/silver/gold), principal <name>,
               principal-role <name> owning the catalog, plus read access to the shared
               lake. Idempotent — every step accepts "already exists" (409).

"My files" — the learner's OWN bucket <name>-lake only. The bucket always comes from
the logged-in user; nothing from the browser can point at another bucket.
  GET    /api/files?prefix=a/b/            one folder level (folders, files, is-table)
  GET    /api/files/download?key=…          download a file
  PUT    /api/files/upload?key=…            upload (raw body, streamed)
  POST   /api/files/mkdir?prefix=a/new/     new folder
  DELETE /api/files?key=…                   delete a file
  DELETE /api/files/folder?prefix=…[&confirm_table=1]  delete a folder (tables need confirm)

"My catalogs" — catalogs the learner owns or that are shared with them; create a catalog
<name>_<x> (stored in their bucket); share a namespace/table with another learner
(read / write) and revoke. Polaris enforces the access; ownership is checked here.
  GET    /api/catalogs                                   owned + shared-with-me
  POST   /api/catalogs?name=sales                        create <user>_sales
  GET    /api/catalogs/tree?catalog=…                    namespaces + tables (owner)
  GET    /api/catalogs/shares?catalog=…                  who has what (owner)
  POST   /api/catalogs/shares?catalog&grantee&access&namespace[&table]
  DELETE /api/catalogs/shares?catalog=…&role=…           revoke

Only reachable through oauth2-proxy (it is not published), so the identity headers can
be trusted. Standard library only.
"""
import json
import os
import threading
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import lakehouse as lh
from lakehouse import POLARIS, bucket_name, lake_name, provision

MAX_UPLOAD = int(os.environ.get("MAX_UPLOAD_MB", "512")) * 1024 * 1024


class _Body:
    """The request body as a file that ends after Content-Length bytes (the socket
    itself stays open for keep-alive, so reading it to EOF would hang)."""
    def __init__(self, f, length):
        self.f, self.left = f, length

    def read(self, n=-1):
        if self.left <= 0:
            return b""
        n = self.left if n is None or n < 0 else min(n, self.left)
        chunk = self.f.read(n)
        self.left -= len(chunk)
        return chunk

_ready = set()            # learners already provisioned since start (skip the API calls)
_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- helpers ------------------------------------------------------------------
    def _user(self):
        return self.headers.get("X-Forwarded-Preferred-Username") or self.headers.get("X-Forwarded-User")

    def _route(self):
        u = urllib.parse.urlparse(self.path)
        return u.path, {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}

    def _instructor(self):
        groups = (self.headers.get("X-Forwarded-Groups") or "").split(",")
        return "instructors" in groups

    def _ensure(self, name):
        with _lock:
            if name not in _ready:
                provision(name, instructor=self._instructor())
                _ready.add(name)

    @staticmethod
    def _clean(key):
        key = (key or "").lstrip("/")
        if not key or any(part == ".." for part in key.split("/")):
            raise ValueError("bad path")
        return key

    def _files(self, method):
        """All /api/files* calls. Bucket = the logged-in learner's own, always."""
        path, q = self._route()
        user = self._user()
        if not user:
            return self._json(401, {"error": "not logged in"})
        name = lake_name(user)
        bucket = bucket_name(name)
        try:
            self._ensure(name)
            if method == "GET" and path == "/api/files":
                prefix = (q.get("prefix") or "").lstrip("/")
                folders, files = lh.list_dir(bucket, prefix)
                kids = {f[len(prefix):] for f in folders}
                return self._json(200, {
                    "bucket": bucket, "prefix": prefix,
                    "is_table": {"metadata/", "data/"} <= kids or "metadata/" in kids,
                    "folders": [{"name": f[len(prefix):].rstrip("/"), "prefix": f} for f in folders],
                    "files": [dict(f, name=f["key"][len(prefix):]) for f in files]})
            if method == "GET" and path == "/api/files/download":
                key = self._clean(q.get("key"))
                with lh.get_object(bucket, key) as r:
                    self.send_response(200)
                    self.send_header("Content-Type", r.headers.get("Content-Type", "application/octet-stream"))
                    self.send_header("Content-Length", r.headers.get("Content-Length", "0"))
                    fname = urllib.parse.quote(key.rsplit("/", 1)[-1])
                    self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{fname}")
                    self.end_headers()
                    while chunk := r.read(1 << 16):
                        self.wfile.write(chunk)
                return
            if method == "PUT" and path == "/api/files/upload":
                key = self._clean(q.get("key"))
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_UPLOAD:
                    return self._json(413, {"error": f"file larger than {MAX_UPLOAD >> 20} MB"})
                try:
                    lh.put_object(bucket, key, _Body(self.rfile, length), length,
                                  self.headers.get("Content-Type") or "application/octet-stream")
                except urllib.error.HTTPError as e:
                    msg = e.read().lower()
                    if b"quota exceeded" in msg:
                        return self._json(413, {"error": f"Your bucket is full — the limit is "
                                                         f"{lh.QUOTA_MB} MB. Delete files you no longer need."})
                    if b"quota check temporarily unavailable" in msg:   # brand-new bucket, not scanned yet
                        return self._json(503, {"error": "Your storage is still being prepared — "
                                                         "try the upload again in a few seconds."})
                    raise
                return self._json(200, {"uploaded": key, "path": f"s3a://{bucket}/{key}"})
            if method == "POST" and path == "/api/files/mkdir":
                prefix = self._clean(q.get("prefix")).rstrip("/") + "/"
                import io
                lh.put_object(bucket, prefix, io.BytesIO(b""), 0)
                return self._json(200, {"created": prefix})
            if method == "DELETE" and path == "/api/files":
                key = self._clean(q.get("key"))
                lh.delete_object(bucket, key)
                return self._json(200, {"deleted": key})
            if method == "DELETE" and path == "/api/files/folder":
                prefix = self._clean(q.get("prefix")).rstrip("/") + "/"
                keys = lh.list_all(bucket, prefix)
                if lh.is_table(keys) and q.get("confirm_table") != "1":
                    return self._json(409, {"table": True, "error":
                        "This folder is an Iceberg table — drop it with SQL (DROP TABLE … PURGE) instead."})
                for k in keys:
                    lh.delete_object(bucket, k)
                return self._json(200, {"deleted": len(keys), "prefix": prefix})
            return self._json(404, {"error": "not found"})
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        except urllib.error.HTTPError as e:
            return self._json(404 if e.code == 404 else 502, {"error": f"storage: HTTP {e.code}"})
        except Exception as e:                       # show it on the page, don't crash
            return self._json(500, {"error": str(e)})

    def _catalogs(self, method):
        """All /api/catalogs* calls — always on behalf of the logged-in learner."""
        path, q = self._route()
        user = self._user()
        if not user:
            return self._json(401, {"error": "not logged in"})
        name = lake_name(user)
        try:
            self._ensure(name)
            if method == "GET" and path == "/api/catalogs":
                return self._json(200, lh.my_catalogs(name))
            if method == "POST" and path == "/api/catalogs":
                return self._json(200, lh.create_catalog(name, (q.get("name") or "").strip().lower()))
            if method == "GET" and path == "/api/catalogs/tree":
                return self._json(200, lh.catalog_tree(name, q.get("catalog", "")))
            if method == "GET" and path == "/api/catalogs/shares":
                return self._json(200, lh.list_shares(name, q.get("catalog", "")))
            if method == "POST" and path == "/api/catalogs/shares":
                return self._json(200, lh.share(name, q.get("catalog", ""), q.get("grantee", "").strip(),
                                                q.get("access", "read"), q.get("namespace", ""), q.get("table") or None))
            if method == "DELETE" and path == "/api/catalogs/shares":
                lh.revoke(name, q.get("catalog", ""), q.get("role", ""))
                return self._json(200, {"revoked": q.get("role")})
            return self._json(404, {"error": "not found"})
        except PermissionError as e:
            return self._json(403, {"error": str(e)})
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        except Exception as e:
            return self._json(500, {"error": str(e)})

    def _dispatch(self, method):
        if self.path.startswith("/api/catalogs"):
            return self._catalogs(method)
        return self._files(method)

    def do_PUT(self):
        return self._dispatch("PUT")

    def do_POST(self):
        return self._dispatch("POST")

    def do_DELETE(self):
        return self._dispatch("DELETE")

    def do_GET(self):
        if self.path == "/api/health":
            return self._json(200, {"ok": True})
        if self.path.startswith("/api/files"):
            return self._files("GET")
        if self.path.startswith("/api/catalogs"):
            return self._catalogs("GET")
        if self.path != "/api/me":
            return self._json(404, {"error": "not found"})
        user = self._user()
        if not user:
            return self._json(401, {"error": "not logged in"})
        h = self.headers
        name = lake_name(user)
        me = {"user": user, "email": h.get("X-Forwarded-Email", ""),
              # oauth2-proxy's keycloak provider adds roles as "role:…" — keep real groups only
              "groups": [g for g in (h.get("X-Forwarded-Groups") or "").split(",") if g and not g.startswith("role:")],
              "lakehouse": f"{name}_lake", "bucket": bucket_name(name), "principal": name,
              "quota_mb": lh.QUOTA_MB,
              "airflow_port": os.environ.get("AIRFLOW_HOST_PORT", "")}
        try:
            self._ensure(name)
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
