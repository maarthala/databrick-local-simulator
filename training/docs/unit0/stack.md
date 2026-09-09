# 0.7 Stack architecture

Unit **0** showed *how data flows*. This page is the **deployment map**: every service
that runs, what it's for, how the pieces are wired, where state lives, and how the
same stack runs on **Docker Compose** (one machine) and **Kubernetes** (a cluster).

## The whole stack at a glance

```mermaid
flowchart TB
  USER([👩‍💻 You<br/>browser · Trino CLI])

  subgraph EDGE["Access — one entry per tool"]
    HOME[home<br/>landing portal]
  end

  subgraph GOV["Governance"]
    PX[polaris-proxy<br/>same-origin front]
    PC[polaris-console<br/>web UI]
    POL[Apache Polaris<br/>Iceberg REST catalog + RBAC]
    PX --> PC
    PX --> POL
    PC --> POL
  end

  subgraph ENG["Query & compute engines"]
    TR[Trino<br/>SQL engine]
    SM[spark-master] --- SW[spark-worker]
    SC[spark-connect<br/>remote sessions]
  end

  subgraph ORCH["Orchestration & work"]
    AF[Airflow<br/>apiserver · scheduler · dag-processor]
    JUP[Jupyter<br/>notebooks]
    SUP[Superset<br/>dashboards]
  end

  subgraph DATA["State — storage"]
    MIN[(MinIO<br/>lakehouse + raw files)]
    PGS[(Postgres<br/>source DB + metastores)]
    RDS[(Redis<br/>Superset cache)]
  end

  USER --> HOME
  USER --> TR & SUP & JUP & PX

  TR -->|catalog + creds| POL
  SC -->|catalog + creds| POL
  AF -->|spark-submit| SM
  JUP --> SC
  SUP -->|SQL| TR

  POL -->|persist| PGS
  POL -->|vends S3 creds for| MIN
  TR --> MIN
  SM --> MIN
  SC --> MIN
  TR -->|source| PGS
  AF --> PGS
  SUP --> PGS & RDS
```

Everything points at **two stores** (MinIO for tables, Postgres for the source + metadata),
with **Polaris** as the single catalog that every engine consults before touching a table.

## Components

### Storage — where state lives
| Service | What it is | Holds |
|---|---|---|
| **MinIO** | S3-compatible object store — the lakehouse | Iceberg tables (`demo-bucket/…`) **and** raw history as Parquet |
| **Postgres** | One relational DB serving several roles | the **`shopflow`** source OLTP data; **metastores** for Polaris (`polarisdb`), Airflow, Superset |
| **Redis** | In-memory store | **Superset's** cache & async query results (Airflow uses LocalExecutor — no broker needed) |

### Governance — one catalog for all engines
| Service | What it is |
|---|---|
| **Apache Polaris** | The Iceberg **REST catalog** + **RBAC**. Engines ask it "does this principal may read/write this table?", and it **vends short-lived MinIO credentials** for the ones allowed. Metadata persists to Postgres (`polarisdb`). |
| **polaris-console** | The catalog's **web UI** (a single-page app) — browse catalogs/namespaces/tables, manage principals, roles, and grants. |
| **polaris-proxy** | A tiny nginx front that serves the Console at `/` and proxies the API at `/api` on **one origin** (`:8189`), so the browser makes no cross-origin calls. *(On k8s the ingress does this same-origin routing instead.)* |
| **polaris-bootstrap** | A **one-shot** job that creates Polaris's schema + realm in Postgres on first start. Runs once, then exits. |

### Engines — SQL and Spark
| Service | What it is |
|---|---|
| **Trino** | Distributed **SQL engine**. Catalogs: **`iceberg`** (→ Polaris, the lakehouse), **`shopflow`** (→ Postgres source), `system`. Connects to Polaris as admin — it's the broad-access engine for the SQL units. |
| **spark-master** | Standalone Spark **cluster manager** — schedules jobs onto workers. |
| **spark-worker** | The **executor** — runs the actual Spark tasks. |
| **spark-connect** | A long-running **Spark Connect** server so notebooks/clients get a remote Spark session without bundling Spark themselves. |

### Orchestration & work
| Service | What it is |
|---|---|
| **Airflow** | **Schedules** the pipeline (the `shopflow_medallion` DAG runs Bronze→Silver→Gold via `spark-submit`). Three processes: **apiserver** (UI/API), **scheduler**, **dag-processor**. Metadata in Postgres; **LocalExecutor**. On k8s, DAGs + shared `src/` arrive by **git-sync**. |
| **Jupyter** | **Notebooks** for exploration and the Spark labs — wired to Spark Connect and the `iceberg` catalog. |
| **Superset** | **BI dashboards** on the Gold layer — queries via Trino, caches in Redis, stores its own metadata in Postgres. |
| **home** | The **landing portal** (nginx) — one page linking every UI. Start here. |

## Access & ports

On **Compose** each tool publishes a `localhost` port; on **Kubernetes** each is an
ingress host `http://<tool>.de.lan`. Same services, same logins.

| Tool | Compose URL | k8s host | Login |
|---|---|---|---|
| Home portal | http://localhost:8000 | `home.de.lan` | — |
| Polaris Console | http://localhost:8189 | `polaris-console.de.lan` | `root` / `s3cr3t` (or a persona) |
| Polaris API | http://localhost:8185 | `polaris.de.lan` | client id/secret |
| Trino | http://localhost:8007/ui/ | `trino.de.lan` | any user, no password |
| Superset | http://localhost:8004 | `superset.de.lan` | `admin` / `admin` |
| Jupyter | http://localhost:8008 | `jupyter.de.lan` | token `123456` |
| Airflow | http://localhost:8001 | `airflow.de.lan` | `airflow` / `airflow` |
| MinIO console | http://localhost:9001 | `minio.de.lan` | `minioadmin` / `minioadmin` |
| Spark master UI | http://localhost:8002 | `spark.de.lan` | — |

Internal wiring uses service names on a shared network: `polaris:8181`, `minio:9000`,
`postgres:5432`, `spark://spark-master:7077`, `sc://spark-connect:15002`.

## Persistence

State survives restarts; only a deliberate teardown wipes it.

- **MinIO volume** — all lakehouse tables + raw files.
- **Postgres volume** — source data + every metastore (incl. Polaris' `polarisdb`, so the
  catalog, principals, and grants persist).
- **Spark / Jupyter** working dirs and Superset's home.

On Compose these are named Docker volumes; on k8s they're PersistentVolumeClaims
(`microk8s-hostpath`). `make down` (Compose) removes volumes — use `stop` to keep data.

## Compose vs. Kubernetes

| | **Docker Compose** | **Kubernetes** (MicroK8s) |
|---|---|---|
| Unit | containers on the `sparknet` network | pods in namespace `de-stack` |
| Reach a UI | `localhost:<port>` | nginx **ingress** at `*.de.lan` |
| Code/DAGs | bind-mounted from `local/code` | **git-sync** of the shared repo (DAGs + `src/`) |
| Images | built/pulled locally | imported to the node (`microk8s images import`) |
| Config | compose files + `configs/` | Helm chart `de-stack` (values + templates) |
| Postgres | a stack container | in-cluster Postgres |

Pick the tab that matches your setup on the [deploy page](../setup/deploy.md) — the
lakehouse, the catalog, and the lessons are identical either way.

## What's intentionally *not* running

The stack is trimmed to the **governed lakehouse** set. These are present in the repo
but disabled by default (re-enable if a lesson needs them):

- **Unity Catalog** — an alternative catalog we evaluated; **paused** in favour of Polaris (revisit later).
- **Keycloak** — an external SSO/identity server; **dropped** for training (principals log in with a client id/secret; an IdP is the production path).
- **iceberg-rest** — the earlier ungoverned catalog; **folded into Polaris** (one catalog now).
- **Kafka / Kafka-Connect / Kafka-UI, ClickHouse, Hive Metastore, Hue** — not needed for this course's batch/lakehouse focus.

## You can now…
- Name **every service** in the stack and what it's responsible for
- Explain how engines reach data: **catalog via Polaris**, **bytes via MinIO**, gated by **grants**
- Say **where state lives** (MinIO + Postgres) and what survives a restart
- Describe how the **same stack** maps from Docker Compose to Kubernetes
