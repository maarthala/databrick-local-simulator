#!/usr/bin/env bash
# Per-user Unity Catalog login via Keycloak — prints a UC access token to stdout.
#
# The Homebrew `uc` 0.6.0 CLI's `auth` command is broken (NoSuchMethodError on
# OAuth*Form.toUrlQueryString(), missing from controlapi-0.6.0.jar), so we do the
# OIDC exchange with curl and then use `uc --auth_token` for everything else.
#
# Usage:
#   export T=$(common/uc-cli/login.sh analyst)          # password defaults to username
#   export T=$(common/uc-cli/login.sh analyst s3cr3t)   # explicit password
#   uc --server http://localhost:8081 --auth_token "$T" catalog list
#
# Endpoints auto-detect: a local compose stack (localhost) when its UC is reachable,
# otherwise the k8s ingress hosts (*.de.lan). Override either with KC_URL / UC_URL.
set -euo pipefail

USER="${1:?usage: login.sh <keycloak-user> [password]}"
PASS="${2:-$USER}"

# Default endpoints — prefer a running compose stack (localhost); fall back to k8s.
if [ -z "${KC_URL:-}" ] && [ -z "${UC_URL:-}" ]; then
  if [ "$(curl -s -o /dev/null -w '%{http_code}' -m 3 \
          http://localhost:8081/api/2.1/unity-catalog/catalogs 2>/dev/null)" != "000" ]; then
    KC_URL="http://localhost:8080/realms/de-stack/protocol/openid-connect/token"
    UC_URL="http://localhost:8081"
  fi
fi
KC="${KC_URL:-http://auth.de.lan/realms/de-stack/protocol/openid-connect/token}"
UC="${UC_URL:-http://uc.de.lan:30808}"
CID="${UC_CLIENT_ID:-unity-catalog}"
SECRET="${UC_CLIENT_SECRET:-unity-catalog-secret}"

# 1. authenticate to Keycloak -> id_token
IDT=$(curl -sf -m 15 "$KC" \
  -d grant_type=password -d client_id="$CID" -d client_secret="$SECRET" \
  -d username="$USER" -d password="$PASS" -d scope="openid profile email" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id_token'])") || {
    echo "Keycloak login failed for '$USER'" >&2; exit 1; }

# 2. exchange id_token at UC -> UC access token
curl -sf -m 15 -X POST "$UC/api/1.0/unity-control/auth/tokens" \
  --data-urlencode "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  --data-urlencode "requested_token_type=urn:ietf:params:oauth:token-type:access_token" \
  --data-urlencode "subject_token_type=urn:ietf:params:oauth:token-type:id_token" \
  --data-urlencode "subject_token=$IDT" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" || {
    echo "UC token exchange failed (is '$USER' a UC user with matching email?)" >&2; exit 1; }
