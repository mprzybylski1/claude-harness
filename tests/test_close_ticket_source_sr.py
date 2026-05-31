"""Tests for T108: close_ticket.py close-the-loop — resolves source SR on ticket close."""
from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import git_init, make_harness_tree, run_close_ticket

_TICKET_WITH_SOURCE = """\
---
id: T999
title: Synthetic source ticket
severity: low
status: open
phase: 2
layer: tooling
opened: S1 2026-01-01
closed:
source: myws/SR-001
---

## Problem

Promoted from SR-001.

## Acceptance Criteria

- [x] AC done

## Resolution
(Fill in on close.)
"""

_TICKET_NO_SOURCE = """\
---
id: T998
title: Synthetic ticket no source
severity: low
status: open
phase: 2
layer: tooling
opened: S1 2026-01-01
closed:
---

## Problem

No source.

## Acceptance Criteria

- [x] AC done

## Resolution
(Fill in on close.)
"""

_SR_BODY = """\
---
id: SR-001
from: myws
raised: S5 2026-05-27
title: Some concern
severity: medium
status: promoted
harness_ticket: T999
resolved_in:
---

## Context

Context here.

## Harness disposition

Promoted S5 2026-05-27.
"""


def _setup(tmp_path: Path, *, with_sr: bool = True) -> tuple[Path, Path | None]:
    """Minimal harness + git repo with source SR. Returns (ticket_path, sr_path | None)."""
    # Build harness tree without git (we may need to add SR files before commit)
    docs = tmp_path / "docs"
    (docs / "tickets" / "open").mkdir(parents=True)
    (docs / "archive").mkdir(parents=True)
    (docs / "tickets" / "INDEX.md").write_text("# Ticket Index\n", encoding="utf-8")
    (docs / "sessions.md").write_text(
        "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
    )
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text("print('S9')\n", encoding="utf-8")
    (tools / "generate_ticket_index.py").write_text(
        "import os; from pathlib import Path\n"
        "root = Path(os.environ.get('HARNESS_ROOT', '.'))\n"
        "(root / 'docs' / 'tickets' / 'INDEX.md').write_text('# Updated\\n')\n",
        encoding="utf-8",
    )
    ticket = docs / "tickets" / "open" / "T999-synthetic-source-ticket.md"
    ticket.write_text(_TICKET_WITH_SOURCE, encoding="utf-8")

    sr_path: Path | None = None
    if with_sr:
        raised = tmp_path / "workspaces" / "myws" / "raised"
        raised.mkdir(parents=True)
        sr_path = raised / "SR-001-some-concern.md"
        sr_path.write_text(_SR_BODY, encoding="utf-8")

    git_init(tmp_path)
    return ticket, sr_path


class TestCloseTicketSourceSR:

    def test_sr_status_set_to_resolved(self, tmp_path):
        """Closing a ticket with source: updates the SR status to resolved."""
        _, sr_path = _setup(tmp_path)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "Done.", "--tick-acs")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "status: resolved" in content
        assert "status: promoted" not in content

    def test_sr_resolved_in_set(self, tmp_path):
        """Closing a ticket with source: sets resolved_in on the SR."""
        _, sr_path = _setup(tmp_path)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "Done.", "--tick-acs")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "resolved_in: S9" in content

    def test_sr_staged_in_same_transaction(self, tmp_path):
        """SR file appears in git staging area after close."""
        _, sr_path = _setup(tmp_path)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "Done.", "--tick-acs")
        assert result.returncode == 0, result.stderr
        status = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain"],
            capture_output=True, text=True,
        ).stdout
        sr_rel = sr_path.relative_to(tmp_path)
        assert str(sr_rel) in status, f"SR not staged. git status:\n{status}"

    def test_sr_path_in_stdout(self, tmp_path):
        """Output mentions the SR file as staged."""
        _, sr_path = _setup(tmp_path)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "Done.", "--tick-acs")
        assert result.returncode == 0, result.stderr
        assert "SR-001" in result.stdout

    def test_no_source_field_is_noop(self, tmp_path):
        """Ticket without source: closes normally with no SR side-effect."""
        make_harness_tree(
            tmp_path, _TICKET_NO_SOURCE,
            ticket_filename="T998-synthetic-ticket-no-source.md",
        )
        result = run_close_ticket(tmp_path, "T998", "--resolution", "Done.", "--tick-acs")
        assert result.returncode == 0, result.stderr
        assert not (tmp_path / "workspaces").exists() or \
               not (tmp_path / "workspaces" / "myws").exists()

    def test_missing_sr_file_blocks_close_by_default(self, tmp_path):
        """T120: missing source SR file blocks close (exit 2) by default."""
        _setup(tmp_path, with_sr=False)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "Done.", "--tick-acs")
        assert result.returncode == 2, result.stderr
        assert "SR" in result.stderr
        assert not (tmp_path / "docs" / "archive" / "T999-synthetic-source-ticket.md").exists()
        assert (tmp_path / "docs" / "tickets" / "open" / "T999-synthetic-source-ticket.md").exists()

    def test_missing_sr_file_message_includes_sr_path(self, tmp_path):
        """T120: error message includes the path that was searched."""
        _setup(tmp_path, with_sr=False)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "Done.", "--tick-acs")
        assert result.returncode == 2
        assert "myws" in result.stderr
        assert "SR-001" in result.stderr
        assert "--ignore-missing-sr" in result.stderr

    def test_ignore_missing_sr_flag_allows_close(self, tmp_path):
        """T120: --ignore-missing-sr allows close to proceed when SR file absent."""
        _setup(tmp_path, with_sr=False)
        result = run_close_ticket(
            tmp_path, "T999", "--resolution", "Done.",
            "--tick-acs", "--ignore-missing-sr",
        )
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "docs" / "archive" / "T999-synthetic-source-ticket.md").exists()

    def test_sr_resolved_in_inserted_when_field_absent(self, tmp_path):
        """resolved_in: is inserted into SR frontmatter even if field was missing."""
        _, sr_path = _setup(tmp_path)
        text = sr_path.read_text(encoding="utf-8")
        sr_path.write_text(text.replace("resolved_in:\n", ""), encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(tmp_path), "add", "-A"],
            capture_output=True
        )
        result = run_close_ticket(tmp_path, "T999", "--resolution", "Done.", "--tick-acs")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "resolved_in: S9" in content
