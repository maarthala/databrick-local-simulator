# de-stack bootstrap (Ansible)

Reproduce the whole environment. Two playbooks, so it fits both a locked-down node
(copy images in) and a normal cluster (pull from a registry):

- **`build-load.yml`** — build custom + patched images on the Mac and `ctr import`
  them into the node's containerd. For nodes that can't pull large images (this
  MicroK8s-on-LXC box).
- **`deploy.yml`** — helm deploy (ordered waves) + seed Unity Catalog. Works either
  way: `imagePullPolicy: IfNotPresent` means the kubelet uses a **locally-present**
  image if it's there, otherwise **pulls from the registry**.
- **`push-images.sh`** — publish all custom/patched images to a registry, for
  bigger environments that pull directly (no `ctr import`).
- `site.yml` — convenience wrapper: `build-load.yml` + `deploy.yml` in one run.

## Two paths

**A) Local / offline node (this box)** — build + import, then deploy:
```bash
ansible-playbook build-load.yml --ask-become-pass      # build on Mac + ctr import
ansible-playbook deploy.yml     --ask-vault-pass       # helm + seed (uses local images)
# or both at once:  ansible-playbook site.yml --ask-become-pass --ask-vault-pass
```

**B) Registry-based cluster** — build, push, then deploy (kubelet pulls):
```bash
ansible-playbook build-load.yml --tags images          # build only (no import)
REGISTRY=ghcr.io/<you>/de-stack ./push-images.sh       # publish to your registry
ansible-playbook deploy.yml --ask-vault-pass \
  -e global_image_registry=$REGISTRY \
  -e uc_image=$REGISTRY/unity-catalog:vendflat \
  -e uc_ui_image=$REGISTRY/unity-catalog-ui:kcflat
```

## Prerequisites
- **On the Mac (control node):** `ansible`, `docker`, `helm`, `kubectl`, `git`,
  and `KUBECONFIG` at `~/.kube/config-de-node` pointing at the cluster.
- **The node already exists** — MicroK8s up with `ingress`, `hostpath-storage`,
  `metrics-server`; the `*.de.lan` Pi-hole wildcard; external postgres reachable.
  (Node provisioning lives in the separate `dev-setup/k8s` Ansible repo — run that first.)
- **SSH + sudo** to `sysadmin@192.168.1.201` (Ansible `become` handles the sudo for
  `ctr import`).

## One-time setup
```bash
cd k8s/ansible
cp group_vars/vault.example.yml group_vars/vault.yml
# put your git-sync PAT in vault.yml, then encrypt it:
ansible-vault encrypt group_vars/vault.yml
```

## Notes on speed
First build is slow — it builds the Spark/Jupyter/Superset/Airflow images and does a
full **UC + UI source build** (sbt). Re-runs are fast: image builds hit the docker
layer cache, and the from-source images are **skipped if already built**.

Tags let you run one phase: `--tags images|load|secrets|deploy|seed`.

## What each phase does
| Phase | Where | Action |
|---|---|---|
| **images** | Mac | `init.sh` (fetch base jars) → build `spark/jupyter/superset/airflow-slim` → build+patch **UC server** (`unitycatalog:vendflat`) and **UI** (`unitycatalog-ui:kcflat`) from source → flatten → `docker save` |
| **load** | node | copy tarballs → `microk8s ctr images import` (sudo) → clean up |
| **secrets** | Mac | create the `de-stack-git-token` secret from the vault |
| **deploy** | Mac | `helm template … \| kubectl apply` in waves — commodity → catalog/identity → compute → apps — waiting for readiness between each |
| **seed** | Mac | create UC users (analyst/engineer/lead), the `lakehouse.sales` catalog/schema, and grants |

## Config
Everything is in `group_vars/all.yml` — image matrix, the pinned UC commit + which
`tools/*` patches to apply, the deploy waves, and the UC seed (users/grants).

## Caveats
- **First container start after import can wedge** this node's containerd on a large
  image. If a pod is stuck in `ContainerCreating`, run once on the node:
  `sudo systemctl restart snap.microk8s.daemon-containerd`, then re-run `--tags deploy`.
- Copying multi-GB tarballs uses the `copy` module (works, but slow). For speed,
  install `ansible.posix` and switch the load role to `synchronize` (rsync).
- Public images (postgres, redis, minio, trino, keycloak, iceberg-rest) are pulled
  by the kubelet — only the custom/patched images are built + imported here.
- The **demo table** isn't auto-created (it's the lesson); make it with
  `common/uc-spark/` after seeding.
