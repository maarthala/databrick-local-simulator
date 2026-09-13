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
| Storage | **MinIO** (S3) |
| Catalog / governance | **Apache Polaris** (governed Iceberg REST catalog + per-persona RBAC) + web **Console** |
| Compute | **Spark** (master + worker), **Spark Connect**, **Trino** |
| Orchestration / apps | **Airflow**, **Jupyter**, **Superset** |
| Commodity | **Postgres**, **Redis**, an **nginx** landing page |

(Unity Catalog + Keycloak, ClickHouse, Kafka, Hive Metastore, Iceberg-REST, Hue are in
the chart but disabled by default in `k8s/helm/de-stack/values.yaml` — Polaris replaced
UC/Keycloak; flip `enabled: true` to use any of the others.)

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
| Landing page | `http://home.de.lan` | — |
| Training course | `http://home.de.lan/training/` | — |
| MinIO console | `http://minio.de.lan` | `minioadmin` / `minioadmin` |
| Polaris Console | `http://polaris-console.de.lan` | `analyst`/`engineer`/`lead` (client id = secret = name); admin `root`/`s3cr3t` |
| Polaris API | `http://polaris.de.lan` | OAuth2 client credentials (realm `POLARIS`) |
| Trino (monitor UI) | `http://trino.de.lan/ui/` | any username, no password |
| Superset | `http://superset.de.lan` | `admin` / `admin` |
| Airflow | `http://airflow.de.lan` | `airflow` / `airflow` |
| Jupyter | `http://jupyter.de.lan` | token `123456` |
| Spark master UI | `http://spark.de.lan` | — |

## 5. First steps (what to actually do)
1. **Log in as a persona** — open the Polaris Console `http://polaris-console.de.lan` and
   sign in with a client id/secret (`analyst`/`analyst`, `engineer`/`engineer`,
   `lead`/`lead`; admin `root`/`s3cr3t`). You browse the catalog *as that persona* — Polaris
   applies its grants (RBAC in action).
2. **Governed tables via Spark** — from Jupyter, `spark.sql("SHOW NAMESPACES IN iceberg")`
   shows `bronze`/`silver`/`gold` (the seeded medallion). Spark Connect reads/writes the
   Polaris-governed `iceberg` catalog; per-persona access is enforced by Polaris.
3. **Query the lake with SQL** — Trino (`iceberg` catalog) via the CLI, or Superset's SQL
   Lab (Trino → Iceberg connection is pre-configured).
4. **Manage access** — create catalogs/namespaces/principals and grant/revoke in the Polaris
   Console, or via the REST API (see `common/polaris/seed-polaris.sh` for the API calls).
5. **Schedule / notebooks** — Airflow DAGs are git-synced (read-only) from the `de-lab`
   repo; Jupyter clones the same repo and **auto-pushes every notebook save** (see below).

### Notebook auto-push (git commit + push on save)
Jupyter clones `git.repoUrl` into a writable dir and, on every save, commits + pushes the
file. Save notebooks under the repo's `notebooks/` folder. Enabled by `git.autopush: true`.

**Requirements:** the `de-stack-git-token` PAT must have **Contents: Read and write** on the
repo, and its **account must have write access** to the repo (a fine-grained PAT can't exceed
the account's repo role).

**Point it at a different account / repo:**
```bash
# 1. edit k8s/helm/de-stack/values.yaml → git.repoUrl / git.branch
#    (commit author name/email are in templates/jupyter.yaml env)

# 2. swap the token (the token = the pushing account)
kubectl -n de-stack create secret generic de-stack-git-token \
  --from-literal=token='<NEW_PAT>' --dry-run=client -o yaml | kubectl -n de-stack apply -f -

# 3. apply + restart (pod re-clones on start)
helm template de-stack k8s/helm/de-stack -s templates/jupyter.yaml | kubectl -n de-stack apply -f -
kubectl -n de-stack rollout restart deploy jupyter
```
Note: `git.repoUrl` + this secret are **shared with Airflow's DAG git-sync**, so changing
them repoints both Jupyter and Airflow.

## 6. How the custom pieces are built
Most images are stock (incl. **Apache Polaris** — `apache/polaris:latest`, no patch). The
custom ones are built from `common/dockerfiles` by the Ansible `images` role:
- **Spark** — bakes the Iceberg runtime + AWS bundle jars (`Dockerfile.spark`).
- **Jupyter** — thin Spark Connect client + notebook auto-push (`Dockerfile.jupyter`).
- **Superset**, **airflow-slim**, **home** (nginx + baked training site).

If you re-enable Unity Catalog (`unityCatalog.enabled` + `keycloak.enabled` in
`values.yaml`), its patched server/UI images are built from source — restore the
`source_images` entries in `k8s/ansible/group_vars/all.yml` (see git history) and the
runbooks in [`common/uc-server`](../common/uc-server/README.md) /
[`common/uc-ui`](../common/uc-ui/README.md).

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
