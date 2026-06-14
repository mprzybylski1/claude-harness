"""
Tests for T165: check_session_continuity.py — advisory session-start guard that
detects when the about-to-be-used session number S<N> was already stamped on
tickets by a prior, unlogged session (a numbering collision).

Intended caller is /session-start (before this session creates any S<N> work), so
an exact session-number match is the signal — no date filter (that would break for
sessions spanning midnight).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "check_session_continuity.py"

SESSIONS_S29 = "## Session Log\n\nS28 2026-06-01: x\nS29 2026-06-01: y\n"


def _ticket(session: int, dt: str, tid: str = "T157") -> str:
    return (
        f"---\nid: {tid}\ntitle: ghost\nseverity: low\nstatus: open\n"
        f"opened: S{session} {dt}\nclosed:\n---\n\n## Problem\n\nx\n"
    )


def _tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    sessions = tmp_path / "sessions.md"
    sessions.write_text(SESSIONS_S29)
    open_dir = tmp_path / "open"
    archive_dir = tmp_path / "archive"
    open_dir.mkdir()
    archive_dir.mkdir()
    return sessions, open_dir, archive_dir


def _run(sessions: Path, open_dir: Path, archive_dir: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--sessions", str(sessions),
         "--tickets-dir", str(open_dir),
         "--archive-dir", str(archive_dir)],
        capture_output=True, text=True,
    )


class TestSessionContinuity:
    def test_flags_ghost_collision_in_archive(self, tmp_path):
        """Archived ticket stamped opened: S30 → warns (N derives to 30 from last-logged S29)."""
        sessions, open_dir, archive_dir = _tree(tmp_path)
        (archive_dir / "T157-ghost.md").write_text(_ticket(30, "2026-06-02", "T157"))

        result = _run(sessions, open_dir, archive_dir)
        assert result.returncode == 0, result.stderr
        assert "S30" in result.stdout
        assert "T157" in result.stdout
        assert "collision" in result.stdout.lower()

    def test_flags_ghost_in_open_dir(self, tmp_path):
        """Open-dir ticket is scanned too."""
        sessions, open_dir, archive_dir = _tree(tmp_path)
        (open_dir / "T158-ghost.md").write_text(_ticket(30, "2026-06-02", "T158"))

        result = _run(sessions, open_dir, archive_dir)
        assert "T158" in result.stdout

    def test_clean_when_no_collision(self, tmp_path):
        """Tickets stamped with older session numbers (not the current N) → no warning."""
        sessions, open_dir, archive_dir = _tree(tmp_path)
        (archive_dir / "T100-old.md").write_text(_ticket(28, "2026-06-01", "T100"))
        (archive_dir / "T101-old.md").write_text(_ticket(29, "2026-06-01", "T101"))

        result = _run(sessions, open_dir, archive_dir)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == ""

    def test_matches_exact_session_number_only(self, tmp_path):
        """A ticket stamped with the LAST-logged number (S29, not the current N=30) is not flagged."""
        sessions, open_dir, archive_dir = _tree(tmp_path)
        (open_dir / "T140-prev.md").write_text(_ticket(29, "2026-06-01", "T140"))

        result = _run(sessions, open_dir, archive_dir)
        assert result.stdout.strip() == ""

    def test_silent_when_sessions_missing(self, tmp_path):
        """No sessions.md → advisory check exits 0 with no output."""
        open_dir = tmp_path / "open"
        archive_dir = tmp_path / "archive"
        open_dir.mkdir()
        archive_dir.mkdir()
        result = _run(tmp_path / "nope.md", open_dir, archive_dir)
        assert result.returncode == 0
        assert result.stdout.strip() == ""
