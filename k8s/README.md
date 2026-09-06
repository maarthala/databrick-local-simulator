# Kubernetes setup — the governed lakehouse stack

This documents the **Kubernetes** deployment of the stack (Helm chart `k8s/helm/de-stack`),
which adds a governed Unity Catalog + single-sign-on on top of the lakehouse. It's
separate from the docker-compose stack in the root [`Readme.md`](../Readme.md) (that one
is the single-machine local version).

- **Deploy it:** [`ansible/README.md`](ansible/README.md) — one command, two paths.
- **Tool guides:** [`common/uc-cli`](../common/uc-cli/README.md) ·
  [`common/uc-spark`](../common/uc-spark/README.md) ·
  [`common/uc-server`](../common/uc-server/README.md) ·
  [`common/uc-ui`](../common/uc-ui/README.md)

---

## 1. What gets deployed
Namespace `de-stack` on the cluster:

| Layer | Services |
|---|---|
| Storage | **MinIO** (S3) |
| Catalogs | **Iceberg REST** (the lake) · **Unity Catalog** server + web UI (governance) |
| Identity | **Keycloak** (OIDC / single sign-on) |
| Compute | **Spark** (master + worker), **Spark Connect**, **Trino** |
| Orchestration / apps | **Airflow**, **Jupyter**, **Superset** |
| Commodity | **Postgres**, **Redis**, an **nginx** landing page |

(ClickHouse, Kafka, Hive Metastore, Hue are in the chart but disabled by default in
`k8s/helm/de-stack/values.yaml` — flip `enabled: true` to use them.)

## 2. Prerequisites
- A **MicroK8s node** with addons `ingress`, `hostpath-storage`, `metrics-server`,
  and an external Postgres reachable. (Node provisioning is out of scope here — see
  the separate `dev-setup/k8s` Ansible repo.)
- **DNS:** a wildcard `*.de.lan → <node-ip>` (a Pi-hole `address=/de.lan/<node-ip>`
  entry) so all the `*.de.lan` UIs resolve.
- **On your workstation:** `kubectl` + `helm` with `KUBECONFIG` pointing at the
  cluster (this repo assumes `~/.kube/config-de-node`), plus `docker`, `git`,
  `ansible`, and the `uc` CLI (`brew install unitycatalog`).

## 3. Deploy
Use the Ansible bootstrap ([full details](ansible/README.md)). Short version:

**Local / offline node (this box)** — build images on the Mac, import to the node, deploy:
```bash
cd k8s/ansible
cp group_vars/vault.example.yml group_vars/vault.yml   # add git PAT; ansible-vault encrypt
ansible-playbook build-load.yml --ask-become-pass       # build + ctr import
ansible-playbook deploy.yml     --ask-vault-pass         # helm waves + UC seed
```

**Registry-based cluster** — build, push, deploy (kubelet pulls):
```bash
ansible-playbook build-load.yml --tags images
REGISTRY=ghcr.io/<you>/de-stack ./push-images.sh
ansible-playbook deploy.yml -e global_image_registry=$REGISTRY \
  -e uc_image=$REGISTRY/unity-catalog:vendflat -e uc_ui_image=$REGISTRY/unity-catalog-ui:kcflat
```

Manual (no Ansible) — deploy the whole chart at once:
```bash
kubectl create namespace de-stack
kubectl -n de-stack create secret generic de-stack-git-token --from-literal=token=<PAT>
helm template de-stack k8s/helm/de-stack | kubectl -n de-stack apply -f -
```

## 4. Access
All UIs are at `https?://<name>.de.lan`. Default credentials (change for anything real):

| Service | URL | Login |
|---|---|---|
| Landing page | `http://home.de.lan` | — |
| Training course | `http://home.de.lan/training/` | — |
| MinIO console | `http://minio.de.lan` | `minioadmin` / `minioadmin` |
| Keycloak | `http://auth.de.lan` | `admin` / `admin` |
| Unity Catalog UI | `http://uc-ui.de.lan` | `analyst` / `engineer` / `lead` (password = username; Keycloak) |
| Unity Catalog API | `http://uc.de.lan:30808` | bearer token (`uc` CLI) |
| Trino (monitor UI) | `http://trino.de.lan/ui/` | any username, no password |
| Superset | `http://superset.de.lan` | `admin` / `admin` |
| Airflow | `http://airflow.de.lan` | `airflow` / `airflow` |
| Jupyter | `http://jupyter.de.lan` | token `123456` |
| Spark master UI | `http://spark.de.lan` | — |

## 5. First steps (what to actually do)
1. **Log in as a user** — open `http://uc-ui.de.lan`, "Continue with Keycloak", sign in
   as `analyst`. You see only what analyst is granted (RBAC in action).
2. **Manage the catalog with the CLI** — [`common/uc-cli`](../common/uc-cli/README.md):
   ```bash
   export T=$(common/uc-cli/login.sh analyst)
   uc --server http://uc.de.lan:30808 --auth_token "$T" catalog list
   ```
   Create catalogs/schemas and grant/revoke access with `uc catalog|schema create` and
   `uc permission create` (see the CLI guide).
3. **Governed tables via Spark** — [`common/uc-spark`](../common/uc-spark/README.md): create
   a Delta table in `lakehouse.sales`, then watch RBAC — analyst can `SELECT`, engineer is denied.
4. **Query the lake with SQL** — Trino (`iceberg` catalog) via the CLI, or Superset's SQL
   Lab (Trino → Iceberg connection is pre-configured).
5. **Schedule / notebooks** — Airflow DAGs + Jupyter (Spark Connect) run shared code
   git-synced from the `de-lab` repo.

## 6. How the custom pieces are built
Most images are stock. The non-trivial ones are built from source with small patches,
each with its own runbook:
- **Unity Catalog server** — patched for MinIO static credential vending
  ([`common/uc-server`](../common/uc-server/README.md)).
- **UC web UI** — patched to add Keycloak login over http
  ([`common/uc-ui`](../common/uc-ui/README.md)).
- **Spark image** — bakes the UC connector jars (`common/dockerfiles/Dockerfile.spark`
  + `common/dockerfiles/uc-jars/`).

The Ansible `images` role builds all of these automatically.

## 7. Teardown
```bash
helm template de-stack k8s/helm/de-stack | kubectl -n de-stack delete -f - || true
kubectl delete namespace de-stack
```

## 8. Repo layout (relative to repo root)
```
k8s/helm/de-stack/    Helm umbrella chart (templates, values, config files)
k8s/ansible/          bootstrap: build-load.yml, deploy.yml, push-images.sh
common/dockerfiles/   Dockerfiles for the custom images (+ uc-jars/)
common/uc-server, common/uc-ui   Unity Catalog server + UI image patches
common/uc-cli, common/uc-spark   runtime helper scripts
```
