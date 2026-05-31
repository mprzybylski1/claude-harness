"""
Tests for T085: close_ticket.py --path-only flag resolves ticket ID to file path.
"""
from __future__ import annotations

from pathlib import Path

from conftest import make_harness_tree, run_close_ticket

OPEN_TICKET = """\
---
id: T999
title: Synthetic test ticket
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


def _setup(tmp_path: Path) -> Path:
    """Minimal harness tree (no git needed for --path-only). Returns the ticket path."""
    docs = tmp_path / "docs"
    (docs / "tickets" / "open").mkdir(parents=True)
    (docs / "archive").mkdir(parents=True)
    (docs / "tickets" / "INDEX.md").write_text("# Ticket Index\n")
    (docs / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n")
    ticket = docs / "tickets" / "open" / "T999-synthetic-test-ticket.md"
    ticket.write_text(OPEN_TICKET, encoding="utf-8")
    return ticket


class TestPathOnly:

    def test_path_only_prints_ticket_path(self, tmp_path):
        """--path-only prints the absolute path of the open ticket and exits 0."""
        ticket = _setup(tmp_path)
        result = run_close_ticket(tmp_path, "T999", "--path-only")
        assert result.returncode == 0, f"Expected 0\nstderr={result.stderr}"
        assert str(ticket) in result.stdout.strip(), \
            f"Expected ticket path in stdout:\n{result.stdout}"

    def test_path_only_no_side_effects(self, tmp_path):
        """--path-only must not move the ticket or modify any files."""
        ticket = _setup(tmp_path)
        run_close_ticket(tmp_path, "T999", "--path-only")
        assert ticket.exists(), "ticket must still be in open/ after --path-only"
        archive = tmp_path / "docs" / "archive" / ticket.name
        assert not archive.exists(), "archive must not be created by --path-only"

    def test_path_only_not_found_exits_nonzero(self, tmp_path):
        """--path-only exits 1 and prints an error when ticket ID is not found."""
        _setup(tmp_path)
        result = run_close_ticket(tmp_path, "T000", "--path-only")
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower(), \
            f"Expected error message:\n{result.stderr}"

    def test_path_only_exclusive_with_resolution(self, tmp_path):
        """--path-only combined with --resolution must fail (argparse error)."""
        _setup(tmp_path)
        result = run_close_ticket(tmp_path, "T999", "--path-only", "--resolution", "done")
        assert result.returncode != 0, \
            "--path-only and --resolution together must be an error"

    def test_path_only_no_resolution_required(self, tmp_path):
        """--path-only must not require --resolution (the normally-required group)."""
        _setup(tmp_path)
        result = run_close_ticket(tmp_path, "T999", "--path-only")
        assert result.returncode == 0, \
            f"--path-only must succeed without --resolution\nstderr={result.stderr}"
