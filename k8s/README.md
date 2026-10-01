# Kubernetes setup — the governed lakehouse stack

This documents the **Kubernetes** deployment of the stack (Helm chart `k8s/helm/de-stack`),
which adds a governed **Apache Polaris** catalog (Iceberg REST + per-persona RBAC) on top
of the lakehouse. It's separate from the docker-compose stack in the root
[`Readme.md`](../Readme.md) (that one is the single-machine local version).

- **Deploy it:** [`ansible/README.md`](ansible/README.md) — one command, two paths.
- **Polaris seed:** [`common/polaris/seed-polaris.sh`](../common/polaris/seed-polaris.sh)
  (catalog, namespaces, personas, RBAC).

---

## 1. What gets deployed
Namespace `de-stack` on the cluster:

| Layer | Services |
|---|---|
| Storage | **RustFS** (S3; service name `minio`) — shared `demo-bucket` + one bucket per learner |
| Catalog / governance | **Apache Polaris** (governed Iceberg REST catalog + per-persona RBAC) + web **Console** |
| Compute | **Spark** (master + worker), **Spark Connect**, **Trino** |
| Orchestration / apps | **Airflow**, **JupyterHub** (one Jupyter pod per learner), **Superset**, **SQLPad** |
| Accounts | **Keycloak** (lab accounts, SSO for every tool), **oauth2-proxy** + **home-api** (landing page, My files, My catalogs) |
| Commodity | **Postgres**, **Redis**, an **nginx** landing page |

(Unity Catalog, ClickHouse, Kafka, Hive Metastore, Iceberg-REST, and Hue were removed —
Polaris replaced UC and the rest were unused; see git history to restore any of them.
Keycloak is back as the lab-account / single-sign-on service.)

## 2. Prerequisites
- A **MicroK8s node** with addons `ingress`, `hostpath-storage`, `metrics-server`,
  and an external Postgres reachable. (Node provisioning is out of scope here — see
  the separate `dev-setup/k8s` Ansible repo.)
- **DNS:** a wildcard `*.de.lan → <node-ip>` (a Pi-hole `address=/de.lan/<node-ip>`
  entry) so all the `*.de.lan` UIs resolve.
- **On your workstation:** `kubectl` + `helm` with `KUBECONFIG` pointing at the
  cluster (this repo assumes `~/.kube/config-de-node`), plus `docker`, `git`, and
  `ansible`.

## 3. Deploy
Use the Ansible bootstrap ([full details](ansible/README.md)). Short version:

**Local / offline node (this box)** — build images on the Mac, import to the node, deploy:
```bash
cd k8s/ansible
cp group_vars/vault.example.yml group_vars/vault.yml   # add git PAT (write scope); ansible-vault encrypt
ansible-playbook build-load.yml --ask-become-pass       # build + ctr import
ansible-playbook deploy.yml     --ask-vault-pass         # helm waves + Polaris seed
```

**Registry-based cluster** — build, push, deploy (kubelet pulls):
```bash
ansible-playbook build-load.yml --tags images
REGISTRY=ghcr.io/<you>/de-stack ./push-images.sh
ansible-playbook deploy.yml -e global_image_registry=$REGISTRY
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
| Landing page | `http://de.lan` | **lab account** (Register, or `instructor`/`instructor`) — one login for every tool |
| Keycloak (accounts) | `http://auth.de.lan/admin` | `admin` / `admin` (realm `de-lab`) |
| Training course | https://maarthala.github.io/databrick-local-simulator/ | — (linked from the landing page) |
| RustFS console | `http://minio.de.lan/rustfs/console/` | lab account (own bucket) · root `minioadmin` / `minioadmin` |
| Polaris Console | `http://polaris-console.de.lan` | lab account · `/login?local=1`: personas `analyst`/`engineer`/`lead` (id = secret = name), admin `root`/`s3cr3t` |
| Polaris API | `http://polaris.de.lan` | OAuth2 client credentials (realm `POLARIS`) |
| Trino (monitor UI) | `http://trino.de.lan/ui/` | any username, no password |
| Superset | `http://superset.de.lan` | lab account |
| SQLPad (SQL workbench) | `http://sqlpad.de.lan` | lab account |
| Airflow | `http://airflow.de.lan` | lab account |
| Jupyter (JupyterHub) | `http://jupyter.de.lan` | lab account — own Jupyter pod + own lakehouse |
| Spark master UI | `http://spark.de.lan` | — |

## 5. First steps (what to actually do)
1. **Register a lab account** at `http://de.lan` — first sign-in creates your lakehouse
   `<user>_lake`, bucket `<user>-lake` (100 MB) and SQLPad user; Jupyter starts your own pod.
2. **Governed tables via Spark** — in Jupyter, `iceberg` = your own lakehouse
   (`bronze`/`silver`/`gold`), `shared` = the course lake. Spark Connect reads/writes through
   Polaris, which enforces each learner's access.
   **Personas** (governance lessons): `http://polaris-console.de.lan/login?local=1` with
   `analyst`/`analyst`, `engineer`/`engineer`, `lead`/`lead` (admin `root`/`s3cr3t`).
3. **Query the lake with SQL** — Trino (`iceberg` catalog) via the CLI, or Superset's SQL
   Lab (Trino → Iceberg connection is pre-configured).
4. **Manage access** — create catalogs/namespaces/principals and grant/revoke in the Polaris
   Console, or via the REST API (see `common/polaris/seed-polaris.sh` for the API calls).
5. **Schedule / notebooks** — Airflow loads DAGs from the `de-lab` repo (git-sync) **and**
   from every learner's bucket `dags/` (see below).
6. **Fill the shared lake once** — trigger the `shopflow_medallion` DAG (built-in; runs the
   ShopFlow Bronze → Silver → Gold jobs over Spark Connect into `polaris_lake`). The lessons'
   ready-made tables (`shared.gold.daily_sales` in notebooks) come from it.

### Learners' notebooks and DAGs (no git needed)
Each learner's Jupyter keeps `notebooks/` and `dags/` mirrored to their own bucket
`<user>-lake`; Airflow's `learners` DAG bundle loads every bucket's `dags/` (dag_id must start
with `<user>_`). The per-learner pods don't clone the shared repo.

### Airflow git-sync
Airflow git-syncs DAGs + `src/` (read-only) from `git.repoUrl` using the `de-stack-git-token`
secret. To point it at a different repo: edit `git.repoUrl` / `git.branch` in
`k8s/helm/de-stack/values.yaml`, swap the token, then re-apply `templates/airflow.yaml`:
```bash
kubectl -n de-stack create secret generic de-stack-git-token \
  --from-literal=token='<NEW_PAT>' --dry-run=client -o yaml | kubectl -n de-stack apply -f -
helm template de-stack k8s/helm/de-stack -s templates/airflow.yaml | kubectl -n de-stack apply -f -
kubectl -n de-stack rollout restart deploy airflow
```

## 6. How the custom pieces are built
Most images are stock (incl. **Apache Polaris** — `apache/polaris:latest`, no patch). The
custom ones are built from `common/dockerfiles` by the Ansible `images` role:
- **Spark** — bakes the Iceberg runtime + AWS bundle jars (`Dockerfile.spark`).
- **Jupyter** — the per-learner image: thin Spark Connect client + bucket sync (`Dockerfile.jupyter`).
- **JupyterHub** — hub + KubeSpawner + the spawn hook (`Dockerfile.jupyterhub`).
- **home-api** — landing-page backend, provisioning, My files / My catalogs (`Dockerfile.home-api`).
- **polaris-console** — upstream console + lab SSO (`Dockerfile.polaris-console`).
- **Superset**, **airflow-slim**, **home** (nginx + baked training site).

Unity Catalog + Keycloak have been removed (Polaris is the governance). To bring them
back, restore their chart templates, `values.yaml` blocks, and the ansible
`source_images` build spec from git history.

## 7. Teardown
```bash
helm template de-stack k8s/helm/de-stack | kubectl -n de-stack delete -f - || true
kubectl delete namespace de-stack
```

## 8. Repo layout (relative to repo root)
```
k8s/helm/de-stack/    Helm umbrella chart (templates, values, config files)
k8s/ansible/          bootstrap: build-load.yml, deploy.yml, push-images.sh
common/dockerfiles/   Dockerfiles for the custom images (spark, jupyter, superset, …)
common/polaris/       seed-polaris.sh (catalog + personas + RBAC)
common/polaris-console/  Polaris Console image build
```
