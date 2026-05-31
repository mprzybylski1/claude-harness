"""Tests for T148: create_ticket.py --problem TEXT flag.

--problem replaces the '(Describe the problem here.)' placeholder in ## Problem.
Combined with --ac, a single invocation produces a close-ready ticket with no
placeholder residue (but ACs remain unchecked — they're criteria to verify, not
auto-ticked).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
import create_ticket  # noqa: E402


class TestProblemInTemplate:
    def test_problem_replaces_placeholder(self):
        content = create_ticket._TEMPLATE.format(
            ticket_id="T999", title="test", severity="medium", phase="2",
            layer="tooling", repo_line="", session="S1", today="2026-01-01",
            acs="- [ ] done",
        )
        result = create_ticket._apply_problem(content, "The widget crashes on startup.")
        assert "The widget crashes on startup." in result
        assert "(Describe the problem here.)" not in result

    def test_without_problem_placeholder_preserved(self):
        content = create_ticket._TEMPLATE.format(
            ticket_id="T999", title="test", severity="medium", phase="2",
            layer="tooling", repo_line="", session="S1", today="2026-01-01",
            acs="- [ ] done",
        )
        assert "(Describe the problem here.)" in content

    def test_combined_with_ac_no_placeholder_residue(self):
        content = create_ticket._TEMPLATE.format(
            ticket_id="T999", title="test", severity="medium", phase="2",
            layer="tooling", repo_line="", session="S1", today="2026-01-01",
            acs="- [ ] First AC\n- [ ] Second AC",
        )
        result = create_ticket._apply_problem(content, "Real problem text.")
        assert "(Describe the problem here.)" not in result
        assert "(fill in)" not in result
        assert "Real problem text." in result
        assert "- [ ] First AC" in result
