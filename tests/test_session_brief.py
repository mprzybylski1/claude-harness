"""
Tests for T061: extract_session_brief.py tails .git/session_tool_log.errors
and includes the last 5 lines in its output.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "scripts" / "tools"

# Minimal valid sessions.md fixture
SESSIONS_MD = """\
# Sessions

## Current Phase & Status

Phase 1 (Test).

## Active Work

**S001 — test session**

## Session Log

S1 2026-01-01: initial
"""


class TestHookErrorsTail:
    """T061: extract_session_brief.py surfaces .git/session_tool_log.errors tail."""

    def _run(self, tmp_path: Path, errors_file: Path | None = None) -> subprocess.CompletedProcess:
        """Run extract_session_brief.py with a custom sessions.md and optional errors path."""
        sessions = tmp_path / "sessions.md"
        sessions.write_text(SESSIONS_MD)
        cmd = [
            sys.executable, str(TOOLS / "extract_session_brief.py"),
            "--sessions", str(sessions),
        ]
        if errors_file is not None:
            cmd += ["--errors", str(errors_file)]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_absent_errors_file_shows_none(self, tmp_path):
        """When no errors file exists, output says 'Hook errors: none'."""
        result = self._run(tmp_path, errors_file=tmp_path / "nonexistent_errors.txt")
        assert result.returncode == 0
        assert "Hook errors" in result.stdout
        assert "none" in result.stdout.lower()

    def test_empty_errors_file_shows_none(self, tmp_path):
        """When errors file is empty, output says 'Hook errors: none'."""
        errors = tmp_path / "errors.txt"
        errors.write_text("")
        result = self._run(tmp_path, errors_file=errors)
        assert result.returncode == 0
        assert "Hook errors" in result.stdout
        assert "none" in result.stdout.lower()

    def test_10_line_errors_file_shows_last_5(self, tmp_path):
        """With 10-line errors file, only the last 5 lines appear in output."""
        errors = tmp_path / "errors.txt"
        lines = [f"error line {i}" for i in range(1, 11)]
        errors.write_text("\n".join(lines) + "\n")
        result = self._run(tmp_path, errors_file=errors)
        assert result.returncode == 0
        # Last 5 lines must appear
        for i in range(6, 11):
            assert f"error line {i}" in result.stdout, (
                f"Expected 'error line {i}' in output:\n{result.stdout}"
            )
        # First 5 lines must NOT appear (use exact-line check to avoid substring collision
        # e.g. "error line 1" appears inside "error line 10")
        output_lines = result.stdout.splitlines()
        for i in range(1, 6):
            assert f"error line {i}" not in output_lines, (
                f"Did not expect 'error line {i}' as a complete line in output:\n{result.stdout}"
            )

    def test_fewer_than_5_lines_shows_all(self, tmp_path):
        """With only 3 error lines, all 3 appear in output (no truncation)."""
        errors = tmp_path / "errors.txt"
        errors.write_text("err A\nerr B\nerr C\n")
        result = self._run(tmp_path, errors_file=errors)
        assert result.returncode == 0
        assert "err A" in result.stdout
        assert "err B" in result.stdout
        assert "err C" in result.stdout

    def test_output_has_hook_errors_section_header(self, tmp_path):
        """Output includes a '## Hook errors' heading."""
        result = self._run(tmp_path, errors_file=tmp_path / "no_file.txt")
        assert result.returncode == 0
        assert "## Hook errors" in result.stdout

    def test_default_errors_path_used_when_flag_omitted(self, tmp_path):
        """When --errors is not passed, script uses default path without crashing."""
        # Run without --errors flag; the default .git/session_tool_log.errors likely
        # does not exist in tmp_path, but the script should still exit 0 and show "none".
        sessions = tmp_path / "sessions.md"
        sessions.write_text(SESSIONS_MD)
        result = subprocess.run(
            [
                sys.executable, str(TOOLS / "extract_session_brief.py"),
                "--sessions", str(sessions),
                # No --errors flag — use default path
            ],
            capture_output=True, text=True,
        )
        # Script must not crash; hook errors section must appear
        assert result.returncode == 0
        assert "## Hook errors" in result.stdout
