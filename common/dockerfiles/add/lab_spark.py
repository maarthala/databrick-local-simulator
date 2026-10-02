"""lab_spark() — a Spark session for a learner's DAG, signed in AS THAT LEARNER.

Learner DAGs (synced from <user>-lake/dags/ by the "learners" bundle) run in the shared
Airflow, which has no learner credentials. This helper gives a task the same Spark a notebook
has: `iceberg` = the learner's own lakehouse (<user>_lake), `shared` = the course's shared lake.

    from airflow.sdk import dag, task

    @dag(dag_id="ravi_medallion", schedule=None, start_date=...)
    def ravi_medallion():
        @task
        def bronze():
            from lab_spark import lab_spark
            spark = lab_spark()                     # signs in as ravi
            spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.bronze")
            ...

Who: the folder of the running DAG's file (learners/<user>/…), so a learner's DAG gets
their own lakehouse. The login is a dedicated Polaris principal <user>_jobs holding the
learner's own principal-role (so it can do what they can); it's created on first use and its
secret kept in the Airflow Variable lab_jobs_<user>. (The learner's notebook login is
re-keyed on every Jupyter start, so jobs need their own.)
"""
import os
import re
import secrets

import lakehouse as lh

SPARK_REMOTE = os.environ.get("SPARK_REMOTE", "sc://spark-connect:15002")
BUNDLE = "/learners/"


def _current_user():
    from airflow.sdk import get_current_context
    loc = str(getattr(get_current_context()["dag"], "fileloc", "") or "")
    if BUNDLE not in loc:
        raise RuntimeError("lab_spark() is for learner DAGs (saved in your bucket's dags/ folder)")
    return loc.split(BUNDLE, 1)[1].split("/", 1)[0]          # bucket prefix, e.g. ravi or ravi-k


def _works(cred):
    cid, secret = cred.split(":", 1)
    st, _ = lh._call("POST", "/api/catalog/v1/oauth/tokens", form={
        "grant_type": "client_credentials", "client_id": cid, "client_secret": secret,
        "scope": "PRINCIPAL_ROLE:ALL"})
    return st == 200


def _jobs_credential(name):
    """client_id:secret of <name>_jobs (created + bound to the learner's role on first use)."""
    from airflow.sdk import Variable
    key = f"lab_jobs_{name}"
    cred = Variable.get(key, default=None)
    if cred and _works(cred):
        return cred
    # first use — or the stored login no longer works (secret reset elsewhere): make a fresh one
    t, m, jobs = lh._admin_token(), "/api/management/v1", f"{name}_jobs"
    lh._ok(lh._call("POST", f"{m}/principals", {"principal": {"name": jobs}}, t)[0], "jobs principal")
    lh._ok(lh._call("PUT", f"{m}/principals/{jobs}/principal-roles", {"principalRole": {"name": name}}, t)[0],
           "jobs role")
    secret = secrets.token_urlsafe(24)
    st, _ = lh._call("POST", f"{m}/principals/{jobs}/reset", {"clientId": jobs, "clientSecret": secret}, t)
    if st != 200:
        raise RuntimeError(f"jobs login for {name}: HTTP {st}")
    cred = f"{jobs}:{secret}"
    Variable.set(key, cred)
    return cred


def lab_spark(user=None):
    """Spark Connect session: iceberg = <user>_lake (as <user>_jobs), shared = the course lake."""
    from pyspark.sql import SparkSession
    name = lh.lake_name(user or _current_user())
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise ValueError(f"bad learner name {name!r}")
    cred = _jobs_credential(name)
    spark = SparkSession.builder.remote(SPARK_REMOTE).getOrCreate()
    # same settings as the server's own `iceberg` catalog — only the warehouse + login differ
    base = "spark.sql.catalog.iceberg"
    conf = {k: v for k, v in spark.conf.getAll.items() if k == base or k.startswith(base + ".")}
    for cat, warehouse in (("iceberg", f"{name}_lake"), ("shared", lh.SHARED)):
        for k, v in conf.items():
            spark.conf.set(f"spark.sql.catalog.{cat}" + k[len(base):], v)
        spark.conf.set(f"spark.sql.catalog.{cat}.warehouse", warehouse)
        spark.conf.set(f"spark.sql.catalog.{cat}.credential", cred)
    print(f"lab_spark: you are {name} · iceberg = {name}_lake · shared = {lh.SHARED}")
    return spark


def run_notebook(notebook, user=None):
    """Run one of the learner's notebooks (files/src/notebooks/<notebook> in their bucket) from a
    DAG task, the way Jupyter would: `spark` = lab_spark() (signed in as them) and `%%sql`.
    Cells run top to bottom; the task fails on the first cell that fails.

        @task
        def load():
            from lab_spark import run_notebook
            run_notebook("load_sample_orders.ipynb")
    """
    import json
    from IPython.core.interactiveshell import InteractiveShell

    who = user or _current_user()
    key = f"{lh.SRC}notebooks/{notebook}"
    with lh.get_object(lh.bucket_name(lh.lake_name(who)), key) as r:
        nb = json.loads(r.read())
    spark = lab_spark(who)
    shell = InteractiveShell.instance()
    shell.user_ns["spark"] = spark

    def sql(line, cell):                              # same %%sql as in the notebooks
        return spark.sql(cell).limit(1000).toPandas()
    shell.register_magic_function(sql, magic_kind="cell", magic_name="sql")

    cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    print(f"run_notebook: {key} — {len(cells)} code cells")
    for i, c in enumerate(cells, 1):
        src = "".join(c.get("source", []))
        result = shell.run_cell(src)
        err = result.error_in_exec or result.error_before_exec
        if err:
            raise RuntimeError(f"{notebook}: cell {i} failed: {err}")
        if result.result is not None:
            print(result.result)
        print(f"run_notebook: cell {i}/{len(cells)} ok")
