# Databrick Local Simulator

A hands-on Data Engineering learning environment — a **governed lakehouse**
(MinIO, Iceberg, Unity Catalog, Keycloak SSO, Spark, Trino, Superset, Airflow,
Jupyter) that you can run two ways with the **same stack**:

## 📚 Training course

Read the hands-on **Data Engineering course** online — build the ShopFlow
Bronze→Silver→Gold lakehouse and map every skill to Databricks, Snowflake & Fabric:

**→ [maarthala.github.io/databrick-local-simulator](https://maarthala.github.io/databrick-local-simulator/)**

Start with **Prerequisites & setup** and **Bring up the stack**, then work through the units.
(The same course is also served by the running stack at `http://localhost:8000/training/`.)

## Setup — pick your environment

### 🖥️ [Local (Docker Compose)](./local/README.md)
Run the whole governed lakehouse on a single machine with Docker Compose.
Fastest to start; great for learning and offline use.
→ **[local/README.md](./local/README.md)**

### ☸️ [Kubernetes](./k8s/README.md)
The same stack on a MicroK8s/Kubernetes cluster via a Helm umbrella chart, with a
one-command Ansible bootstrap (build-and-import for locked-down nodes, or pull from
a registry for bigger clusters).
→ **[k8s/README.md](./k8s/README.md)**

## Repository layout
```
local/    Docker Compose stack + its setup, config, and challenges (Tasks.md)
k8s/      Helm chart (k8s/helm) + Ansible bootstrap (k8s/ansible)
common/   Shared by both: Dockerfiles for the custom images, Unity Catalog
          image patches (uc-server, uc-ui), and helper tools (uc-cli, uc-spark)
```

Both environments deploy the **same governed-lakehouse component set** and are
self-contained (each runs its own Postgres). What differs is only the orchestrator
(Compose vs Kubernetes) and the hostnames (localhost ports vs `*.de.lan` ingress).
