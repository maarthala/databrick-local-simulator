#!/usr/bin/env bash
# Complete Metabase's first-run setup non-interactively (create the admin account),
# so you don't have to click through the setup wizard.
#
#   Login (Metabase authenticates by EMAIL, not a bare username):
#     email:    admin@de.local
#     password: admin1234
#
# Idempotent: if setup is already done (no setup token), it does nothing.
# Override via env vars: MB_URL, MB_EMAIL, MB_PASSWORD, MB_SITE_NAME.
#
# Usage:  bash setup-metabase.sh        (or:  make metabase-admin)
set -euo pipefail

MB_URL="${MB_URL:-http://localhost:8003}"
MB_EMAIL="${MB_EMAIL:-admin@de.local}"
MB_PASSWORD="${MB_PASSWORD:-admin1234}"
MB_SITE_NAME="${MB_SITE_NAME:-Local Lakehouse}"

echo "Waiting for Metabase at $MB_URL ..."
for _ in $(seq 1 60); do
  curl -fsS "$MB_URL/api/health" >/dev/null 2>&1 && break
  sleep 3
done

# The setup token is present only until first-run setup is completed.
token="$(curl -fsS "$MB_URL/api/session/properties" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("setup-token") or "")')"

if [ -z "$token" ]; then
  echo "✅ Metabase setup already completed — admin already exists. Nothing to do."
  echo "   (If you forgot the password, reset it from the Metabase UI or recreate the container.)"
  exit 0
fi

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
resp="$(mktemp)"
code="$(curl -sS -o "$resp" -w '%{http_code}' -X POST "$MB_URL/api/setup" \
  -H 'Content-Type: application/json' -d "$payload")"

if [ "$code" = "200" ] || [ "$code" = "201" ]; then
  rm -f "$resp"
  echo "✅ Admin created — log in at $MB_URL"
  echo "   email:    $MB_EMAIL"
  echo "   password: $MB_PASSWORD"
else
  echo "❌ Setup failed (HTTP $code):"
  cat "$resp"; echo; rm -f "$resp"
  exit 1
fi
