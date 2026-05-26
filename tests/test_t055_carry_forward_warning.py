"""tests/test_t055_carry_forward_warning.py

TDD tests for T055: carry-forward warning must be surfaced to the user when
extract_opus_key_sections.py calls extract_carry_forwards.py and the latter
emits a warning because no session-number header was found in opus_notes.md.

The warning from extract_carry_forwards.py appears on stderr; the caller
must re-emit it as a 'Note:' line in stdout so the user sees it regardless
of invocation mode.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))


def _make_opus_notes_with_review(tmp_path: Path, has_session_header: bool, has_session_ref: bool) -> Path:
    """Create opus_notes.md that passes main() but optionally triggers the warning.

    main() requires a '# Opus Review' section. The carry-forward warning fires
    when there are 'carry-forward from S<N>' lines but NO 'Opus Review — SN' header
    (the session number header).  Both can coexist: the file can have a bare
    '# Opus Review' (no session number) plus session-ref carry-forward lines.
    """
    lines = []
    if has_session_header:
        # Full header with session number — no warning will fire
        lines.append("# Opus Review — S10")
    else:
        # Bare header — passes main() but has no session number → warning fires
        lines.append("# Opus Review")
    lines.append("")
    lines.append("## Invariant Violations")
    lines.append("")
    lines.append("*(none)*")
    lines.append("")
    if has_session_ref:
        # A carry-forward line using the session-reference pattern
        lines.append("- **SomeIssue** — carry-forward from S7")
        lines.append("")
    p = tmp_path / "opus_notes.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


class TestRunWithCarryForwards:
    """extract_opus_key_sections.run_with_carry_forwards() must surface warnings."""

    def test_warning_appears_in_stdout_when_no_session_header(self, tmp_path):
        """When no 'Opus Review — SN' header exists, a Note: line appears in stdout."""
        import extract_opus_key_sections as eks

        # No session-number header → extract_carry_forwards warns
        notes = _make_opus_notes_with_review(
            tmp_path, has_session_header=False, has_session_ref=True
        )

        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        with patch("sys.stdout", captured_stdout), patch("sys.stderr", captured_stderr):
            eks.run_with_carry_forwards(notes_file=notes)

        stdout_text = captured_stdout.getvalue()
        assert "Note:" in stdout_text, (
            f"Expected 'Note:' in stdout when carry-forward warning exists.\n"
            f"stdout was:\n{stdout_text!r}"
        )

    def test_no_note_when_session_header_present(self, tmp_path):
        """When the session header is present, no spurious Note: line appears."""
        import extract_opus_key_sections as eks

        notes = _make_opus_notes_with_review(
            tmp_path, has_session_header=True, has_session_ref=True
        )

        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        with patch("sys.stdout", captured_stdout), patch("sys.stderr", captured_stderr):
            eks.run_with_carry_forwards(notes_file=notes)

        stdout_text = captured_stdout.getvalue()
        assert "Note:" not in stdout_text, (
            f"Unexpected 'Note:' in stdout when no warning should exist.\n"
            f"stdout was:\n{stdout_text!r}"
        )

    def test_note_contains_meaningful_context(self, tmp_path):
        """The Note: line contains enough text to be actionable."""
        import extract_opus_key_sections as eks

        notes = _make_opus_notes_with_review(
            tmp_path, has_session_header=False, has_session_ref=True
        )

        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        with patch("sys.stdout", captured_stdout), patch("sys.stderr", captured_stderr):
            eks.run_with_carry_forwards(notes_file=notes)

        stdout_text = captured_stdout.getvalue()
        # The note should reference carry-forward or session so the user knows what happened
        note_lines = [ln for ln in stdout_text.splitlines() if "Note:" in ln]
        assert note_lines, "No Note: line found"
        note_content = " ".join(note_lines).lower()
        assert "carry" in note_content or "session" in note_content, (
            f"Note: line should mention 'carry' or 'session'.\nGot: {note_lines}"
        )

    def test_no_note_when_no_session_ref_lines(self, tmp_path):
        """When there are no session-ref carry-forward lines, no warning fires and no Note:."""
        import extract_opus_key_sections as eks

        notes = _make_opus_notes_with_review(
            tmp_path, has_session_header=False, has_session_ref=False
        )

        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()
        with patch("sys.stdout", captured_stdout), patch("sys.stderr", captured_stderr):
            eks.run_with_carry_forwards(notes_file=notes)

        stdout_text = captured_stdout.getvalue()
        assert "Note:" not in stdout_text, (
            f"No warning should fire when there are no session-ref lines.\n"
            f"stdout was:\n{stdout_text!r}"
        )
