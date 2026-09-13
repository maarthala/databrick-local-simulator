#!/usr/bin/env bash
# Jupyter entrypoint. When GIT_AUTOPUSH=1, clone (or refresh) the target repo
# into GIT_AUTOPUSH_DIR with an authenticated remote, so the post-save hook
# (jupyter_server_config.py) can commit + push every save. The token is read
# from GIT_TOKEN or, on k8s, from the file at GIT_TOKEN_FILE (mounted secret).
# Then exec Jupyter Lab.
set -uo pipefail

REPO_DIR="${GIT_AUTOPUSH_DIR:-/home/jovyan/work/repo}"

if [ "${GIT_AUTOPUSH:-0}" = "1" ] && [ -n "${GIT_REPO_URL:-}" ]; then
  TOKEN="${GIT_TOKEN:-}"
  if [ -z "$TOKEN" ] && [ -n "${GIT_TOKEN_FILE:-}" ] && [ -f "$GIT_TOKEN_FILE" ]; then
    TOKEN="$(cat "$GIT_TOKEN_FILE")"
  fi
  GIT_USER="${GIT_USERNAME:-x-access-token}"
  BRANCH="${GIT_BRANCH:-main}"
  HOSTPATH="${GIT_REPO_URL#https://}"
  if [ -n "$TOKEN" ]; then
    AUTH_URL="https://${GIT_USER}:${TOKEN}@${HOSTPATH}"
  else
    AUTH_URL="$GIT_REPO_URL"
    echo "[entrypoint] WARNING: no token found — push will only work for a public/writable remote"
  fi

  mkdir -p "$(dirname "$REPO_DIR")"
  if [ ! -d "$REPO_DIR/.git" ]; then
    echo "[entrypoint] cloning ${GIT_REPO_URL} (${BRANCH}) -> ${REPO_DIR}"
    git clone --branch "$BRANCH" "$AUTH_URL" "$REPO_DIR" \
      || echo "[entrypoint] clone failed — continuing without autopush repo"
  else
    git -C "$REPO_DIR" remote set-url origin "$AUTH_URL" || true
  fi

  if [ -d "$REPO_DIR/.git" ]; then
    git -C "$REPO_DIR" config user.name  "${GIT_AUTHOR_NAME:-notebook}"
    git -C "$REPO_DIR" config user.email "${GIT_AUTHOR_EMAIL:-notebook@de.lan}"
    git -C "$REPO_DIR" config pull.rebase true
    git -C "$REPO_DIR" checkout "$BRANCH" 2>/dev/null || true
    echo "[entrypoint] autopush ready on ${REPO_DIR} (branch ${BRANCH})"
  fi
fi

exec jupyter lab --ip=0.0.0.0 --port=8888 --no-browser \
  --IdentityProvider.token="${JUPYTER_TOKEN:-123456}" \
  --ServerApp.root_dir=/home/jovyan --ServerApp.allow_origin='*'
