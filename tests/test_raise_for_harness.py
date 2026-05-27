"""Tests for T104: raise_for_harness.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "raise_for_harness.py"


def _setup(tmp_path: Path, slug: str = "myws") -> tuple[Path, Path]:
    """Minimal harness skeleton with one workspace. Returns (harness, ws_dir)."""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "sessions.md").write_text("## Session Log\n\nS9 2026-05-27: init\n", encoding="utf-8")
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text("print('S9')\n", encoding="utf-8")
    ws_dir = tmp_path / "workspaces" / slug
    ws_dir.mkdir(parents=True)
    (ws_dir / "workspace.yaml").write_text(f"name: {slug}\n", encoding="utf-8")
    return tmp_path, ws_dir


def _run(
    harness: Path, *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or harness),
        env={**_os.environ, "HARNESS_ROOT": str(harness), "PYTHONPATH": str(ROOT)},
    )


class TestRaiseForHarness:

    def test_happy_path_creates_file(self, tmp_path):
        """SR file created in boundary slot with correct frontmatter."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Database timeout bug", "--severity", "high",
                      "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        assert created.exists(), f"File not created at {created}"
        content = created.read_text(encoding="utf-8")
        assert "id: SR-001" in content
        assert "from: myws" in content
        assert "title: Database timeout bug" in content
        assert "severity: high" in content
        assert "status: raised" in content
        assert "harness_ticket:" in content

    def test_required_sections_present(self, tmp_path):
        """File body contains Context, Proposed change, and Harness disposition sections."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Any concern", "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "## Context" in content
        assert "## Proposed change" in content
        assert "## Harness disposition" in content

    def test_file_lands_in_boundary_slot(self, tmp_path):
        """Output path is workspaces/<slug>/raised/<SR>.md, not elsewhere."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Location test", "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        assert created.parent == harness / "workspaces" / "myws" / "raised"

    def test_sequence_number_increments(self, tmp_path):
        """SR-002 allocated when SR-001 already exists in raised/."""
        harness, ws_dir = _setup(tmp_path)
        raised = ws_dir / "raised"
        raised.mkdir()
        (raised / "SR-001-old.md").write_text("---\nid: SR-001\n---\n", encoding="utf-8")

        result = _run(harness, "Second concern", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "id: SR-002" in content

    def test_sequence_scans_archive(self, tmp_path):
        """SR number allocation includes raised/archive/ so archived SRs are never reused."""
        harness, ws_dir = _setup(tmp_path)
        raised = ws_dir / "raised"
        archive = raised / "archive"
        raised.mkdir()
        archive.mkdir()
        (archive / "SR-003-archived.md").write_text("---\nid: SR-003\n---\n", encoding="utf-8")

        result = _run(harness, "After archive gap", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "id: SR-004" in content

    def test_no_workspace_context_exits_nonzero(self, tmp_path):
        """Refuses without --workspace and CWD not inside a workspace directory."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Should fail")  # cwd=harness, not inside workspaces/
        assert result.returncode != 0
        assert "workspace" in result.stderr.lower()

    def test_unknown_workspace_exits_nonzero(self, tmp_path):
        """--workspace with non-existent slug exits non-zero with ERROR."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Bad slug", "--workspace", "does-not-exist")
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_cwd_workspace_detection(self, tmp_path):
        """Auto-detects workspace slug from CWD when inside workspaces/<slug>/."""
        harness, ws_dir = _setup(tmp_path)
        result = _run(harness, "Auto-detected workspace", cwd=ws_dir)
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "from: myws" in content

    def test_filename_slug_from_title(self, tmp_path):
        """Filename follows SR-NNN-<slug>.md pattern with title-derived slug."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Fix the broken widget", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        created = Path(result.stdout.strip())
        assert created.name.startswith("SR-001-")
        assert "fix" in created.name
        assert created.name.endswith(".md")

    def test_archive_dir_created_automatically(self, tmp_path):
        """raised/archive/ is created if it does not exist."""
        harness, ws_dir = _setup(tmp_path)
        result = _run(harness, "Any concern", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert (ws_dir / "raised" / "archive").is_dir()
