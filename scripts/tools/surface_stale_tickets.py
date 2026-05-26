#!/usr/bin/env python3
"""
Print a triage warning for any open ticket exceeding the stale-session threshold.

Reads the "## Aging Tickets" section of docs/tickets/INDEX.md and prints:
  TRIAGE NEEDED: T026 (76s) — close, defer to Phase 4+, or schedule

Threshold: TRIAGE_THRESHOLD env var (default: 50 sessions).
Prints nothing if no tickets exceed the threshold.

Usage:
    python scripts/tools/surface_stale_tickets.py
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX_MD = ROOT / "docs" / "tickets" / "INDEX.md"

TRIAGE_THRESHOLD = int(os.environ.get("TRIAGE_THRESHOLD", "50"))


class ParseResult:
    """Result of parsing the Aging Tickets section."""
    def __init__(
        self,
        tickets: list[tuple[str, int, str]],
        section_found: bool,
        parse_warning: str | None = None,
    ) -> None:
        self.tickets = tickets
        self.section_found = section_found
        self.parse_warning = parse_warning


def parse_aging_section(index_path: Path = INDEX_MD, threshold: int = TRIAGE_THRESHOLD) -> ParseResult:
    """
    Parse the Aging Tickets section of INDEX.md.

    Returns a ParseResult with three states:
    1. section_found=True, tickets non-empty  → tickets above threshold found
    2. section_found=True, tickets empty      → section parsed cleanly, none above threshold
    3. section_found=False                    → section missing or regex matched zero entries
                                                when the section header exists (format drift)
    """
    if not index_path.exists():
        return ParseResult([], section_found=False, parse_warning=f"{index_path} not found")

    content = index_path.read_text()

    aging_match = re.search(r"## Aging Tickets.*?$", content, re.MULTILINE)
    if not aging_match:
        # Section absent = no tickets old enough to appear — clean state, not an error.
        return ParseResult([], section_found=True)

    aging_section = content[aging_match.start():]

    pattern = re.compile(
        r"-\s+\*\*(T\d+)\*\*\s+—\s+(.+?)\s+\(open\s+(\d+)\s+sessions",
        re.MULTILINE,
    )
    all_entries = list(pattern.finditer(aging_section))

    if not all_entries:
        # Header exists but zero list items matched — likely format drift
        return ParseResult(
            [],
            section_found=False,
            parse_warning="surface_stale_tickets.py could not parse INDEX.md aging section — format may have drifted",
        )

    results = []
    for m in all_entries:
        ticket_id = m.group(1)
        title = m.group(2).strip()
        age = int(m.group(3))
        if age >= threshold:
            results.append((ticket_id, age, title))

    return ParseResult(sorted(results, key=lambda x: x[1], reverse=True), section_found=True)


def get_stale_tickets(index_path: Path = INDEX_MD, threshold: int = TRIAGE_THRESHOLD) -> list[tuple[str, int, str]]:
    """Return (ticket_id, age, title) for tickets exceeding threshold. Backwards-compatible."""
    return parse_aging_section(index_path, threshold).tickets


def main() -> None:
    result = parse_aging_section()
    if result.parse_warning:
        print(f"WARNING: {result.parse_warning}", file=sys.stderr)
        return
    if not result.tickets:
        return
    print("TRIAGE REQUIRED — tickets open too long without a decision:")
    for ticket_id, age, title in result.tickets:
        short_title = title if len(title) <= 55 else title[:52] + "..."
        print(f"  {ticket_id} ({age}s): {short_title} — close, defer, or schedule")


if __name__ == "__main__":
    main()
