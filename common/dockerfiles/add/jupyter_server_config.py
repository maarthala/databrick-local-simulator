# Auto-push on save: after Jupyter writes a notebook/file that lives under the
# cloned git repo, commit it and push to the remote. Enabled only when
# GIT_AUTOPUSH=1 (the entrypoint clones + configures the repo first). The push
# runs on a background thread so saving in the UI never blocks on the network;
# a lock serialises pushes so rapid saves don't race.
import datetime
import os
import subprocess
import threading

REPO = os.environ.get("GIT_AUTOPUSH_DIR", "/home/jovyan/work/repo")
ENABLED = os.environ.get("GIT_AUTOPUSH", "0") == "1"
_lock = threading.Lock()


def _run(args):
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True)


def _autopush(os_path, log):
    with _lock:
        try:
            if not os.path.isdir(os.path.join(REPO, ".git")):
                return
            rel = os.path.relpath(os_path, REPO)
            if rel.startswith(".."):
                return  # saved outside the repo clone → nothing to push
            _run(["git", "add", "--", rel])
            # nothing staged (unchanged content) → skip an empty commit
            if not _run(["git", "status", "--porcelain"]).stdout.strip():
                return
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _run(["git", "commit", "-m", f"auto-save: {rel} @ {ts}"])
            # rebase on top of remote first so a push isn't rejected non-ff
            _run(["git", "pull", "--rebase", "--autostash"])
            push = _run(["git", "push"])
            if push.returncode != 0:
                log.warning("[autopush] push failed for %s: %s", rel, push.stderr.strip())
            else:
                log.info("[autopush] pushed %s", rel)
        except Exception as exc:  # never let a hook break saving
            log.warning("[autopush] error: %s", exc)


def post_save_hook(model, os_path, contents_manager, **kwargs):
    if not ENABLED or model.get("type") not in ("notebook", "file"):
        return
    threading.Thread(
        target=_autopush, args=(os_path, contents_manager.log), daemon=True
    ).start()


c = get_config()  # noqa: F821  (provided by Jupyter's config loader)
c.FileContentsManager.post_save_hook = post_save_hook
