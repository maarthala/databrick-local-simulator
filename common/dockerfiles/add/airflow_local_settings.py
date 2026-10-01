"""Airflow cluster policy: learner DAGs (bundle "learners", synced from <user>-lake/dags/)
must have a dag_id starting with <user>_ — one shared Airflow, so names can't clash.
A DAG that breaks the rule shows up as an import error naming the expected prefix.
"""
from airflow.exceptions import AirflowClusterPolicyViolation

BUNDLE = "/learners/"


def dag_policy(dag):
    loc = str(dag.fileloc or "")
    if BUNDLE not in loc:
        return
    user = loc.split(BUNDLE, 1)[1].split("/", 1)[0]
    prefix = user.replace("-", "_") + "_"
    if not dag.dag_id.startswith(prefix):
        raise AirflowClusterPolicyViolation(
            f"DAG id {dag.dag_id!r} must start with {prefix!r} (your username) — rename it, "
            f"e.g. dag_id='{prefix}{dag.dag_id}'")
    if user not in dag.tags:
        dag.tags.add(user) if isinstance(dag.tags, set) else dag.tags.append(user)
