from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

from .git_ops import _get_root

# Paths the agent must never write to. Writing to these kills the agent immediately.
#
# core/, execution/, strategies/runtime.py are intentionally NOT here — the agent
# may propose changes to safety-critical code, but those changes are routed to
# AWAITING_ARCHITECTURE_REVIEW (not auto-committed). The hash guard enforces that
# scripts/workflows/ is never modified by using SHA-256 checks rather than watcher.
DENIED_PATHS = [
    "docs/architecture_invariants.md",  # immutable governance document
    "config.yaml",                       # production config
    "infra/audit_log.py",               # append-only audit log — never modify
]

POLL_INTERVAL_S = 0.5


class DenylistWatcher(threading.Thread):
    """Background thread that polls git status and kills the agent on denylist violations."""

    def __init__(self, process: subprocess.Popen, root: Path | None = None) -> None:
        super().__init__(daemon=True)
        self._process = process
        self._root = root or _get_root()
        self._violation: str | None = None
        self._exception: BaseException | None = None
        self._stop_event = threading.Event()  # named _stop_event to avoid shadowing Thread._stop()

    @property
    def crashed(self) -> bool:
        return self._exception is not None

    def run(self) -> None:
        try:
            while not self._stop_event.is_set():
                r = subprocess.run(
                    ["git", "status", "--short", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=self._root,
                )
                for line in r.stdout.splitlines():
                    filepath = line[3:].strip()
                    if any(filepath.startswith(p) for p in DENIED_PATHS):
                        self._violation = filepath
                        self._process.terminate()
                        self._stop_event.set()
                        return
                time.sleep(POLL_INTERVAL_S)
        except Exception as exc:  # noqa: BLE001
            self._exception = exc
            self._stop_event.set()

    def stop(self) -> str | None:
        """Signal the thread to stop and return any recorded violation path."""
        self._stop_event.set()
        self.join(timeout=2.0)
        return self._violation
