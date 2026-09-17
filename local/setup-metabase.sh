#!/usr/bin/env bash
# Provision Metabase non-interactively so a fresh setup is ready to use:
#   1. create the admin account (skips the setup wizard)
#   2. add the Trino catalog connections (so you don't re-add them each rebuild)
#
#   Login (Metabase authenticates by EMAIL, not a bare username):
#     email:    admin@de.local
#     password: admin1234
#
# Both steps are idempotent (safe to re-run). Override via env vars:
#   MB_URL, MB_EMAIL, MB_PASSWORD, MB_SITE_NAME, MB_CATALOGS (space-separated),
#   MB_TRINO_HOST (default "trino"), MB_TRINO_PORT (default 8080).
#
# Usage:  bash setup-metabase.sh        (or:  make metabase-admin)
set -euo pipefail

MB_URL="${MB_URL:-http://localhost:8003}"
MB_EMAIL="${MB_EMAIL:-admin@de.local}"
MB_PASSWORD="${MB_PASSWORD:-admin1234}"
MB_SITE_NAME="${MB_SITE_NAME:-Local Lakehouse}"
MB_CATALOGS="${MB_CATALOGS:-iceberg shopflow adventureworks}"
MB_TRINO_HOST="${MB_TRINO_HOST:-trino}"     # docker/k8s service name Metabase connects to
MB_TRINO_PORT="${MB_TRINO_PORT:-8080}"      # Trino's in-container port (not the host 8007)

echo "Waiting for Metabase at $MB_URL ..."
for _ in $(seq 1 60); do
  curl -fsS "$MB_URL/api/health" >/dev/null 2>&1 && break
  sleep 3
done

# --- 1. Admin account (only creatable while the setup token exists) ---------
token="$(curl -fsS "$MB_URL/api/session/properties" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("setup-token") or "")')"

if [ -n "$token" ]; then
  payload="$(python3 - "$token" "$MB_EMAIL" "$MB_PASSWORD" "$MB_SITE_NAME" <<'PY'
import json, sys
token, email, pw, site = sys.argv[1:5]
print(json.dumps({
    "token": token,
    "user": {"first_name": "Admin", "last_name": "User",
             "email": email, "password": pw, "site_name": site},
    "prefs": {"site_name": site, "allow_tracking": False},
}))
PY
)"
  echo "Creating admin account $MB_EMAIL ..."
  curl -fsS -X POST "$MB_URL/api/setup" -H 'Content-Type: application/json' -d "$payload" >/dev/null
  echo "✅ Admin created ($MB_EMAIL / $MB_PASSWORD)"
else
  echo "✅ Metabase already set up — skipping admin creation."
fi

# --- 2. Trino catalog connections (idempotent) -----------------------------
echo "Logging in to add database connections ..."
session="$(curl -fsS -X POST "$MB_URL/api/session" -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"username":sys.argv[1],"password":sys.argv[2]}))' "$MB_EMAIL" "$MB_PASSWORD")" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("id") or "")' 2>/dev/null || true)"

if [ -z "$session" ]; then
  echo "⚠️  Could not authenticate as $MB_EMAIL — skipping connection setup."
  echo "    (Admin may already exist with a different password. Add catalogs in the UI, or set MB_PASSWORD.)"
  exit 0
fi

existing="$(curl -fsS -H "X-Metabase-Session: $session" "$MB_URL/api/database" \
  | python3 -c 'import sys,json
d=json.load(sys.stdin); rows=d.get("data",d) if isinstance(d,dict) else d
print("\n".join(x.get("name","") for x in rows))' 2>/dev/null || true)"

for cat in $MB_CATALOGS; do
  name="Trino - $cat"
  if printf '%s\n' "$existing" | grep -qxF "$name"; then
    echo "  • $name already exists — skipping"
    continue
  fi
  body="$(python3 - "$name" "$MB_TRINO_HOST" "$MB_TRINO_PORT" "$cat" <<'PY'
import json, sys
name, host, port, catalog = sys.argv[1:5]
print(json.dumps({
    "name": name, "engine": "starburst",
    "details": {"host": host, "port": int(port), "catalog": catalog,
                "user": "metabase", "ssl": False},
}))
PY
)"
  if curl -fsS -X POST "$MB_URL/api/database" -H "X-Metabase-Session: $session" \
       -H 'Content-Type: application/json' -d "$body" >/dev/null 2>&1; then
    echo "  ✅ added connection: $name  (catalog=$cat)"
  else
    echo "  ⚠️  failed to add $name (catalog may not exist yet) — skipping"
  fi
done

echo "Done. Log in at $MB_URL as $MB_EMAIL"
