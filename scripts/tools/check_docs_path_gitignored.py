#!/usr/bin/env python3
"""Check whether a workspace's docs_path is gitignored.

Usage:
    python scripts/tools/check_docs_path_gitignored.py <workspace-slug>

Prints a warning if docs_path is configured and git check-ignore reports it as
ignored. Silent (no output) when docs_path is not configured or is not ignored.
Exit 0 always — this is advisory, not a blocker.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace_config as _wc


def check_gitignored(slug: str, root: Path | None = None) -> str | None:
    """Return a warning string if the workspace's docs_path is gitignored, else None."""
    import os
    harness_root = root or Path(os.environ.get(
        "HARNESS_ROOT", str(Path(__file__).resolve().parents[2])
    ))
    ws_dir = harness_root / "workspaces" / slug
    cfg = _wc.load_workspace(ws_dir)
    if not cfg:
        return None

    raw_docs_path = cfg.get("docs_path")
    if not raw_docs_path:
        return None

    docs_path = Path(raw_docs_path).expanduser().resolve()
    if not docs_path.exists():
        return None

    result = subprocess.run(
        ["git", "-C", str(docs_path.parent), "check-ignore", "-q", str(docs_path)],
        capture_output=True,
    )
    if result.returncode == 0:
        return (
            f"WARNING: docs_path '{raw_docs_path}' is gitignored — "
            f"workspace docs will not sync across machines. "
            f"Remove the gitignore rule or move docs_path to a tracked location."
        )
    return None


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: check_docs_path_gitignored.py <workspace-slug>", file=sys.stderr)
        sys.exit(1)

    slug = sys.argv[1]
    warning = check_gitignored(slug)
    if warning:
        print(warning)


if __name__ == "__main__":
    main()
