#!/usr/bin/env python3
"""
PreToolUse hook: block cross-layer writes between workspace and harness state.

Reads HARNESS_ROOT/.claude/.active_workspace to determine session type:
  - Non-empty content → workspace session (value is the slug)
  - Empty or absent   → harness-root session

Blocks:
  - Workspace session writing to harness-layer docs:
      docs/tickets/  docs/sessions.md  docs/opus_notes.md
      docs/architecture_invariants.md
  - Harness-root session writing to workspaces/*/internal/

Exempt:
  - workspaces/*/raised/ — boundary slot, always allowed

Fires on Edit and Write tools only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_default_root = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("HARNESS_ROOT", str(_default_root)))

_STATE_FILE = ROOT / ".claude" / ".active_workspace"
_WS_BASE = ROOT / "workspaces"

_HARNESS_PROTECTED = [
    ROOT / "docs" / "tickets",
    ROOT / "docs" / "sessions.md",
    ROOT / "docs" / "opus_notes.md",
    ROOT / "docs" / "architecture_invariants.md",
]


def _active_workspace_slug() -> str | None:
    try:
        slug = _STATE_FILE.read_text(encoding="utf-8").strip()
        return slug if slug else None
    except OSError:
        return None


def _is_boundary_slot(resolved: Path) -> bool:
    try:
        rel = resolved.relative_to(_WS_BASE)
        parts = rel.parts
        return len(parts) >= 2 and parts[1] == "raised"
    except ValueError:
        return False


def _is_harness_protected(resolved: Path) -> bool:
    for protected in _HARNESS_PROTECTED:
        try:
            resolved.relative_to(protected)
            return True
        except ValueError:
            pass
    return False


def _is_workspace_internal(resolved: Path) -> bool:
    try:
        rel = resolved.relative_to(_WS_BASE)
        parts = rel.parts
        return len(parts) >= 2 and parts[1] == "internal"
    except ValueError:
        return False


def _block(message: str) -> None:
    print(f"CROSS-LAYER WRITE BLOCKED — {message}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    resolved = Path(file_path).resolve()

    if _is_boundary_slot(resolved):
        sys.exit(0)

    workspace_slug = _active_workspace_slug()

    if workspace_slug:
        if _is_harness_protected(resolved):
            try:
                rel = str(resolved.relative_to(ROOT))
            except ValueError:
                rel = str(resolved)
            _block(
                f"workspace session '{workspace_slug}' may not write to harness-layer "
                f"path '{rel}'. Use workspaces/{workspace_slug}/raised/ to communicate "
                f"with the harness, or close the workspace session first."
            )
    else:
        if _is_workspace_internal(resolved):
            _block(
                f"harness-root session may not write to workspace-internal path "
                f"'{resolved}'. Open a workspace session (select a workspace at "
                f"session start) to write workspace-internal files."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
