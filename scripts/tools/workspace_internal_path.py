#!/usr/bin/env python3
"""Print the internal docs directory for a workspace slug.

Usage:
    python scripts/tools/workspace_internal_path.py <slug>

Prints the absolute path to the docs root (docs_path if configured in
workspace.yaml, otherwise workspaces/<slug>/internal/).

Used by session-start and session-close to resolve the correct path for
sessions.md, opus_notes.md, and tickets/ regardless of whether docs_path
is configured.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from workspace_config import workspace_dir, load_workspace, internal_dir


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <slug>", file=sys.stderr)
        sys.exit(1)

    slug = sys.argv[1]
    ws_dir = workspace_dir(slug)
    if not ws_dir.exists():
        print(f"Error: workspace '{slug}' not found at {ws_dir}", file=sys.stderr)
        sys.exit(1)

    ws = load_workspace(ws_dir)
    if not ws:
        print(f"Error: could not load workspace.yaml for '{slug}'", file=sys.stderr)
        sys.exit(1)

    print(internal_dir(ws_dir, ws))


if __name__ == "__main__":
    main()
