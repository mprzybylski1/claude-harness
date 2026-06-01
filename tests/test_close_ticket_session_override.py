"""Tests for T153: --session flag overrides current_session.py lookup.

When sessions.md already contains the S<N> log entry (session-close Step 1
runs before Step 2), close_ticket.py must still stamp S<N>, not S<N+1>.
The --session flag lets the caller pass the known-correct session ID.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conftest import make_harness_tree, run_close_ticket

TICKET = (
    "---\n"
    "id: T999\n"
    "title: Synthetic test ticket\n"
    "severity: medium\n"
    "status: open\n"
    "phase: 2\n"
    "layer: tooling\n"
    "opened: S8 2026-01-01\n"
    "closed:\n"
    "---\n"
    "\n"
    "## Problem\n\nSynthetic.\n\n"
    "## Acceptance Criteria\n\n"
    "- [x] Done\n\n"
    "## Resolution\n"
    "(Fill in on close.)\n"
)


class TestSessionOverride:
    """--session S<N> overrides the current_session.py lookup."""

    def test_session_flag_stamps_frontmatter(self, tmp_path):
        """closed: frontmatter uses the --session value, not current_session.py."""
        make_harness_tree(tmp_path, TICKET)
        result = run_close_ticket(
            tmp_path, "T999", "--resolution", "Fixed.", "--session", "S8",
        )
        assert result.returncode == 0, result.stderr

        archived = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        content = archived.read_text()
        assert "closed: S8 " in content
        # Must NOT contain S9 (which the stub current_session.py returns)
        assert "closed: S9 " not in content

    def test_session_flag_stamps_resolution_close_line(self, tmp_path):
        """Resolution close stamp uses the --session value."""
        make_harness_tree(tmp_path, TICKET)
        result = run_close_ticket(
            tmp_path, "T999", "--resolution", "Fixed.", "--session", "S8",
        )
        assert result.returncode == 0, result.stderr

        archived = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        content = archived.read_text()
        assert "Closed S8 " in content
        assert "Closed S9 " not in content

    def test_without_session_flag_uses_current_session_py(self, tmp_path):
        """Without --session, existing behavior (stub returns S9) is preserved."""
        make_harness_tree(tmp_path, TICKET)
        result = run_close_ticket(
            tmp_path, "T999", "--resolution", "Fixed.",
        )
        assert result.returncode == 0, result.stderr

        archived = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        content = archived.read_text()
        assert "closed: S9 " in content
        assert "Closed S9 " in content

    def test_session_flag_passed_to_index_regen(self, tmp_path):
        """_regenerate_index passes --session <N> so the INDEX gets the right stamp."""
        # Replace the stub generate_ticket_index.py with one that records args
        make_harness_tree(tmp_path, TICKET)
        recorder = tmp_path / "scripts" / "tools" / "generate_ticket_index.py"
        recorder.write_text(
            "import sys, os; from pathlib import Path\n"
            "root = Path(os.environ.get('HARNESS_ROOT', '.'))\n"
            "(root / 'docs' / 'tickets' / 'INDEX.md').write_text('# Updated\\n')\n"
            "(root / '_regen_args.txt').write_text(' '.join(sys.argv[1:]))\n"
        )
        result = run_close_ticket(
            tmp_path, "T999", "--resolution", "Fixed.", "--session", "S8",
        )
        assert result.returncode == 0, result.stderr

        args_file = tmp_path / "_regen_args.txt"
        assert args_file.exists(), "generate_ticket_index.py was not called"
        recorded_args = args_file.read_text()
        assert "--session" in recorded_args
        assert "8" in recorded_args


class TestSessionValidation:
    """--session normalizes input and rejects garbage."""

    def test_bare_number_normalized_to_s_prefix(self, tmp_path):
        """--session 8 is accepted and normalized to S8."""
        make_harness_tree(tmp_path, TICKET)
        result = run_close_ticket(
            tmp_path, "T999", "--resolution", "Fixed.", "--session", "8",
        )
        assert result.returncode == 0, result.stderr

        archived = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        content = archived.read_text()
        assert "closed: S8 " in content
        assert "Closed S8 " in content

    def test_malformed_session_rejected(self, tmp_path):
        """--session with non-numeric garbage exits non-zero."""
        make_harness_tree(tmp_path, TICKET)
        result = run_close_ticket(
            tmp_path, "T999", "--resolution", "Fixed.", "--session", "abc",
        )
        assert result.returncode != 0
        assert "S<N>" in result.stderr or "must be" in result.stderr
