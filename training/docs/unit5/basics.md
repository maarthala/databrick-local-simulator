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

### What an orchestrator does
Back in [Unit 1.1](../unit1/what-is-de.md) we said a pipeline is just "steps that turn raw data into
useful data." An **orchestrator** is the thing that *runs those steps for you* so you don't have to
babysit them. Concretely it does four jobs:

- **Runs steps in the right order** — Bronze, then Silver, then Gold. You declare the order once;
  the orchestrator never runs Silver before Bronze finishes.
- **On a schedule** — "every day at 06:00", or "every hour", declared in one line. No human at a
  terminal, no crontab to hand-maintain.
- **With retries** — if a step fails on a transient hiccup (a dropped connection), the orchestrator
  can automatically try it again a few times before giving up and alerting you.
- **With backfills** — if the pipeline was down for three days, an orchestrator can *catch up* by
  running the missed days one by one. (We'll meet this as **catchup** below and use it for real in
  [5.3](schedule.md).)

Everything in this lesson is a concrete instance of one of those four jobs. Keep them in mind as
the vocabulary below gives each one a name.

### The vocabulary
Five words carry this whole lesson. Read them once here; you'll see each one appear in real code in
the Lab.

- **DAG** (Directed Acyclic Graph) — your pipeline. It's a set of **tasks** with a defined order.
  *Directed* = the arrows point one way (Bronze → Silver, never back). *Acyclic* = no loops, so the
  pipeline always finishes. In Airflow, **one Python file defines one (or more) DAGs** — the file
  *is* the pipeline.
- **Task** — a single unit of work, one box in the graph (e.g. "run the Bronze Spark job", or here,
  "echo a message").
- **Operator** — the *type* of a task, i.e. *what kind of work* it does. `BashOperator` runs a shell
  command, `PythonOperator` runs a Python function, `SparkSubmitOperator` submits a Spark job. You
  pick an operator, give it parameters, and that becomes a task.
- **Schedule** — how often the DAG runs (`@daily`, a cron string, or `None` for "manual only, I'll
  press the button myself").
- **DAG run** — **one execution of the whole DAG** — one pass through all its tasks for one point in
  time. Inside a run, each task becomes a **task instance** that succeeds or fails *independently*,
  so you can retry just the one that broke instead of rerunning everything.

!!! info "How the UI shows a run: colored squares"
    Airflow's **Grid** view is a table: **each DAG run is a column**, **each task is a row**, and
    every cell is a colored square showing that task instance's **state** — green = success, red =
    failed, yellow = running or retrying, grey = not started yet. One glance tells you which run,
    and which task inside it, went wrong. Click a square to jump to that task's **Logs**.

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

This one file is a complete pipeline. It's short on purpose — two trivial tasks that just print
text — so you can see the *shape* of every DAG without any real logic in the way. Read the whole
thing first, then we'll walk it line by line.

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

**Read it step by step:**

- **`from airflow.sdk import DAG`** — imports the `DAG` class. In **Airflow 3.x** this lives in
  `airflow.sdk` (older tutorials import `from airflow import DAG` — that's the 2.x style; use the
  `sdk` one here).
- **`from airflow.providers.standard.operators.bash import BashOperator`** — imports the operator
  we'll use. `BashOperator` is a task that runs a shell command. Operators ship in *provider*
  packages; the Bash one lives in the `standard` provider.
- **`import pendulum`** — a date/time library Airflow uses. We only need it to build a proper
  timezone-aware `start_date` below.
- **`with DAG(...) as dag:`** — this **defines the DAG**. The `with … as dag:` block is a Python
  context manager: every task you create *inside* the indented block automatically belongs to this
  DAG. The arguments configure the pipeline:
    - **`dag_id="hello_shopflow"`** — the DAG's unique name. This is exactly what you'll see in the
      DAGs list in the UI, so make it descriptive.
    - **`description=...`** — a one-line summary shown next to the DAG in the UI.
    - **`schedule=None`** — how often to run automatically. `None` means **manual only** — it never
      runs on its own; you press ▶ Trigger. (In [5.3](schedule.md) you'll change this to a real
      daily schedule.)
    - **`start_date=pendulum.datetime(2026, 1, 1, tz="UTC")`** — the date the DAG becomes
      "eligible" to run. Every DAG needs one, even a manual one. It's the *earliest* logical date
      Airflow will consider — think of it as the pipeline's birthday, not "run now."
    - **`catchup=False`** — when you *do* have a schedule, `catchup` controls **backfilling**: if
      the `start_date` is in the past, should Airflow run *every* missed interval to catch up?
      `False` says "no, don't run history, just go forward from now." Leaving it `True` on a DAG with
      an old `start_date` is the classic beginner surprise — it fires off dozens of runs at once. We
      keep it `False` here.
    - **`tags=["unit5", "demo"]`** — labels for filtering the DAGs list. Purely cosmetic.
- **`say_hello = BashOperator(task_id="say_hello", bash_command="echo …")`** — creates the **first
  task**. `task_id` is the task's name (what you see as a box in the Graph and a row in the Grid);
  `bash_command` is the shell command it runs. Because this is written inside the `with DAG` block,
  the task is automatically attached to the DAG.
- **`show_run = BashOperator(...)`** — the **second task**, same pattern. Its command prints
  `{{ run_id }}` (explained just below).
- **`say_hello >> show_run`** — this is the whole point: **`>>` defines the dependency (the order)**.
  Read it as "`say_hello` **then** `show_run`" — Airflow will not start `show_run` until
  `say_hello` has succeeded. The arrow you'll see between the two boxes in the Graph view *is* this
  line.

!!! note "Nothing here 'runs' when you save the file"
    Saving `hello_shopflow.py` doesn't execute any echo. This file is a **definition** — it *builds
    the graph* (which tasks exist, in what order). The commands only run later, inside a **DAG run**,
    when the scheduler or your ▶ Trigger click actually executes each task. Defining the pipeline
    and running it are two separate moments.

`{{ run_id }}` is a **template** — Airflow fills it in at run time. Templating is how tasks become
run-aware.

!!! note "`{{ run_id }}` vs `{{ ds }}` — the business date"
    You'll often want the run's **business date**, written `{{ ds }}` (`YYYY-MM-DD`). But that only
    exists for **scheduled** runs — it comes from the run's *logical date*. A **manual** trigger in
    Airflow 3 has no logical date, so `{{ ds }}` would be undefined here; that's why this first DAG
    uses `{{ run_id }}`. You'll use `{{ ds }}` for the real daily pipeline in [5.3](schedule.md).

### 3. Run it
You wrote the *definition*; now trigger an actual **DAG run** and watch the task instances turn
green. Airflow rescans the dags folder every ~30s, so give it a moment after saving to appear. In
the UI:

1. Find **hello_shopflow** in the DAGs list and toggle it **on** (unpause).
2. Click **▶ Trigger**.
3. Open **Grid** → you should see two green squares. Click `show_run` → **Logs** and confirm it
   printed the run id.

Everything here — authoring, triggering, watching, reading logs — happens in the **browser**
(the Airflow UI, and JupyterLab for the file). You never open a shell inside a container.

!!! tip "Why tasks should be idempotent"
    Because an orchestrator **retries** failed tasks and can **backfill** past days, the same task
    may run more than once for the same date. A task is **idempotent** when running it twice gives
    the same result as running it once — e.g. "overwrite today's Silver partition" rather than
    "append rows" (which would double them). Idempotent tasks are what make retries and backfills
    *safe*. Our echo tasks are trivially idempotent; you'll design the real Spark jobs this way in
    [5.3](schedule.md).

## Challenge
Add a third task `count_dags` that runs *after* `show_run` and prints how many DAG files are in the
dags folder. Wire the order `say_hello >> show_run >> count_dags`. You're doing two things: making a
third `BashOperator`, and extending the dependency chain so the new task runs last.

??? note "Solution"
    ```python
    count_dags = BashOperator(
        task_id="count_dags",
        bash_command="ls /code/airflow/dags/*.py | wc -l",
    )

    say_hello >> show_run >> count_dags
    ```
    **Read it step by step:**

    - **`count_dags = BashOperator(...)`** — a third task, same pattern as before. Its
      `bash_command` lists the `.py` files in the dags folder and pipes the list to `wc -l` to
      count the lines (one per file).
    - **`say_hello >> show_run >> count_dags`** — chaining `>>` reads left to right as
      "`say_hello`, **then** `show_run`, **then** `count_dags`." This one line replaces the earlier
      two-task version and wires all three in order.

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
| **Orchestration** | Run jobs automatically, in order, on a schedule, with retries & backfills |
| **DAG** | Your pipeline as code — tasks with a defined order, no cycles |
| **Task / task instance** | A unit of work / one run of it inside a DAG run |
| **Operator** | The *type* of task — *what work it does* (`BashOperator`, `SparkSubmitOperator`, …) |
| **`BashOperator`** | An operator whose task runs a shell command (`bash_command=…`) |
| **`schedule`** | `@daily` / cron / `None` — how often the DAG runs |
| **`start_date`** | The earliest logical date the DAG is eligible to run from |
| **`catchup`** | Whether to backfill every missed interval since `start_date` (usually `False`) |
| **Dependency (`>>`)** | "then" — defines task order; `a >> b` runs `a` before `b` |
| **DAG run** | One execution of the whole DAG — one pass through all its tasks |
| **Idempotent** | Re-running the same task/run gives the same result (safe to retry & backfill) |
| **Template (`{{ … }}`)** | Value filled in at run time (`run_id`, `ds`, …) |

## You can now…
- Explain what an orchestrator does — order, schedule, retries, backfills — and the four problems
  Airflow solves
- Name the core Airflow objects: DAG, task, operator (`BashOperator`), schedule, DAG run
- Define a DAG with `dag_id`, `schedule`, `start_date`, and `catchup`, and wire task order with `>>`
- Write, trigger, and inspect a multi-task DAG in the Airflow UI, reading task states in the Grid
- Use templating (`{{ run_id }}`) and know when `{{ ds }}` applies
