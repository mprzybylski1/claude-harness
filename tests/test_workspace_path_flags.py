"""
Tests for T020 + T022: workspace path flag support in session-start / session-close scripts.

Each test verifies that when a script is invoked with a workspace path flag it reads
from that path, not from the harness-root default.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "scripts" / "tools"

# ── Minimal file fixtures ─────────────────────────────────────────────────────

SESSIONS_MD = """\
# Sessions

## Current Phase & Status

Phase 99 (Testing).

## Active Work

**S000 — test session**

## Session Log

S0 2000-01-01: initial
S42 2026-01-15: test entry
"""

OPUS_NOTES_MD = """\
# Opus Notes

# Opus Review — S42 2026-01-15

## Invariant Violations

None.

## Architectural Concerns

None.

## Suggested Next Session Focus

1. Keep testing.
"""


# ── T020: current_session.py --sessions ───────────────────────────────────────

class TestCurrentSessionFlag:
    def test_reads_from_custom_sessions_path(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        sessions.write_text(SESSIONS_MD)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"), "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "S43"

    def test_custom_path_is_independent_of_harness_root(self, tmp_path):
        # Create a sessions.md with a different session number than harness root
        sessions = tmp_path / "ws_sessions.md"
        sessions.write_text(SESSIONS_MD.replace("S42", "S7"))
        result = subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"), "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "S8"

    def test_missing_custom_sessions_exits_nonzero(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"),
             "--sessions", str(tmp_path / "nonexistent.md")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ── T020: extract_session_brief.py --sessions ─────────────────────────────────

class TestExtractSessionBriefFlag:
    def test_reads_from_custom_sessions_path(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        sessions.write_text(SESSIONS_MD)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_session_brief.py"),
             "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Phase 99" in result.stdout

    def test_custom_path_excludes_harness_root_content(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        # Write content that differs from harness-root sessions.md
        sessions.write_text(SESSIONS_MD.replace("Phase 99", "Phase WORKSPACE-ONLY"))
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_session_brief.py"),
             "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert "WORKSPACE-ONLY" in result.stdout

    def test_missing_custom_sessions_exits_nonzero(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_session_brief.py"),
             "--sessions", str(tmp_path / "nonexistent.md")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ── T020: extract_opus_key_sections.py --opus ─────────────────────────────────

class TestExtractOpusKeySectionsFlag:
    def test_reads_from_custom_opus_path(self, tmp_path):
        opus = tmp_path / "opus_notes.md"
        opus.write_text(OPUS_NOTES_MD)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(opus)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "S42" in result.stdout

    def test_custom_path_excludes_harness_root_content(self, tmp_path):
        opus = tmp_path / "opus_notes.md"
        # Write content with a unique marker
        opus.write_text(OPUS_NOTES_MD.replace("S42 2026-01-15", "S999 2030-06-01"))
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(opus)],
            capture_output=True, text=True,
        )
        assert "S999" in result.stdout

    def test_missing_custom_opus_exits_nonzero(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(tmp_path / "nonexistent.md")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ── T022: archive_session_log.py --sessions / --archive ──────────────────────

class TestArchiveSessionLogFlags:
    def _make_sessions(self, path: Path, n_entries: int = 80) -> None:
        entries = "\n".join(
            f"S{i} 2026-01-{(i % 28) + 1:02d}: session {i}"
            for i in range(1, n_entries + 1)
        )
        path.write_text(
            "# Sessions\n\n## Current Phase & Status\n\nPhase 1.\n\n"
            "## Active Work\n\nActive.\n\n## Session Log\n\n" + entries + "\n",
            encoding="utf-8",
        )

    def test_reads_from_custom_sessions_path(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        archive = tmp_path / "archive" / "session_log_archive.md"
        self._make_sessions(sessions, n_entries=80)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "archive_session_log.py"),
             "--sessions", str(sessions), "--archive", str(archive),
             "--threshold", "75", "--keep", "30"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert archive.exists(), "archive file should be created"
        content = sessions.read_text()
        # Only 30 entries should remain
        remaining = [ln for ln in content.splitlines() if ln.startswith("S")]
        assert len(remaining) == 30

    def test_does_not_touch_harness_root_sessions(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        archive = tmp_path / "archive" / "log.md"
        self._make_sessions(sessions, n_entries=10)
        harness_sessions = ROOT / "docs" / "sessions.md"
        harness_mtime_before = harness_sessions.stat().st_mtime if harness_sessions.exists() else None
        subprocess.run(
            [sys.executable, str(TOOLS / "archive_session_log.py"),
             "--sessions", str(sessions), "--archive", str(archive)],
            capture_output=True, text=True,
        )
        if harness_mtime_before is not None:
            assert harness_sessions.stat().st_mtime == harness_mtime_before


# ── T022: rotate_opus_notes.py --opus / --archive ────────────────────────────

class TestRotateOpusNotesFlags:
    def _make_opus(self, path: Path, n_sections: int = 3) -> None:
        header = "# Opus Notes\n\n"
        sections = "\n\n".join(
            f"# Opus Review — S{i} 2026-01-{i:02d}\n\n"
            f"## Invariant Violations\n\nNone.\n\n"
            f"## Architectural Concerns\n\nNone.\n"
            for i in range(1, n_sections + 1)
        )
        path.write_text(header + sections + "\n")

    def test_rotates_using_custom_opus_and_archive(self, tmp_path):
        opus = tmp_path / "opus_notes.md"
        archive_dir = tmp_path / "archive"
        self._make_opus(opus, n_sections=3)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "rotate_opus_notes.py"),
             "--opus", str(opus), "--archive", str(archive_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        # After rotation, exactly 1 section should remain
        content = opus.read_text()
        sections = [ln for ln in content.splitlines() if ln.startswith("# Opus Review")]
        assert len(sections) == 1
        # Archive directory should have been created
        assert archive_dir.exists()

    def test_does_not_touch_harness_root_opus(self, tmp_path):
        opus = tmp_path / "opus_notes.md"
        archive_dir = tmp_path / "archive"
        self._make_opus(opus, n_sections=2)
        harness_opus = ROOT / "docs" / "opus_notes.md"
        harness_mtime_before = harness_opus.stat().st_mtime if harness_opus.exists() else None
        subprocess.run(
            [sys.executable, str(TOOLS / "rotate_opus_notes.py"),
             "--opus", str(opus), "--archive", str(archive_dir)],
            capture_output=True, text=True,
        )
        if harness_mtime_before is not None:
            assert harness_opus.stat().st_mtime == harness_mtime_before
