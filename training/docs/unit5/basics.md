# 5.1 Airflow basics

## Concept
So far you've run each ShopFlow Spark job by hand: ingest Bronze, build Silver, build Gold
([Unit 4](../unit4/fundamentals.md)). That's fine for learning, but in production nobody sits at
a terminal at 6 a.m. to run three commands in the right order. **Orchestration** is the practice
of running data jobs *automatically*, in the *right order*, on a *schedule*, with *retries* when
things fail and *visibility* into what happened.

**Apache Airflow** is the most widely used open-source orchestrator. You describe your pipeline
**as code** and it runs it for you. The four problems it solves:

- **Dependencies** — Silver must not start until Bronze finished. Airflow enforces the order.
- **Retries** — a flaky Postgres connection shouldn't fail the whole night; Airflow retries a task.
- **Scheduling** — "run every day at 06:00" is one line, not a cron file you forget.
- **Observability** — a web UI shows every run, task, log, timing, and success/failure at a glance.

### The vocabulary
- **DAG** (Directed Acyclic Graph) — your pipeline: a set of tasks with a defined order and no
  cycles. One Python file = one (or more) DAGs.
- **Task** — a single unit of work (e.g. "run the Bronze Spark job").
- **Operator** — the *type* of a task. `BashOperator` runs a shell command, `PythonOperator` a
  Python function, `SparkSubmitOperator` a Spark job.
- **Schedule** — how often the DAG runs (`@daily`, a cron string, or `None` for manual only).
- **DAG run** — one execution of the whole DAG; each **task instance** inside it succeeds or fails
  independently.

```mermaid
flowchart LR
  subgraph DAG["DAG (your pipeline as code)"]
    A[Task A<br/>operator] --> B[Task B<br/>operator]
  end
  SCHED[Scheduler<br/>@daily] -.triggers.-> DAG
  DAG -.logs + status.-> UI[Web UI]
```

## Lab

### 1. Open the Airflow UI
ShopFlow's Airflow is already running on your stack (see the
[architecture](../unit0/architecture.md)).

- Local: <http://localhost:8001> (login `airflow` / `airflow`)
- On k8s: <http://airflow.de.lan>

Take the tour:

- **DAGs** list — every pipeline, its schedule, and last run status. The toggle on the left
  enables/disables (pauses) scheduling.
- Click a DAG → **Graph** shows tasks and dependencies; **Grid** shows every run as a column and
  every task as a row (green = success, red = failed, yellow = running/retry).
- Click any task square → **Logs** to see exactly what happened.
- The **▶ Trigger** button runs a DAG on demand.

### 2. Write your first DAG
DAGs live in the **dags folder** — `code/airflow/dags/` in the compose stack (git-synced from the
`de-lab` repo on Kubernetes). That folder is the *same* `/code` mount **JupyterLab** uses, so the
container-free way to author a DAG is to create/edit the file right in JupyterLab's file browser
(<http://localhost:8008>) — no container shell needed. Add `code/airflow/dags/hello_shopflow.py`:

```python
from airflow.sdk import DAG                                    # Airflow 3.x
from airflow.providers.standard.operators.bash import BashOperator
import pendulum

with DAG(
    dag_id="hello_shopflow",
    description="First tiny DAG — two tasks in order",
    schedule=None,                    # manual only for now
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["unit5", "demo"],
) as dag:

    say_hello = BashOperator(
        task_id="say_hello",
        bash_command="echo 'ShopFlow pipeline starting…'",
    )

    show_run = BashOperator(
        task_id="show_run",
        bash_command="echo 'Run id is {{ run_id }}'",
    )

    # define the dependency: say_hello must finish before show_run
    say_hello >> show_run
```

`{{ run_id }}` is a **template** — Airflow fills it in at run time. Templating is how tasks become
run-aware.

!!! note "`{{ run_id }}` vs `{{ ds }}` — the business date"
    You'll often want the run's **business date**, written `{{ ds }}` (`YYYY-MM-DD`). But that only
    exists for **scheduled** runs — it comes from the run's *logical date*. A **manual** trigger in
    Airflow 3 has no logical date, so `{{ ds }}` would be undefined here; that's why this first DAG
    uses `{{ run_id }}`. You'll use `{{ ds }}` for the real daily pipeline in [5.3](schedule.md).

### 3. Run it
Airflow rescans the folder every ~30s. In the UI:

1. Find **hello_shopflow** in the DAGs list and toggle it **on** (unpause).
2. Click **▶ Trigger**.
3. Open **Grid** → you should see two green squares. Click `show_run` → **Logs** and confirm it
   printed the run id.

Everything here — authoring, triggering, watching, reading logs — happens in the **browser**
(the Airflow UI, and JupyterLab for the file). You never open a shell inside a container.

## Challenge
Add a third task `count_dags` that runs *after* `show_run` and prints how many DAG files are in the
dags folder. Wire the order `say_hello >> show_run >> count_dags`.

??? note "Solution"
    ```python
    count_dags = BashOperator(
        task_id="count_dags",
        bash_command="ls /code/airflow/dags/*.py | wc -l",
    )

    say_hello >> show_run >> count_dags
    ```
    Chaining with `>>` scales to any number of tasks — in the Graph view you'll now see three boxes
    connected left to right. (The command reads the mounted dags folder, so it needs no extra tools.)

!!! tip "🎯 The same orchestration on Azure, Databricks, Snowflake & Fabric"
    **What you just did:** described a pipeline as a DAG of tasks wired with `>>`, then triggered
    and inspected it in the Airflow UI.

    - **Azure Data Factory** — a DAG is a **Pipeline**; tasks are **activities**; your `>>` is a
      success arrow; `schedule=` is a **Schedule trigger**; Grid/Graph is **ADF Monitor**.
    - **Azure Databricks** — a **Workflow/Job**: multiple tasks with dependencies, schedules,
      retries, and alerts built in.
    - **Snowflake** — chain **Tasks** with `AFTER` predecessors to form a task graph (DAG).
    - **Microsoft Fabric** — **Data Factory in Fabric** pipelines: the same activity-and-dependency
      model.

    The *concepts* — DAG, task, dependency, schedule, retry — are identical everywhere, and
    **Airflow itself runs managed on all of them** (ADF Managed Airflow, Amazon MWAA, Google Cloud
    Composer), so *this exact DAG* ports almost unchanged.

## Key terms, at a glance
| Term | Plain meaning |
|---|---|
| **Orchestration** | Run jobs automatically, in order, on a schedule, with retries |
| **DAG** | Your pipeline as code — tasks with a defined order, no cycles |
| **Task / task instance** | A unit of work / one run of it |
| **Operator** | The *type* of task (`BashOperator`, `SparkSubmitOperator`, …) |
| **Schedule** | `@daily` / cron / `None` — how often the DAG runs |
| **DAG run** | One execution of the whole DAG |
| **`>>`** | "then" — defines task dependency/order |
| **Template (`{{ … }}`)** | Value filled in at run time (`run_id`, `ds`, …) |

## You can now…
- Explain what orchestration is and the four problems it solves
- Name the core Airflow objects: DAG, task, operator, schedule, DAG run
- Write, trigger, and inspect a multi-task DAG in the Airflow UI
- Use templating (`{{ run_id }}`) and know when `{{ ds }}` applies
