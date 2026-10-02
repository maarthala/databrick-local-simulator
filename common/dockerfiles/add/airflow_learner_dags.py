"""Learner DAGs from the object store — one DAG bundle for ALL learners.

Every learner bucket <user>-lake has a files/src/dags/ folder (created by lakehouse.provision).
On each refresh this bundle lists the learner buckets and syncs each files/src/dags/ folder to
<bundle dir>/<user>/ — so a learner saves a .py into dags/ in Jupyter (synced to files/src/dags/),
or uploads it with My files / the RustFS console, and it shows up in Airflow a little later.
New learners appear without touching the Airflow config (one bundle, not one each).

DAG ids must start with <user>_ (one shared Airflow) — enforced by the dag_policy in
airflow_local_settings.py.
"""
import logging
import shutil
from pathlib import Path

from airflow.dag_processing.bundles.base import BaseDagBundle
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

SUFFIX = "-lake"
log = logging.getLogger(__name__)


class LearnerDagsBundle(BaseDagBundle):
    supports_versioning = False

    def __init__(self, *, aws_conn_id="learner_s3", prefix="files/src/dags/", **kwargs):
        super().__init__(**kwargs)
        self.aws_conn_id = aws_conn_id
        self.prefix = prefix

    @property
    def path(self) -> Path:
        return self.base_dir

    def get_current_version(self):
        return None

    def initialize(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.refresh()
        super().initialize()

    def refresh(self) -> None:
        hook = S3Hook(aws_conn_id=self.aws_conn_id)
        with self.lock():
            users = set()
            for b in hook.get_conn().list_buckets().get("Buckets", []):
                bucket = b["Name"]
                if not bucket.endswith(SUFFIX):
                    continue
                user = bucket[: -len(SUFFIX)]
                users.add(user)
                try:
                    hook.sync_to_local_dir(bucket_name=bucket, s3_prefix=self.prefix,
                                           local_dir=self.base_dir / user, delete_stale=True)
                except Exception as e:          # one broken bucket mustn't hide everyone's DAGs
                    log.warning("learner DAGs: skip %s: %s", bucket, e)
            for d in self.base_dir.iterdir():   # learner removed → their DAGs go too
                if d.is_dir() and d.name not in users:
                    shutil.rmtree(d, ignore_errors=True)
