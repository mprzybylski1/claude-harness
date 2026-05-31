"""Shared test fixtures for close_ticket.py test files."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STUB_CURRENT_SESSION = "print('S9')\n"

STUB_GENERATE_INDEX = (
    "import os; from pathlib import Path\n"
    "root = Path(os.environ.get('HARNESS_ROOT', '.'))\n"
    "(root / 'docs' / 'tickets' / 'INDEX.md').write_text('# Updated\\n')\n"
)


def git_init(repo: Path) -> None:
    """Initialize a git repo with test identity and an initial commit of all files."""
    for cmd in [
        ["git", "-C", str(repo), "init", "-q"],
        ["git", "-C", str(repo), "config", "user.email", "t@test.com"],
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        ["git", "-C", str(repo), "config", "commit.gpgsign", "false"],
        ["git", "-C", str(repo), "add", "-A"],
        ["git", "-C", str(repo), "commit", "-q", "-m", "init"],
    ]:
        subprocess.run(cmd, check=True, capture_output=True)


def make_harness_tree(
    tmp_path: Path,
    ticket_content: str,
    ticket_filename: str = "T999-synthetic-test-ticket.md",
) -> Path:
    """Create a minimal harness dir tree + git repo. Returns the ticket path."""
    docs = tmp_path / "docs"
    (docs / "tickets" / "open").mkdir(parents=True)
    (docs / "archive").mkdir(parents=True)
    (docs / "tickets" / "INDEX.md").write_text("# Ticket Index\n", encoding="utf-8")
    (docs / "sessions.md").write_text(
        "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
    )
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text(STUB_CURRENT_SESSION)
    (tools / "generate_ticket_index.py").write_text(STUB_GENERATE_INDEX)
    ticket = docs / "tickets" / "open" / ticket_filename
    ticket.write_text(ticket_content, encoding="utf-8")
    git_init(tmp_path)
    return ticket


def run_close_ticket(harness_root: Path, *extra_args: str) -> subprocess.CompletedProcess:
    """Run close_ticket.py as a subprocess against a test harness root."""
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "tools" / "close_ticket.py"), *extra_args],
        capture_output=True, text=True,
        env={**os.environ, "HARNESS_ROOT": str(harness_root), "PYTHONPATH": str(ROOT)},
    )
