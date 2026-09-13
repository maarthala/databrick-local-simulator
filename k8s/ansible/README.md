# de-stack bootstrap (Ansible)

Reproduce the whole environment. Two playbooks, so it fits both a locked-down node
(copy images in) and a normal cluster (pull from a registry):

- **`build-load.yml`** — build custom + patched images on the Mac and `ctr import`
  them into the node's containerd. For nodes that can't pull large images (this
  MicroK8s-on-LXC box).
- **`deploy.yml`** — helm deploy (ordered waves) + seed Polaris. Works either
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
  -e global_image_registry=$REGISTRY
```
(If you re-enable Unity Catalog, also pass `-e uc_image=…` / `-e uc_ui_image=…`.)

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
First build is slow — it builds the Spark/Jupyter/Superset/Airflow/home images (the Spark
image is large). Re-runs are fast: builds hit the docker layer cache. (No source builds
for the default Polaris stack; those only run if you re-enable Unity Catalog.)

Tags let you run one phase: `--tags images|load|secrets|deploy|seed`.

## What each phase does
| Phase | Where | Action |
|---|---|---|
| **images** | Mac | `init.sh` (fetch base jars) → build `spark/jupyter/superset/airflow-slim/home` → `docker save` (plus UC server/UI source builds only if `source_images` is set) |
| **load** | node | copy tarballs → `microk8s ctr images import` (sudo) → clean up |
| **secrets** | Mac | create the `de-stack-git-token` secret from the vault |
| **deploy** | Mac | `helm template … \| kubectl apply` in waves — commodity → catalog (Polaris) → compute → apps — waiting for readiness between each |
| **seed** | Mac | wait for Polaris + its bootstrap Job, then run `common/polaris/seed-polaris.sh` (catalog, bronze/silver/gold namespaces, analyst/engineer/lead personas, graded RBAC) via a port-forward |

## Config
Everything is in `group_vars/all.yml` — image matrix, deploy waves, and the Polaris seed
settings (`polaris_seed_script`, `polaris_local_port`). `source_images` is empty for the
Polaris stack (set it to build the patched UC images if you re-enable UC).

## Caveats
- **First container start after import can be very slow / wedge** on a large image (the
  3.68GB Spark image saturates this LXC's disk; 3 concurrent unpacks can time out with a
  stuck container-name reservation). No-sudo fix: scale `spark-worker`/`spark-connect` to
  0, let `spark-master` unpack alone, `kubectl delete` any stuck pod, then scale back —
  they reuse the cached layers. (Or, with sudo on the node:
  `sudo systemctl restart snap.microk8s.daemon-containerd`.)
- Copying multi-GB tarballs uses the `copy` module (works, but slow). For speed,
  install `ansible.posix` and switch the load role to `synchronize` (rsync).
- Public images (postgres, redis, minio, trino, apache/polaris) are pulled by the kubelet
  — only the custom images are built + imported here.
- Personas log in with client id = secret = name (`analyst`/`analyst`, …); admin is
  `root`/`s3cr3t`. The **demo/medallion tables** are built by the course pipeline, not the
  seed.
