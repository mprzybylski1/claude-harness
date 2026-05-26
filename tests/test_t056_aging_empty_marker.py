"""tests/test_t056_aging_empty_marker.py

TDD tests for T056: AGING_EMPTY_MARKER constant must be defined in a shared
module (ticket_constants.py) and both generate_ticket_index.py and
surface_stale_tickets.py must reference it instead of the duplicated literal.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))


class TestAgingEmptyMarkerConstant:
    """ticket_constants.py must export AGING_EMPTY_MARKER."""

    def test_ticket_constants_module_exists(self):
        """ticket_constants.py must be importable."""
        import ticket_constants  # noqa: F401

    def test_aging_empty_marker_value(self):
        """AGING_EMPTY_MARKER must equal '*(none)*'."""
        from ticket_constants import AGING_EMPTY_MARKER
        assert AGING_EMPTY_MARKER == "*(none)*"

    def test_generate_ticket_index_imports_constant(self):
        """generate_ticket_index.py must import AGING_EMPTY_MARKER from ticket_constants."""
        import generate_ticket_index as gti
        # The constant must be accessible from the module namespace
        assert hasattr(gti, "AGING_EMPTY_MARKER"), (
            "generate_ticket_index must import AGING_EMPTY_MARKER from ticket_constants"
        )

    def test_surface_stale_tickets_imports_constant(self):
        """surface_stale_tickets.py must import AGING_EMPTY_MARKER from ticket_constants."""
        import surface_stale_tickets as sst
        assert hasattr(sst, "AGING_EMPTY_MARKER"), (
            "surface_stale_tickets must import AGING_EMPTY_MARKER from ticket_constants"
        )

    def test_constant_values_are_identical(self):
        """Both modules must reference the same constant object (not copies)."""
        import generate_ticket_index as gti
        import surface_stale_tickets as sst
        assert gti.AGING_EMPTY_MARKER == sst.AGING_EMPTY_MARKER == "*(none)*"


class TestAgingEmptyMarkerUsedInOutput:
    """generate_ticket_index emits AGING_EMPTY_MARKER in the aging section."""

    def test_generate_ticket_index_emits_marker_when_no_aging(self, tmp_path):
        """When no tickets exceed the aging threshold, AGING_EMPTY_MARKER appears in output."""
        import generate_ticket_index as gti
        from ticket_constants import AGING_EMPTY_MARKER

        # Fresh ticket — 0 sessions old, well below AGING_THRESHOLD of 10
        tickets = [
            {
                "id": "T001",
                "title": "Test ticket",
                "severity": "low",
                "opened": "S10 2026-05-26",
                "phase": "2",
                "layer": "infra",
                "filename": "T001-test.md",
            }
        ]

        output = gti.render_index(tickets, current_session=10, today="2026-05-26")
        assert AGING_EMPTY_MARKER in output, (
            f"Expected {AGING_EMPTY_MARKER!r} in aging section output.\n"
            f"Output was:\n{output}"
        )


class TestAgingEmptyMarkerUsedInParser:
    """surface_stale_tickets uses AGING_EMPTY_MARKER to detect clean state."""

    def test_parse_aging_section_recognises_marker(self, tmp_path):
        """parse_aging_section returns section_found=True when INDEX.md contains AGING_EMPTY_MARKER."""
        import surface_stale_tickets as sst
        from ticket_constants import AGING_EMPTY_MARKER

        index_md = tmp_path / "INDEX.md"
        index_md.write_text(
            f"# Ticket Index\n\n## Aging Tickets (open >= 10 sessions)\n\n{AGING_EMPTY_MARKER}\n",
            encoding="utf-8",
        )

        result = sst.parse_aging_section(index_path=index_md, threshold=50)
        assert result.section_found is True
        assert result.tickets == []
