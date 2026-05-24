from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _get_root() -> Path:
    env = os.environ.get("WORKFLOW_REPO_ROOT")
    if env:
        return Path(env)
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    )


_SAFETY_PREFIXES = [
    "core/",
    "execution/",
    "strategies/runtime.py",
    "strategies/specs/",
    "infra/audit_log.py",
]


def snapshot(root: Path | None = None) -> str:
    r = root or _get_root()
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=r, text=True
    ).strip()


def revert_to_snapshot(sha: str, root: Path | None = None) -> None:
    r = root or _get_root()
    subprocess.run(["git", "reset", "--hard", sha], cwd=r, check=True, capture_output=True)
    subprocess.run(["git", "clean", "-fd"], cwd=r, check=True, capture_output=True)


def has_unauthorized_commits(since_sha: str, root: Path | None = None) -> bool:
    r = root or _get_root()
    out = subprocess.check_output(
        ["git", "log", f"{since_sha}..HEAD", "--oneline"],
        cwd=r,
        text=True,
    ).strip()
    return bool(out)


def touches_safety_critical(since_sha: str, root: Path | None = None) -> bool:
    r = root or _get_root()
    # Diff working tree against snapshot — NOT since_sha..HEAD (which compares two commits
    # and returns empty when no unauthorized commits exist).
    changed_tracked = subprocess.check_output(
        ["git", "diff", "--name-only", since_sha],
        cwd=r,
        text=True,
    ).splitlines()

    # Also include new untracked files — git diff won't show files that were never tracked.
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=r,
        text=True,
    )
    untracked = [
        line[3:].strip()
        for line in status.splitlines()
        if line.startswith("??")
    ]

    all_changed = [f.strip() for f in changed_tracked + untracked if f.strip()]
    return any(
        any(f.startswith(p) for p in _SAFETY_PREFIXES)
        for f in all_changed
    )


def diff_since(since_sha: str, root: Path | None = None) -> str:
    r = root or _get_root()
    diff = subprocess.check_output(["git", "diff", since_sha], cwd=r, text=True)

    # Append stubs for new untracked files — git diff won't show files not yet tracked.
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=r, text=True,
    )
    for line in status.splitlines():
        if line.startswith("??"):
            filepath = line[3:].strip()
            full = r / filepath
            if full.is_file():
                try:
                    content = full.read_text()[:300]
                except OSError:
                    content = "(unreadable)"
                diff += f"\n--- /dev/null\n+++ b/{filepath}\n@@ -0,0 +1 @@\n{content}\n"
    return diff
