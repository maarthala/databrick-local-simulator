# Auto-create a Databricks-style `spark` session in every notebook (IPython startup).
# Uses SPARK_REMOTE (sc://spark-connect:15002) set in the image, so no config needed.
# Wrapped so a down spark-connect doesn't break kernel startup.
try:
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    print(f"✓ `spark` ready via Spark Connect (Spark {spark.version})")
except Exception as _e:  # noqa: BLE001
    print(f"⚠ `spark` not created ({_e}).")
    print("  Start it once spark-connect is up: spark = SparkSession.builder.getOrCreate()")


# --- Materialized views for `%%sql` ------------------------------------------------
# Spark only runs CREATE MATERIALIZED VIEW inside a Declarative Pipeline, and Trino
# can't create them on a REST catalog (Polaris). So `%%sql` turns these statements into
# a one-view pipeline run (python -m pyspark.pipelines.cli). The view is a normal
# Iceberg table in Polaris; its SQL is kept in the `mv.definition` table property so
# REFRESH can re-run it. Supported:
#   CREATE [OR REPLACE] MATERIALIZED VIEW [IF NOT EXISTS] cat.ns.view AS <query>
#   REFRESH MATERIALIZED VIEW cat.ns.view
#   DROP MATERIALIZED VIEW [IF EXISTS] cat.ns.view
#   SHOW MATERIALIZED VIEWS IN cat.ns
import json as _json
import os as _os
import re as _re

_MV_STORAGE = _os.environ.get("MV_PIPELINE_STORAGE", "s3a://demo-bucket/pipelines/mv")
_MV_NAME = r"([A-Za-z0-9_`]+\.[A-Za-z0-9_`]+\.[A-Za-z0-9_`]+)"
_MV_CREATE = _re.compile(
    r"CREATE\s+(OR\s+REPLACE\s+)?MATERIALIZED\s+VIEW\s+(IF\s+NOT\s+EXISTS\s+)?"
    + _MV_NAME + r"\s+AS\s+(.+?)\s*;?\s*$", _re.I | _re.S)
_MV_REFRESH = _re.compile(r"REFRESH\s+MATERIALIZED\s+VIEW\s+" + _MV_NAME + r"\s*;?\s*$", _re.I)
_MV_DROP = _re.compile(r"DROP\s+MATERIALIZED\s+VIEW\s+(IF\s+EXISTS\s+)?" + _MV_NAME + r"\s*;?\s*$", _re.I)
_MV_SHOW = _re.compile(r"SHOW\s+MATERIALIZED\s+VIEWS\s+IN\s+([A-Za-z0-9_`]+\.[A-Za-z0-9_`]+)\s*;?\s*$", _re.I)


def _mv_strip_comments(sql):
    return "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--")).strip()


def _mv_definition(name):
    props = {r[0]: r[1] for r in spark.sql(f"SHOW TBLPROPERTIES {name}").collect()}
    return props.get("mv.definition")


def _mv_run(name, query):
    """Create/refresh one materialized view by running a single-view pipeline."""
    import subprocess, sys, tempfile, shutil
    catalog, ns, view = [p.strip("`") for p in name.split(".")]
    work = tempfile.mkdtemp(prefix="mv_")
    try:
        _os.makedirs(f"{work}/transformations")
        spec = {  # JSON is valid YAML
            "name": f"mv_{ns}_{view}", "catalog": catalog, "database": ns,
            "storage": f"{_MV_STORAGE}/{catalog}/{ns}/{view}",
            "libraries": [{"glob": {"include": "transformations/**"}}],
        }
        with open(f"{work}/spark-pipeline.yml", "w") as f:
            _json.dump(spec, f)
        with open(f"{work}/transformations/{view}.sql", "w") as f:
            f.write(f"CREATE MATERIALIZED VIEW {view} AS\n{query}\n")
        run = subprocess.run(
            [sys.executable, "-m", "pyspark.pipelines.cli", "run", "--spec", f"{work}/spark-pipeline.yml"],
            capture_output=True, text=True)
        if run.returncode != 0 or "Run is COMPLETED" not in run.stdout + run.stderr:
            tail = "\n".join((run.stdout + run.stderr).strip().splitlines()[-15:])
            raise RuntimeError(f"materialized view pipeline failed for {name}:\n{tail}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # Keep the SQL on the table itself (survives refreshes) so REFRESH can re-run it.
    literal = query.replace("\\", "\\\\").replace("'", "\\'")
    spark.sql(f"ALTER TABLE {name} SET TBLPROPERTIES ('mv.definition' = '{literal}')")


def _mv_handle(sql):
    """Run a materialized-view statement, or return None if `sql` isn't one."""
    import pandas as pd
    sql = _mv_strip_comments(sql)
    if m := _MV_CREATE.match(sql):
        replace, if_not_exists, name, query = m.groups()
        if spark.catalog.tableExists(name):
            if if_not_exists:
                return pd.DataFrame([{"materialized_view": name, "action": "exists, skipped"}])
            if not replace and _mv_definition(name) is None:
                raise ValueError(f"{name} already exists and is not a materialized view")
            if not replace:
                raise ValueError(f"{name} already exists — use CREATE OR REPLACE or REFRESH")
        _mv_run(name, query)
        action = "replaced" if replace else "created"
    elif m := _MV_REFRESH.match(sql):
        name = m.group(1)
        query = _mv_definition(name) if spark.catalog.tableExists(name) else None
        if query is None:
            raise ValueError(f"{name} is not a materialized view created with %%sql")
        _mv_run(name, query)
        action = "refreshed"
    elif m := _MV_DROP.match(sql):
        if_exists, name = m.groups()
        if not spark.catalog.tableExists(name):
            if if_exists:
                return pd.DataFrame([{"materialized_view": name, "action": "not found, skipped"}])
            raise ValueError(f"{name} does not exist")
        if _mv_definition(name) is None:
            raise ValueError(f"{name} is a table, not a materialized view — use DROP TABLE")
        spark.sql(f"DROP TABLE {name}")
        return pd.DataFrame([{"materialized_view": name, "action": "dropped"}])
    elif m := _MV_SHOW.match(sql):
        ns = m.group(1)
        rows = []
        for t in spark.sql(f"SHOW TABLES IN {ns}").collect():
            name = f"{ns}.{t.tableName}"
            if (d := _mv_definition(name)) is not None:
                rows.append({"materialized_view": name, "definition": d})
        return pd.DataFrame(rows, columns=["materialized_view", "definition"])
    elif _re.match(r"(CREATE|REFRESH|DROP)\s+.*?MATERIALIZED\s+VIEW", sql, _re.I | _re.S):
        raise ValueError("use a fully-qualified name: catalog.namespace.view "
                         "(e.g. iceberg.gold.revenue_by_region)")
    else:
        return None
    rows = spark.table(name).count()
    return pd.DataFrame([{"materialized_view": name, "action": action, "rows": rows}])


# Databricks-style `%%sql` cell magic — runs Spark SQL over any catalog table or view.
try:
    from IPython.core.magic import register_cell_magic

    @register_cell_magic
    def sql(line, cell):  # usage:  %%sql \n SELECT ... FROM iceberg.gold.tbl
        mv = _mv_handle(cell)
        if mv is not None:
            return mv
        # Return a pandas DataFrame so the notebook renders a real table (not just
        # the Spark schema repr). Capped at 1000 rows for display, like Databricks.
        return spark.sql(cell).limit(1000).toPandas()
except Exception:  # not in IPython, or spark missing
    pass
