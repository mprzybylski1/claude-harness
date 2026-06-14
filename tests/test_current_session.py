"""
Tests for current_session.get_current_session, focused on T149: a clearer error
when sessions.md exists with content but has no S<N> YYYY-MM-DD: entries (e.g. a
markdown-table scaffold), which previously blocked create_ticket invisibly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
import current_session  # noqa: E402


class TestGetCurrentSession:
    def test_happy_path_unchanged(self, tmp_path):
        sm = tmp_path / "sessions.md"
        sm.write_text("## Session Log\n\nS11 2026-06-01: a\nS12 2026-06-02: b\n")
        assert current_session.get_current_session(sm) == 13

    def test_missing_file(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            current_session.get_current_session(tmp_path / "nope.md")
        assert exc.value.code == 1
        assert "not found" in capsys.readouterr().err

    def test_wrong_format_shows_first_line_and_expected_pattern(self, tmp_path, capsys):
        """A file with content but no S<N> match prints the first non-blank line + pattern."""
        sm = tmp_path / "sessions.md"
        sm.write_text(
            "\n\n| Session | Date | Notes |\n|---|---|---|\n| 1 | 2026-06-01 | start |\n"
        )
        with pytest.raises(SystemExit) as exc:
            current_session.get_current_session(sm)
        assert exc.value.code == 1
        err = capsys.readouterr().err
        # First non-blank line surfaced
        assert "| Session | Date | Notes |" in err
        # Expected pattern surfaced
        assert "YYYY-MM-DD" in err

    def test_empty_file_says_empty(self, tmp_path, capsys):
        sm = tmp_path / "sessions.md"
        sm.write_text("\n   \n\n")
        with pytest.raises(SystemExit) as exc:
            current_session.get_current_session(sm)
        assert exc.value.code == 1
        assert "empty" in capsys.readouterr().err.lower()
