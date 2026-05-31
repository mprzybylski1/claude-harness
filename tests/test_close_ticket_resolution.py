"""Tests for T144/T145: close_ticket.py _replace_resolution append mode + clearer
missing-placeholder error.

Default (replace) mode finds the '(Fill in on close.)' placeholder and replaces it.
Append mode (--append) preserves an already-populated Resolution section — the rich
content authored during the work — and adds the one-line resolution + close stamp at
the end. When the default path finds no placeholder, the error must name both
remediations rather than the opaque "ticket format unexpected".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
import close_ticket  # noqa: E402

_R = close_ticket._replace_resolution


def _ticket(resolution_body: str) -> str:
    return (
        "---\nid: T999\nstatus: open\n---\n\n"
        "## Problem\n\nSynthetic.\n\n"
        "## Resolution\n" + resolution_body + "\n"
    )


class TestReplaceMode:
    def test_placeholder_replaced(self):
        out = _R(_ticket("(Fill in on close.)"), "Did the thing.")
        assert "Did the thing." in out
        assert "(Fill in on close.)" not in out

    def test_missing_placeholder_error_names_both_remediations(self, capsys):
        ticket = _ticket("Rich content already written during the work.")
        with pytest.raises(SystemExit) as exc:
            _R(ticket, "summary")
        assert exc.value.code == 2
        err = capsys.readouterr().err
        # T145: must point at both fixes, not say "ticket format unexpected".
        assert "--append" in err
        assert "Fill in on close" in err
        assert "ticket format unexpected" not in err


class TestAppendMode:
    def test_preserves_existing_content_and_adds_resolution_at_end(self):
        body = "Rich content authored during the work.\nSecond line."
        out = _R(_ticket(body), "One-line summary.\n\nClosed S26 2026-05-31.", append=True)
        # Existing content survives...
        assert "Rich content authored during the work." in out
        assert "Second line." in out
        # ...and the appended summary follows it (content leads, summary trails).
        assert out.index("Rich content authored") < out.index("One-line summary.")
        assert "Closed S26 2026-05-31." in out

    def test_does_not_disturb_following_sections(self):
        ticket = (
            "## Resolution\nExisting body.\n\n## Notes\nkeep me\n"
        )
        out = _R(ticket, "summary", append=True)
        assert "## Notes\nkeep me\n" in out
        assert "Existing body." in out
        assert "summary" in out
        # summary must land inside Resolution, before ## Notes
        assert out.index("summary") < out.index("## Notes")

    def test_append_errors_when_only_placeholder(self, capsys):
        with pytest.raises(SystemExit) as exc:
            _R(_ticket("(Fill in on close.)"), "summary", append=True)
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "--append" in err  # tells the operator to drop --append

    def test_append_errors_when_section_empty(self, capsys):
        with pytest.raises(SystemExit) as exc:
            _R(_ticket(""), "summary", append=True)
        assert exc.value.code == 2

    def test_append_errors_when_no_resolution_header(self, capsys):
        with pytest.raises(SystemExit) as exc:
            _R("## Problem\n\nNo resolution section here.\n", "summary", append=True)
        assert exc.value.code == 2
