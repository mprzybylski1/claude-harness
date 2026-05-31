#!/usr/bin/env python3
"""
PreToolUse hook: block cross-layer and cross-workspace writes.

Reads HARNESS_ROOT/.claude/.active_workspace to determine session type:
  - "__harness__"           → harness-root session
  - Any other non-empty str → workspace session (value is the slug)
  - Empty or absent file    → undeclared session (fail closed)

Blocks:
  - Workspace session writing to harness-layer docs:
      docs/tickets/  docs/sessions.md  docs/opus_notes.md
      docs/architecture_invariants.md
  - Workspace session writing to a DIFFERENT workspace's internal/
      (Workspace Isolation invariant)
  - Harness-root session writing to any workspaces/*/internal/
  - Undeclared session writing to any protected zone above

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

# Single source of truth for the .active_workspace tri-state read (T143). The hook
# is the *enforcement* authority and read_session_state is the *attribution*
# authority; keeping two readers risked a silent divergence (Opus S25 Concern #2).
# The import resolves from THIS file's location (_default_root), independent of the
# HARNESS_ROOT env override that only redirects where the state file is read.
#
# Fail CLOSED on import failure: this hook is the sole confidentiality enforcer
# (Inv 2/4). Claude Code treats exit 2 as a block but any *other* non-zero — e.g.
# an uncaught ImportError → exit 1 — as a non-blocking error (the tool proceeds),
# which would silently fail OPEN. So a broken import must map to exit 2. The hook
# matches Edit|Write only, so this block still leaves Bash as a recovery surface
# (consistent with T142's fail-closed-with-recovery design).
sys.path.insert(0, str(_default_root / "scripts" / "tools"))
try:
    import workspace_config as _wc
except Exception as _e:  # defensive; workspace_config is core infra (test covers this)
    print(
        f"CROSS-LAYER WRITE BLOCKED — enforcement hook could not import "
        f"workspace_config ({_e}); failing closed. Restore scripts/tools/"
        f"workspace_config.py via Bash to recover.",
        file=sys.stderr,
    )
    sys.exit(2)

STATE_UNDECLARED = _wc.STATE_UNDECLARED
STATE_HARNESS = _wc.STATE_HARNESS
STATE_WORKSPACE = _wc.STATE_WORKSPACE

_WS_BASE = (ROOT / "workspaces").resolve()

_HARNESS_PROTECTED = [
    (ROOT / "docs" / "tickets").resolve(),
    (ROOT / "docs" / "sessions.md").resolve(),
    (ROOT / "docs" / "opus_notes.md").resolve(),
    (ROOT / "docs" / "architecture_invariants.md").resolve(),
]


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


def _workspace_internal_slug(resolved: Path) -> str | None:
    """Return the workspace slug if path is inside workspaces/<slug>/internal/, else None."""
    try:
        rel = resolved.relative_to(_WS_BASE)
        parts = rel.parts
        if len(parts) >= 2 and parts[1] == "internal":
            return parts[0]
    except ValueError:
        pass
    return None


def _block(message: str) -> None:
    print(f"CROSS-LAYER WRITE BLOCKED — {message}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception as e:
        print(f"check_cross_layer_writes: could not parse hook payload: {e}", file=sys.stderr)
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

    state, workspace_slug = _wc.read_session_state(ROOT)

    if state == STATE_UNDECLARED:
        if _is_harness_protected(resolved) or _workspace_internal_slug(resolved) is not None:
            _block(
                f"session type undeclared (.claude/.active_workspace is missing or empty). "
                f"Run /session-start to declare workspace context, then retry the write to "
                f"'{resolved}'."
            )
        sys.exit(0)

    if state == STATE_HARNESS:
        target_slug = _workspace_internal_slug(resolved)
        if target_slug is not None:
            _block(
                f"harness-root session may not write to workspace-internal path "
                f"'{resolved}'. Open a workspace session (select a workspace at "
                f"session start) to write workspace-internal files."
            )
        sys.exit(0)

    # state == STATE_WORKSPACE
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

    target_slug = _workspace_internal_slug(resolved)
    if target_slug is not None and target_slug != workspace_slug:
        _block(
            f"workspace session '{workspace_slug}' may not write to other workspace "
            f"'{target_slug}' internal path '{resolved}'. Cross-workspace writes "
            f"violate the Workspace Isolation invariant."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
