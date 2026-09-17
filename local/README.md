# Local setup (Docker Compose)

The **governed lakehouse** on a single machine with Docker Compose — the same stack
as [`../k8s/README.md`](../k8s/README.md), just on localhost instead of a cluster.

## What runs
MinIO · **Apache Polaris** (governed Iceberg catalog) + web **Console** · Spark
(master + worker + Connect) · Trino · Superset · Airflow · Jupyter · Postgres · Redis ·
an nginx landing page. Postgres also hosts the **AdventureWorks** OLTP sample DB
(see below).

## Prerequisites
- **Docker** + **Docker Compose** v2.
- The custom images (spark, jupyter, superset, airflow, home) are **built by
  `make up`**; the rest (polaris, trino, minio, postgres, redis) are stock and pulled.

## Run
```bash
cp .env.example .env   # first time: create your env (gitignored); set GIT_TOKEN to enable notebook auto-push
make init   # first time: download base JARs (into ../common/dockerfiles/tmp)
make docs   # build the training course site (../training -> ../training/site)
make up     # build the compose images + start everything
make ps     # status      make logs S=polaris     make down   # stop + remove volumes
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
| Polaris Console | http://localhost:8189 | analyst/engineer/lead (client id = secret = name); admin root/s3cr3t |
| Polaris API | http://localhost:8185 | OAuth2 client credentials (realm `POLARIS`) |
| Trino | http://localhost:8007/ui/ | any username, no password |
| Superset | http://localhost:8004 | admin / admin |
| Airflow | http://localhost:8001 | airflow / airflow |
| Jupyter | http://localhost:8008 | token `123456` |
| Spark master UI | http://localhost:8002 | — |

## First steps
Seed the governed catalog (catalog, bronze/silver/gold namespaces, personas + RBAC):
```bash
make polaris-seed      # runs ../common/polaris/seed-polaris.sh against localhost:8185
```
Then:
- **Log in** to the Polaris Console at http://localhost:8189 as a persona
  (`analyst`/`analyst`, `engineer`/`engineer`, `lead`/`lead`; admin `root`/`s3cr3t`).
- **Query the lake** with Trino (`iceberg` catalog) or Superset SQL Lab.
- **Governed Spark** — from Jupyter, `spark.sql("SHOW NAMESPACES IN iceberg")` lists
  `bronze`/`silver`/`gold`; Spark Connect reads/writes the Polaris-governed catalog.

## Notebook auto-push (git commit + push on save)
Jupyter clones a repo into `/home/jovyan/work/repo` and, on every save, commits + pushes
the file. Save notebooks under the repo's `notebooks/` folder. Config is in
`local/jupyter.yaml` (`GIT_REPO_URL`, `GIT_BRANCH`, `GIT_AUTHOR_NAME/EMAIL`).

Config lives in **`local/.env`** (copy from `.env.example`; `.env` is gitignored, so the
token never lands in git):
```bash
cp .env.example .env         # first time
# edit .env → set GIT_TOKEN (the pushing account; needs Contents: Read+Write on the repo)
#   quick fill: GIT_TOKEN=$(gh auth token)
make up                      # or: docker compose up -d --force-recreate jupyter
```
Blank `GIT_TOKEN` = auto-push disabled. To switch account/repo: edit `GIT_REPO_URL` /
`GIT_TOKEN` in `.env`, delete the stale clone, and recreate:
```bash
docker exec jupyter rm -rf /home/jovyan/work/repo
docker compose up -d --force-recreate jupyter
```

## AdventureWorks sample database
The full **AdventureWorks OLTP** sample (68 tables across `person`, `sales`, `production`,
`purchasing`, `humanresources`) is loaded into the local Postgres as the `adventureworks`
database — handy for richer SQL practice than ShopFlow.

**How it's wired:**
- `make init` downloads the Microsoft OLTP CSVs + the community Postgres port and fixes the
  CSVs (needs **`ruby`** — ships with macOS). Data is staged under
  `init_scripts/postgres/adventureworks/` (gitignored, ~110 MB).
- On the **first** `make up`, `init_scripts/postgres/03_adventureworks.sh` creates the
  `adventureworks` DB and loads it.
- Query it from **Trino / Superset** via the `adventureworks` catalog, or directly:
  ```bash
  docker exec -it postgres psql -U postgres -d adventureworks -c \
    "select top 5 firstname, lastname from person.person;"    # (or a normal LIMIT query)
  # Trino:
  docker exec -it trino trino --execute "SELECT count(*) FROM adventureworks.sales.salesorderheader"
  ```

⚠️ It only loads on a **fresh Postgres volume** (init scripts run once). If Postgres already
has a volume, reload with: `make down` (removes volumes) → `make init` → `make up`.
If `ruby` is missing at `make init`, the prep is skipped and the stack still starts — just
without the `adventureworks` DB.

## Notes
- Governance (Polaris per-persona RBAC + MinIO credential vending) is validated in
  compose and works the same as on k8s.
