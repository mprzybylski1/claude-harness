"""Tests for T111: check_cross_layer_writes.py PreToolUse hook."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hooks" / "check_cross_layer_writes.py"


def _setup(tmp_path: Path, workspace_slug: str | None = None) -> Path:
    """Set up minimal harness skeleton. Returns harness root."""
    harness = tmp_path / "harness"
    harness.mkdir()
    (harness / ".claude").mkdir()
    (harness / "docs").mkdir()
    (harness / "docs" / "tickets").mkdir()
    (harness / "workspaces").mkdir()
    if workspace_slug:
        (harness / ".claude" / ".active_workspace").write_text(
            workspace_slug, encoding="utf-8"
        )
    return harness


def _run(harness: Path, tool_name: str, file_path: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"file_path": file_path}})
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        env={**os.environ, "HARNESS_ROOT": str(harness)},
    )


class TestCrossLayerWrites:

    def test_workspace_session_blocks_harness_tickets(self, tmp_path):
        harness = _setup(tmp_path, workspace_slug="my-ws")
        result = _run(harness, "Write", str(harness / "docs" / "tickets" / "T999-foo.md"))
        assert result.returncode == 2
        assert "CROSS-LAYER WRITE BLOCKED" in result.stderr

    def test_workspace_session_blocks_harness_sessions_md(self, tmp_path):
        harness = _setup(tmp_path, workspace_slug="my-ws")
        result = _run(harness, "Edit", str(harness / "docs" / "sessions.md"))
        assert result.returncode == 2
        assert "CROSS-LAYER WRITE BLOCKED" in result.stderr

    def test_workspace_session_blocks_harness_opus_notes(self, tmp_path):
        harness = _setup(tmp_path, workspace_slug="my-ws")
        result = _run(harness, "Write", str(harness / "docs" / "opus_notes.md"))
        assert result.returncode == 2
        assert "CROSS-LAYER WRITE BLOCKED" in result.stderr

    def test_workspace_session_blocks_architecture_invariants(self, tmp_path):
        harness = _setup(tmp_path, workspace_slug="my-ws")
        result = _run(
            harness, "Write", str(harness / "docs" / "architecture_invariants.md")
        )
        assert result.returncode == 2
        assert "CROSS-LAYER WRITE BLOCKED" in result.stderr

    def test_harness_session_blocks_workspace_internal(self, tmp_path):
        harness = _setup(tmp_path)  # no state file → harness-root session
        result = _run(
            harness, "Write",
            str(harness / "workspaces" / "my-ws" / "internal" / "sessions.md"),
        )
        assert result.returncode == 2
        assert "CROSS-LAYER WRITE BLOCKED" in result.stderr

    def test_boundary_slot_exempt_workspace_session(self, tmp_path):
        """workspaces/*/raised/ is always allowed even in workspace session."""
        harness = _setup(tmp_path, workspace_slug="my-ws")
        result = _run(
            harness, "Write",
            str(harness / "workspaces" / "my-ws" / "raised" / "SR-001-test.md"),
        )
        assert result.returncode == 0

    def test_boundary_slot_exempt_harness_session(self, tmp_path):
        """workspaces/*/raised/ is always allowed even in harness session."""
        harness = _setup(tmp_path)  # harness session
        result = _run(
            harness, "Write",
            str(harness / "workspaces" / "my-ws" / "raised" / "SR-001-test.md"),
        )
        assert result.returncode == 0

    def test_workspace_session_allows_workspace_internal(self, tmp_path):
        """Workspace session writing its own internal/ is fine."""
        harness = _setup(tmp_path, workspace_slug="my-ws")
        result = _run(
            harness, "Write",
            str(harness / "workspaces" / "my-ws" / "internal" / "sessions.md"),
        )
        assert result.returncode == 0

    def test_harness_session_allows_harness_docs(self, tmp_path):
        """Harness-root session writing to docs/ is fine."""
        harness = _setup(tmp_path)  # harness session
        result = _run(harness, "Edit", str(harness / "docs" / "sessions.md"))
        assert result.returncode == 0

    def test_non_edit_write_tool_passthrough(self, tmp_path):
        """Non-Edit/Write tools are not checked."""
        harness = _setup(tmp_path, workspace_slug="my-ws")
        result = _run(harness, "Bash", str(harness / "docs" / "sessions.md"))
        assert result.returncode == 0

    def test_error_message_names_workspace_slug(self, tmp_path):
        """Error message includes the active workspace slug."""
        harness = _setup(tmp_path, workspace_slug="scrabble-score")
        result = _run(harness, "Write", str(harness / "docs" / "sessions.md"))
        assert "scrabble-score" in result.stderr

    def test_error_message_names_harness_session(self, tmp_path):
        """Error message says 'harness-root session' for AC on error message content."""
        harness = _setup(tmp_path)  # harness session
        result = _run(
            harness, "Write",
            str(harness / "workspaces" / "my-ws" / "internal" / "sessions.md"),
        )
        assert "harness-root session" in result.stderr
