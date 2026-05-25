#!/usr/bin/env python3
"""
Extract the three session-start-relevant sections from the most recent Opus review.

Reads docs/opus_notes.md, finds the last '# Opus Review' section, and prints
only these subsections:
  - ## Invariant Violations
  - ## Architectural Concerns
  - ## Suggested Next Session Focus

Everything else (Bugs, Session Notes Discrepancy, Minor Issues, Clean, Tickets)
is omitted. The older review section is ignored entirely.

Usage:
    python scripts/tools/extract_opus_key_sections.py

Prints the extracted sections to stdout.
Exits 1 if opus_notes.md is missing or contains no Opus Review sections.
"""
import re
import sys
from pathlib import Path

OPUS_NOTES = Path("docs/opus_notes.md")

KEEP_SECTIONS = {
    "invariant violations",
    "architectural concerns",
    "suggested next session focus",
}

# Sections that appear after the ones we want — stop extraction when hit
STOP_SECTIONS = {
    "bugs & implementation issues",
    "bugs and implementation issues",
    "session notes discrepancy",
    "minor issues",
    "tickets opened",
    "tickets closed",
    "clean",
}

# Max numbered items to show for verbose sections (rest summarised with a count)
SUGGESTED_FOCUS_MAX_ITEMS = 5


def _cap_numbered_list(block: str, max_items: int) -> str:
    """Truncate a numbered-list block to max_items entries, appending a count note."""
    import re as _re
    # Split on lines starting with a digit + period (numbered list items)
    item_pattern = _re.compile(r'(?=^\d+\.)', _re.MULTILINE)
    parts = item_pattern.split(block)
    # parts[0] is the section header; parts[1:] are the numbered items
    header = parts[0]
    items = parts[1:]
    total = len(items)
    if total <= max_items:
        return block
    kept = items[:max_items]
    trailer = f"\n_(showing {max_items}/{total} — full list in opus_notes.md)_"
    return header + "".join(kept).rstrip() + trailer


def main(opus_notes_path: Path | None = None) -> None:
    path = opus_notes_path if opus_notes_path is not None else OPUS_NOTES
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)

    text = path.read_text(encoding="utf-8")

    # Split into top-level review sections (## Opus Review — ...)
    review_pattern = re.compile(r"^# Opus Review", re.MULTILINE)
    boundaries = [m.start() for m in review_pattern.finditer(text)]

    if not boundaries:
        print(f"ERROR: no '# Opus Review' sections found in {OPUS_NOTES}", file=sys.stderr)
        sys.exit(1)

    # Take the LAST review section
    latest_start = boundaries[-1]
    latest_section = text[latest_start:]

    # Print the review header line
    header_end = latest_section.find("\n")
    print(latest_section[:header_end])
    print()

    # Walk through subsections (## ...) and print only the kept ones
    sub_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    sub_matches = list(sub_pattern.finditer(latest_section))

    for i, match in enumerate(sub_matches):
        title = match.group(1).strip()
        title_lower = title.lower()

        # Determine the content span: from this header to the next one
        content_start = match.start()
        content_end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(latest_section)
        block = latest_section[content_start:content_end].rstrip()

        if title_lower in KEEP_SECTIONS:
            if title_lower == "suggested next session focus":
                block = _cap_numbered_list(block, SUGGESTED_FOCUS_MAX_ITEMS)
            print(block)
            print()
        # else: skip


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser(add_help=False)
    _parser.add_argument("--with-carry-forwards", action="store_true")
    _parser.add_argument("--opus", default=None, metavar="PATH")
    _args, _ = _parser.parse_known_args()
    _opus_path = Path(_args.opus) if _args.opus else None
    main(_opus_path)
    if _args.with_carry_forwards:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from extract_carry_forwards import main as _cf_main
        _cf_main(notes_file=_opus_path)
