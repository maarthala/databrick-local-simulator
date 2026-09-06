# Local setup (Docker Compose)

The **governed lakehouse** on a single machine with Docker Compose — the same stack
as [`../k8s/README.md`](../k8s/README.md), just on localhost instead of a cluster.

## What runs
MinIO · Iceberg REST · **Unity Catalog** + web UI · **Keycloak** (SSO) · Spark
(master + worker) · Trino · Superset · Airflow · Jupyter · Postgres · an nginx
landing page.

## Prerequisites
- **Docker** + **Docker Compose** v2.
- **The patched Unity Catalog images built locally** (`unitycatalog/unitycatalog:vendflat`
  and `unitycatalog/unitycatalog-ui:kcflat`) — compose consumes them as pre-built
  refs. Build all custom images with the shared builder:
  ```bash
  cd ../k8s/ansible && ansible-playbook build-load.yml --tags images   # builds on the Mac, no cluster needed
  ```
  (or follow the runbooks in [`../common/uc-server`](../common/uc-server/README.md) and
  [`../common/uc-ui`](../common/uc-ui/README.md)).
- **One hosts entry** so the browser and the containers resolve the Keycloak issuer
  identically (the compose analog of the k8s `*.de.lan` wildcard):
  ```
  # add to /etc/hosts
  127.0.0.1 keycloak
  ```

## Run
```bash
make init   # first time: download base JARs (into ../common/dockerfiles/tmp)
make docs   # build the training course site (../training -> ../training/site)
make up     # build the compose images + start everything
make ps     # status      make logs S=unity-catalog     make down   # stop + remove volumes
```

The **hands-on Data Engineering course** ([`../training`](../training)) is served by the
landing page at **http://localhost:8000/training/**. Run `make docs` to (re)build it
after editing the Markdown under `training/docs/`.

## Access
| Service | URL | Login |
|---|---|---|
| Landing page | http://localhost:8000 | — |
| Training course | http://localhost:8000/training/ | — |
| MinIO console | http://localhost:9001 | minioadmin / minioadmin |
| Keycloak | http://keycloak:8080 | admin / admin |
| Unity Catalog UI | http://localhost:3000 | analyst / engineer / lead (password = username; Keycloak) |
| Unity Catalog API | http://localhost:8081 | bearer token (`uc` CLI) |
| Trino | http://localhost:8007/ui/ | any username, no password |
| Superset | http://localhost:8004 | admin / admin |
| Airflow | http://localhost:8001 | airflow / airflow |
| Jupyter | http://localhost:8008 | token `123456` |
| Spark master UI | http://localhost:8002 | — |

## First steps
Seed the catalog + users (fresh Unity Catalog starts with only an admin):
```bash
ADMIN=$(docker exec unity-catalog cat etc/conf/token.txt)
docker exec unity-catalog bin/uc --auth_token "$ADMIN" user create --name "Ava Analyst" --email analyst@dev-epireum.com
docker exec unity-catalog bin/uc --auth_token "$ADMIN" catalog create --name lakehouse
docker exec unity-catalog bin/uc --auth_token "$ADMIN" schema  create --catalog lakehouse --name sales
# grant analyst, etc. — see ../common/uc-cli/README.md
```
Then:
- **Log in** at http://localhost:3000 → "Continue with Keycloak" → analyst/analyst.
- **Query the lake** with Trino (`iceberg` catalog) or Superset SQL Lab.
- **CLI** against `http://localhost:8081`:
  `UC_URL=http://localhost:8081 KC_URL=http://keycloak:8080/realms/de-stack/protocol/openid-connect/token ../common/uc-cli/login.sh analyst`

## Notes
- The Keycloak↔Unity Catalog governance (OIDC + per-user RBAC + MinIO credential
  vending) is validated in compose and works the same as k8s.
- The legacy Northwind/Kafka streaming scenario and its challenges (`Tasks.md`) were
  removed when the stack was standardized on the governed lakehouse; `Tasks.md` is
  kept for reference only.
