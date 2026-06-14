"""
Tests for T154 + T158: closing a workspace ticket whose internal/ dir is
gitignored at the harness level must skip staging gracefully (exit 0 + note),
not fail on `git add` of an ignored path.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import git_init, run_close_ticket

OPEN_TICKET = """\
---
id: T999
title: Synthetic workspace ticket
severity: low
status: open
phase: 2
layer: tooling
opened: S1 2026-01-01
closed:
---

## Problem

Synthetic.

## Acceptance Criteria

- [x] AC one done

## Resolution
(Fill in on close.)
"""

_INDEX_STUB = (
    "import sys; from pathlib import Path\n"
    "a = sys.argv\n"
    "if '--output' in a:\n"
    "    Path(a[a.index('--output') + 1]).write_text('# Updated\\n')\n"
)


def _make_gitignored_internal_ws(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Harness repo that gitignores workspaces/*/internal/, with a ticket inside it.

    Returns (harness_root, internal_dir, ticket_path).
    """
    harness = tmp_path / "harness"
    (harness / "docs" / "tickets" / "open").mkdir(parents=True)
    (harness / "docs" / "archive").mkdir(parents=True)
    (harness / "docs" / "tickets" / "INDEX.md").write_text("# Index\n")
    (harness / "docs" / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n")
    tools = harness / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text("print('S9')\n")
    (tools / "generate_ticket_index.py").write_text(_INDEX_STUB)
    (harness / ".gitignore").write_text("workspaces/*/internal/\n")

    ws = harness / "workspaces" / "test-ws"
    internal = ws / "internal"
    (internal / "tickets" / "open").mkdir(parents=True)
    (internal / "archive").mkdir(parents=True)
    (internal / "tickets" / "INDEX.md").write_text("# Index\n")
    (internal / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n")
    ws.joinpath("workspace.yaml").write_text("name: test-ws\n")
    ticket = internal / "tickets" / "open" / "T999-synthetic-workspace-ticket.md"
    ticket.write_text(OPEN_TICKET, encoding="utf-8")

    git_init(harness)  # commits everything EXCEPT the gitignored internal/
    return harness, internal, ticket


class TestWorkspaceInternalGitignored:
    def test_close_succeeds_and_moves_archive(self, tmp_path):
        harness, internal, ticket = _make_gitignored_internal_ws(tmp_path)
        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done",
        )
        assert result.returncode == 0, f"Expected exit 0:\n{result.stderr}"
        assert not ticket.exists(), "ticket must be moved out of open/"
        assert (internal / "archive" / ticket.name).exists(), "archive must be created"

    def test_close_notes_gitignored_skip_not_scary_failure(self, tmp_path):
        harness, internal, ticket = _make_gitignored_internal_ws(tmp_path)
        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done",
        )
        assert result.returncode == 0, result.stderr
        # An informational note about the gitignored skip, not a "staging failed" error.
        assert "gitignored" in result.stderr.lower()
        assert "staging failed" not in result.stderr.lower()

    def test_close_with_commit_no_error_when_nothing_tracked(self, tmp_path):
        harness, internal, ticket = _make_gitignored_internal_ws(tmp_path)
        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done", "--commit",
        )
        assert result.returncode == 0, f"--commit must not error on gitignored close:\n{result.stderr}"
        assert (internal / "archive" / ticket.name).exists()


class TestHarnessRootStagingUnaffected:
    def test_harness_ticket_still_stages_archive(self, tmp_path):
        """Regression: a normal harness-root ticket close still stages the archive."""
        from conftest import make_harness_tree
        ticket = make_harness_tree(tmp_path, OPEN_TICKET)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done")
        assert result.returncode == 0, result.stderr
        staged = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        # Archive dest should be staged (index column non-blank).
        assert any("archive" in ln and ln[:1] not in (" ", "?") for ln in staged.splitlines()), \
            f"archive must be staged in harness-root close:\n{staged}"
