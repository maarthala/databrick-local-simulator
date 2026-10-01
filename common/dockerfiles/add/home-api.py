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
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lakehouse import POLARIS, bucket_name, lake_name, provision

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
              "lakehouse": f"{name}_lake", "bucket": bucket_name(name), "principal": name}
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
