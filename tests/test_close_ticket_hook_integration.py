"""
T088: Integration tests — close_ticket.py --files + check_fix_commit_has_code.py hook.

Drives the full seam: close a ticket, then pass the suggested commit through the hook.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "hooks" / "check_fix_commit_has_code.py"
CLOSE_TICKET = ROOT / "scripts" / "tools" / "close_ticket.py"

OPEN_TICKET = """\
---
id: T999
title: Synthetic integration test ticket
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


def _make_git_repo(path: Path) -> None:
    for cmd in [
        ["git", "init", "-q", str(path)],
        ["git", "-C", str(path), "config", "user.email", "t@t.com"],
        ["git", "-C", str(path), "config", "user.name", "Test"],
        ["git", "-C", str(path), "config", "commit.gpgsign", "false"],
    ]:
        subprocess.run(cmd, check=True, capture_output=True)


def _setup_harness(tmp_path: Path) -> tuple[Path, Path]:
    """Return (ticket_path, code_file) after creating a minimal harness git repo."""
    docs = tmp_path / "docs"
    (docs / "tickets" / "open").mkdir(parents=True)
    (docs / "archive").mkdir(parents=True)
    (docs / "tickets" / "INDEX.md").write_text("# Ticket Index\n", encoding="utf-8")
    (docs / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8")

    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
    (tools / "generate_ticket_index.py").write_text(
        "import os; from pathlib import Path\n"
        "root = Path(os.environ.get('HARNESS_ROOT', '.'))\n"
        "(root / 'docs' / 'tickets' / 'INDEX.md').write_text('# Updated\\n')\n"
    )

    ticket = docs / "tickets" / "open" / "T999-synthetic-integration-test-ticket.md"
    ticket.write_text(OPEN_TICKET, encoding="utf-8")

    code_file = tools / "myfix.py"
    code_file.write_text("# v1\n")

    _make_git_repo(tmp_path)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"],
                   check=True, capture_output=True)

    code_file.write_text("# v2\n")
    return ticket, code_file


def _run_close(tmp_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(CLOSE_TICKET), *extra_args],
        capture_output=True, text=True,
        env={**_os.environ, "HARNESS_ROOT": str(tmp_path), "PYTHONPATH": str(ROOT)},
    )


def _run_hook(command: str, cwd: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True,
        cwd=str(cwd),
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
    )


class TestCloseTicketHookIntegration:

    def test_with_files_hook_allows_commit(self, tmp_path):
        """close_ticket --files stages code; hook allows the suggested fix commit."""
        _ticket, code_file = _setup_harness(tmp_path)

        result = _run_close(tmp_path, "T999", "--resolution", "done",
                            "--files", str(code_file))
        assert result.returncode == 0, f"close_ticket failed:\n{result.stderr}"

        # The suggested commit command
        hook_result = _run_hook(
            f'git commit -m "fix(T999): Synthetic integration test ticket"',
            cwd=tmp_path,
        )
        assert hook_result.returncode == 0, (
            f"Hook blocked a commit that should be allowed "
            f"(code staged via --files):\n{hook_result.stderr}"
        )

    def test_without_files_hook_blocks_commit(self, tmp_path):
        """close_ticket without --files stages no code; hook blocks the fix commit."""
        _ticket, _code_file = _setup_harness(tmp_path)
        # Do NOT modify code_file — no dirty working-tree changes, clean repo
        # Close the ticket with no --files
        result = _run_close(tmp_path, "T999", "--resolution", "done")
        assert result.returncode == 0, f"close_ticket failed:\n{result.stderr}"

        # Only archive + INDEX are staged; hook must block
        hook_result = _run_hook(
            f'git commit -m "fix(T999): Synthetic integration test ticket"',
            cwd=tmp_path,
        )
        assert hook_result.returncode != 0, (
            f"Hook should have blocked a fix commit with no code staged:\n"
            f"stdout={hook_result.stdout}\nstderr={hook_result.stderr}"
        )
