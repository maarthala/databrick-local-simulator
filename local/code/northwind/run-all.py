"""Supervisor: run all three Northwind data generators in one container.

Launches the orders, product-price, and clickstream generators as child
processes and monitors them. If any child exits, the rest are terminated and
the supervisor exits non-zero so Docker's `restart: always` restarts the whole
container (keeping all three generators running as a unit).
"""

import os
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = [
    "orders-generator.py",
    "product-price-generator.py",
    "user-click-sessions.py",
]


def main():
    procs = []
    for script in SCRIPTS:
        path = os.path.join(HERE, script)
        print(f"[run-all] starting {script}", flush=True)
        procs.append(subprocess.Popen([sys.executable, "-u", path]))

    def shutdown(*_):
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()

    signal.signal(signal.SIGTERM, lambda *_: (shutdown(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda *_: (shutdown(), sys.exit(0)))

    # Block until any child exits, then take the whole container down so it
    # gets restarted cleanly.
    pid, _status = os.wait()
    print(f"[run-all] a generator exited (pid {pid}) — restarting container", flush=True)
    shutdown()
    sys.exit(1)


if __name__ == "__main__":
    main()
