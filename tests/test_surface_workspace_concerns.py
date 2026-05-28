"""Tests for T110: surface_workspace_concerns.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "surface_workspace_concerns.py"


def _make_sr(
    raised_dir: Path,
    sr_id: str,
    slug: str,
    title: str,
    status: str = "raised",
    severity: str = "medium",
    harness_ticket: str = "",
    resolved_in: str = "",
) -> Path:
    raised_dir.mkdir(parents=True, exist_ok=True)
    (raised_dir / "archive").mkdir(exist_ok=True)
    content = (
        f"---\n"
        f"id: {sr_id}\n"
        f"from: {slug}\n"
        f"raised: S5 2026-05-27\n"
        f"title: {title}\n"
        f"severity: {severity}\n"
        f"status: {status}\n"
        f"harness_ticket: {harness_ticket}\n"
        f"resolved_in: {resolved_in}\n"
        f"---\n\n## Context\n\nSome context.\n"
    )
    path = raised_dir / f"{sr_id}-{title.lower().replace(' ', '-')[:30]}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _setup(tmp_path: Path, slug: str = "myws") -> tuple[Path, Path]:
    """Minimal harness skeleton. Returns (harness, raised_dir)."""
    ws_dir = tmp_path / "workspaces" / slug
    ws_dir.mkdir(parents=True)
    (ws_dir / "workspace.yaml").write_text(f"name: {slug}\n", encoding="utf-8")
    raised_dir = ws_dir / "raised"
    raised_dir.mkdir()
    (raised_dir / "archive").mkdir()
    return tmp_path, raised_dir


def _run(harness: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
        cwd=str(cwd or harness),
        env={**_os.environ, "HARNESS_ROOT": str(harness), "PYTHONPATH": str(ROOT)},
    )


class TestSurfaceWorkspaceConcerns:

    def test_no_concerns_produces_no_output(self, tmp_path):
        """Empty raised/ produces no stdout at all."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == ""

    def test_active_raised_item_shown(self, tmp_path):
        """raised status SR appears under Active section."""
        harness, raised = _setup(tmp_path)
        _make_sr(raised, "SR-001", "myws", "Fix the thing", status="raised")
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert "SR-001" in result.stdout
        assert "Fix the thing" in result.stdout

    def test_active_promoted_item_shown(self, tmp_path):
        """promoted SR appears under Active section with ticket reference."""
        harness, raised = _setup(tmp_path)
        _make_sr(raised, "SR-001", "myws", "Promoted thing",
                 status="promoted", harness_ticket="T999")
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert "SR-001" in result.stdout
        assert "T999" in result.stdout

    def test_terminal_resolved_shown_once(self, tmp_path):
        """resolved SR appears in output on first run."""
        harness, raised = _setup(tmp_path)
        _make_sr(raised, "SR-002", "myws", "Done concern",
                 status="resolved", resolved_in="S19")
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert "SR-002" in result.stdout
        assert "Done concern" in result.stdout

    def test_terminal_rejected_shown_once(self, tmp_path):
        """rejected SR appears in output on first run."""
        harness, raised = _setup(tmp_path)
        _make_sr(raised, "SR-003", "myws", "Rejected thing",
                 status="rejected", resolved_in="S18")
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert "SR-003" in result.stdout

    def test_terminal_items_archived_after_surfacing(self, tmp_path):
        """After first run, resolved/rejected files are moved to raised/archive/."""
        harness, raised = _setup(tmp_path)
        sr = _make_sr(raised, "SR-002", "myws", "Done concern",
                      status="resolved", resolved_in="S19")
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert not sr.exists(), "SR should have been moved to archive"
        archive_files = list((raised / "archive").glob("SR-002-*.md"))
        assert len(archive_files) == 1

    def test_second_run_shows_no_terminal(self, tmp_path):
        """After first run archives terminal items, second run shows nothing."""
        harness, raised = _setup(tmp_path)
        _make_sr(raised, "SR-002", "myws", "Done concern",
                 status="resolved", resolved_in="S19")
        _run(harness, "--workspace", "myws")  # first run archives
        result = _run(harness, "--workspace", "myws")  # second run
        assert result.returncode == 0, result.stderr
        assert "SR-002" not in result.stdout

    def test_excludes_archive_subdirectory(self, tmp_path):
        """Files already in raised/archive/ are not surfaced."""
        harness, raised = _setup(tmp_path)
        archive = raised / "archive"
        (archive / "SR-001-old.md").write_text(
            "---\nid: SR-001\nstatus: resolved\ntitle: Old\n"
            "severity: low\nfrom: myws\nraised: S1 2026-01-01\n"
            "harness_ticket:\nresolved_in: S10\n---\n",
            encoding="utf-8",
        )
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == ""

    def test_active_not_archived(self, tmp_path):
        """Active (raised/promoted) items are NOT moved to archive."""
        harness, raised = _setup(tmp_path)
        sr = _make_sr(raised, "SR-001", "myws", "Active concern", status="raised")
        _run(harness, "--workspace", "myws")
        assert sr.exists(), "Active SR must not be archived"

    def test_cwd_workspace_detection(self, tmp_path):
        """Auto-detects workspace slug when CWD is inside workspaces/<slug>/."""
        harness, raised = _setup(tmp_path)
        _make_sr(raised, "SR-001", "myws", "Auto-detect test")
        ws_dir = harness / "workspaces" / "myws"
        result = _run(harness, cwd=ws_dir)
        assert result.returncode == 0, result.stderr
        assert "SR-001" in result.stdout

    def test_unknown_workspace_exits_nonzero(self, tmp_path):
        """--workspace with non-existent slug exits non-zero."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "--workspace", "no-such-ws")
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_no_workspace_context_exits_nonzero(self, tmp_path):
        """Missing --workspace and non-workspace CWD exits non-zero."""
        harness, _ = _setup(tmp_path)
        result = _run(harness)  # cwd=harness root, not a workspace
        assert result.returncode != 0


def _git_init(tmp_path: Path) -> None:
    """Initialize a git repo at tmp_path with one initial commit."""
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "commit.gpgsign", "false"], check=True)


def _git_status_porcelain(tmp_path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout


def _stub_current_session(tmp_path: Path, session: str = "S42") -> None:
    """Drop a stub current_session.py into tmp_path/scripts/tools/ that prints `session`."""
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "current_session.py").write_text(
        f"import sys\nprint({session!r})\n", encoding="utf-8"
    )


class TestGitStaging:
    """T121: terminal archive moves are staged in git so they appear in the
    session-close commit instead of accumulating as uncommitted changes.

    T126 (Option A) extends this: after staging, the moves are committed in an
    isolated chore commit so they no longer accumulate at all.
    """

    def test_archived_terminal_is_committed(self, tmp_path):
        """T126: archive moves are auto-committed; nothing remains staged."""
        harness, raised = _setup(tmp_path)
        _git_init(tmp_path)
        _stub_current_session(tmp_path, "S42")
        sr = _make_sr(raised, "SR-002", "myws", "Done", status="resolved", resolved_in="S19")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(sr)], check=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-q", "-m", "initial"],
            check=True,
        )
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert sr.exists() is False

        # Nothing staged or unstaged related to SR-002 — it was committed
        status = _git_status_porcelain(tmp_path)
        assert "SR-002" not in status, (
            f"After auto-commit, SR-002 must not appear in git status: {status!r}"
        )

        # The HEAD commit's message includes the session id and 'auto-archive'
        head_msg = subprocess.run(
            ["git", "-C", str(tmp_path), "log", "-1", "--pretty=%s"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        assert "auto-archive" in head_msg, head_msg
        assert "S42" in head_msg, head_msg

    def test_unrelated_staged_changes_preserved(self, tmp_path):
        """T126: auto-commit must NOT sweep up unrelated staged work."""
        harness, raised = _setup(tmp_path)
        _git_init(tmp_path)
        _stub_current_session(tmp_path, "S42")
        sr = _make_sr(raised, "SR-002", "myws", "Done", status="resolved", resolved_in="S19")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(sr)], check=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-q", "-m", "initial"],
            check=True,
        )
        # Pre-stage an unrelated file
        unrelated = tmp_path / "unrelated.txt"
        unrelated.write_text("hello\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(unrelated)], check=True)

        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        # unrelated.txt must still be staged (not committed)
        status = _git_status_porcelain(tmp_path)
        lines = [ln for ln in status.splitlines() if "unrelated.txt" in ln]
        assert lines, f"unrelated.txt must remain staged: {status!r}"
        for line in lines:
            assert line[0] == "A", (
                f"unrelated.txt must be staged-added, not committed: {line!r}"
            )

    def test_commit_failure_leaves_staged(self, tmp_path):
        """T126: if commit fails (e.g. signing issue, hook rejection), fall back
        to today's behaviour — moves remain staged, warning printed."""
        harness, raised = _setup(tmp_path)
        _git_init(tmp_path)
        _stub_current_session(tmp_path, "S42")
        sr = _make_sr(raised, "SR-002", "myws", "Done", status="resolved", resolved_in="S19")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(sr)], check=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-q", "-m", "initial"],
            check=True,
        )
        # Install a pre-commit hook that always rejects — forces commit to fail
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho 'pre-commit reject' >&2\nexit 1\n")
        hook.chmod(0o755)

        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert "auto-commit of archive moves failed" in result.stderr, result.stderr

        # Move still happened — file is in archive, source deleted
        archive_files = list((raised / "archive").glob("SR-002-*.md"))
        assert len(archive_files) == 1

        # Staged state preserved (delete of source + add of dest)
        status = _git_status_porcelain(tmp_path)
        sr_lines = [ln for ln in status.splitlines() if "SR-002" in ln]
        assert sr_lines, f"Expected SR-002 still staged after commit failure: {status!r}"
        for line in sr_lines:
            assert line[0] != " " or line[0] == "R", (
                f"SR-002 must remain staged (index column non-blank): {line!r}"
            )

    def test_works_outside_git_repo(self, tmp_path):
        """Best-effort staging: if not in a git repo, archive still proceeds."""
        harness, raised = _setup(tmp_path)
        # No git init — tmp_path is not a git repo
        sr = _make_sr(raised, "SR-002", "myws", "Done", status="resolved", resolved_in="S19")
        result = _run(harness, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert not sr.exists()
        archive_files = list((raised / "archive").glob("SR-002-*.md"))
        assert len(archive_files) == 1
