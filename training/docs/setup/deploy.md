# Bring up the stack

This page is for **whoever runs the platform** — you on your laptop (Docker Compose) or an operator
on a cluster (Kubernetes). If someone already runs the stack for you and gave you URLs, you don't
need this — go straight to [Prerequisites](prerequisites.md) (browser + `keycloak` hosts entry + the
Trino CLI) and start learning.

!!! info "Two ways to run the *same* stack"
    The lakehouse is identical either way — same services, same course. **Docker Compose** runs it
    all on one machine (the normal choice for learning). **Kubernetes** runs it on a cluster (closer
    to production). Pick the tab that matches your setup.

=== "Local (Docker Compose)"

    ### Prerequisites
    - **Docker Desktop** (≥ 8 GB RAM allocated — 12–16 GB is comfortable) and **Git**
      — see [Prerequisites → run the stack yourself](prerequisites.md#4-running-the-stack-yourself-only-if-it-isnt-provided).
    - The **`keycloak` hosts entry** (`127.0.0.1 keycloak`) —
      [why & how](prerequisites.md#2-the-keycloak-hosts-entry-required).
    - **Ansible** (once, to build the two patched Unity Catalog images the compose stack consumes).

    ### Steps
    ```bash
    # 0. get the repo
    git clone https://github.com/maarthala/databrick-local-simulator.git
    cd databrick-local-simulator

    # 1. first time only: build the patched Unity Catalog images (built on your Mac, no cluster needed)
    (cd k8s/ansible && ansible-playbook build-load.yml --tags images)

    # 2. bring it up (all commands run from local/)
    cd local
    make init      # first run only: download base JARs into ../common/dockerfiles/tmp
    make docs      # build the training course site (../training -> ../training/site)
    make up        # build the compose images + start every service
    make uc-seed   # provision the governed 'shopflow' catalog + personas (needed for Unit 6)
    ```

    ### Verify
    ```bash
    make ps                       # all services should be "running"/"healthy"
    ```
    Open the landing page at **<http://localhost:8000>** — every tool tiles off it. Then run the
    [setup checklist](prerequisites.md#verify-your-setup).

    ### Day-to-day
    | Command | What it does |
    |---|---|
    | `make ps` | show running services |
    | `make logs` (`make logs S=trino`) | tail logs (all, or one service) |
    | `make docs` | rebuild the course site after editing `training/docs/**` |
    | `make restart` | `down` then `up` |
    | `make down` | **stop the stack and remove volumes** (wipes data) |
    | `make clean` | remove the images built for this stack |

    !!! warning "`make down` deletes the volumes"
        It runs `docker compose down -v`, so MinIO data, Postgres, and the catalog are wiped. Use it
        for a clean reset; use `docker compose stop` if you only want to pause and keep your data.

=== "Kubernetes"

    Deploying to a cluster is an **operator** task (more moving parts than Compose). The canonical
    guide is [`k8s/README.md`](https://github.com/maarthala/databrick-local-simulator/blob/main/k8s/README.md)
    and [`k8s/ansible/README.md`](https://github.com/maarthala/databrick-local-simulator/blob/main/k8s/ansible/README.md);
    the essentials are below.

    ### Prerequisites
    - A **Kubernetes cluster** (this repo targets MicroK8s) with the `ingress`,
      `hostpath-storage`, and `metrics-server` addons, plus an external **Postgres** reachable.
    - **Wildcard DNS** `*.de.lan → <node-ip>` so all the `*.de.lan` UIs resolve.
    - On your workstation: **`kubectl`**, **`helm`**, **`ansible`**, **`docker`**, **`git`**, and the
      **`uc` CLI** (`brew install unitycatalog`), with `KUBECONFIG` pointed at the cluster.

    ### Steps — Ansible (recommended)
    ```bash
    cd k8s/ansible
    cp group_vars/vault.example.yml group_vars/vault.yml   # add a git PAT, then: ansible-vault encrypt group_vars/vault.yml
    ansible-playbook build-load.yml --ask-become-pass       # build the custom images + import them to the node
    ansible-playbook deploy.yml     --ask-vault-pass         # helm install (in waves) + seed the governed catalog
    ```

    ??? note "Manual (no Ansible) — deploy the whole chart at once"
        ```bash
        kubectl create namespace de-stack
        kubectl -n de-stack create secret generic de-stack-git-token --from-literal=token=<PAT>
        helm template de-stack k8s/helm/de-stack | kubectl -n de-stack apply -f -
        # then seed governance with the uc CLI (see common/uc-cli/README.md)
        ```

    ### Verify
    ```bash
    kubectl -n de-stack get pods         # wait for everything to be Running/Ready
    ```
    Open the landing page at **`http://home.de.lan`**. All UIs live at `http(s)://<name>.de.lan`
    (jupyter, trino, superset, airflow, spark, minio, auth, uc-ui) — the landing page links them.

    ### Teardown
    ```bash
    helm template de-stack k8s/helm/de-stack | kubectl -n de-stack delete -f - || true
    kubectl delete namespace de-stack
    ```

## After it's up
- Sign in as one of the [personas](personas.md) (`analyst` / `engineer` / `lead`) to see governance
  in action.
- The training course itself is served **by the stack** at `/(training)/` on the landing page
  (`http://localhost:8000/training/` locally, `http://home.de.lan/training/` on k8s).

## You can now…
- Bring the whole stack up with Docker Compose (`make up` + `make uc-seed`) or on Kubernetes (Ansible)
- Verify every service is running and reach the landing page
- Tear it down / reset cleanly, and know which command wipes data
