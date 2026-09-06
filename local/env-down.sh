#!/usr/bin/env bash
# Stop the stack and remove volumes.
# The list of compose files lives once in .env (COMPOSE_FILE). Run from repo root.
set -e
docker compose down -v
