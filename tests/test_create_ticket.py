"""Tests for T089: create_ticket.py scaffolding script."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATE = ROOT / "scripts" / "tools" / "create_ticket.py"


def _setup(tmp_path: Path) -> Path:
    """Minimal harness skeleton. Returns harness root."""
    (tmp_path / "docs" / "tickets" / "open").mkdir(parents=True)
    (tmp_path / "docs" / "archive").mkdir(parents=True)
    (tmp_path / "docs" / "tickets" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (tmp_path / "docs" / "sessions.md").write_text(
        "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
    )
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
    (tools / "generate_ticket_index.py").write_text(
        "import os; from pathlib import Path\n"
        "root = Path(os.environ.get('HARNESS_ROOT', '.'))\n"
        "(root / 'docs' / 'tickets' / 'INDEX.md').write_text('# Updated\\n')\n"
    )
    return tmp_path


def _run(harness: Path, *args: str) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(CREATE), *args],
        capture_output=True, text=True,
        env={**_os.environ, "HARNESS_ROOT": str(harness), "PYTHONPATH": str(ROOT)},
    )


class TestCreateTicket:

    def test_happy_path_creates_file(self, tmp_path):
        """Ticket file is created with correct frontmatter."""
        harness = _setup(tmp_path)
        result = _run(harness, "Fix the thing", "--severity", "high")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        assert created.exists(), f"File not created at {created}"
        content = created.read_text(encoding="utf-8")
        assert "id: T001" in content
        assert "title: Fix the thing" in content
        assert "severity: high" in content
        assert "status: open" in content
        assert "- [ ] (fill in)" in content

    def test_auto_id_increments(self, tmp_path):
        """Second ticket gets T002 when T001 already exists in archive."""
        harness = _setup(tmp_path)
        # Seed a T001 in archive
        (harness / "docs" / "archive" / "T001-old.md").write_text("---\nid: T001\n---\n")

        result = _run(harness, "Second ticket")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        content = created.read_text(encoding="utf-8")
        assert "id: T002" in content

    def test_ac_flag_populates_acs(self, tmp_path):
        """--ac flags write checked ACs into the file."""
        harness = _setup(tmp_path)
        result = _run(harness, "Ticket with ACs", "--ac", "AC one", "--ac", "AC two")
        assert result.returncode == 0, result.stderr

        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "- [ ] AC one" in content
        assert "- [ ] AC two" in content
        assert "(fill in)" not in content

    def test_workspace_routing(self, tmp_path):
        """--workspace routes to workspace internal tickets/open/."""
        harness = _setup(tmp_path)
        ws = harness / "workspaces" / "myws"
        (ws / "internal" / "tickets" / "open").mkdir(parents=True)
        (ws / "internal" / "archive").mkdir(parents=True)
        (ws / "internal" / "tickets" / "INDEX.md").write_text("# Index\n")
        (ws / "internal" / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n"
        )
        ws.joinpath("workspace.yaml").write_text("name: myws\n", encoding="utf-8")

        result = _run(harness, "Workspace ticket", "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        assert "myws" in str(created) or "internal" in str(created), \
            f"Expected ticket in workspace dir, got: {created}"
        assert created.exists()

    def test_index_regenerated(self, tmp_path):
        """INDEX.md is rewritten after ticket creation."""
        harness = _setup(tmp_path)
        original = (harness / "docs" / "tickets" / "INDEX.md").read_text()
        result = _run(harness, "Index test ticket")
        assert result.returncode == 0, result.stderr
        updated = (harness / "docs" / "tickets" / "INDEX.md").read_text()
        assert updated != original, "INDEX.md must be regenerated"

    def test_prints_created_path(self, tmp_path):
        """Script prints the absolute path of the created file to stdout."""
        harness = _setup(tmp_path)
        result = _run(harness, "Path print test")
        assert result.returncode == 0, result.stderr
        printed = result.stdout.strip()
        assert printed.endswith(".md"), f"Expected .md path in stdout, got: {printed!r}"
        assert Path(printed).exists()

    def test_unknown_workspace_exits_nonzero(self, tmp_path):
        """--workspace with non-existent slug exits 1."""
        harness = _setup(tmp_path)
        result = _run(harness, "Bad workspace", "--workspace", "does-not-exist")
        assert result.returncode != 0
        assert "ERROR" in result.stderr
