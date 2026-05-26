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

OPUS_NOTES = Path(__file__).resolve().parents[2] / "docs" / "opus_notes.md"

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

    # Split into top-level review sections — harness-root uses level-1 headers
    # ("# Opus Review"), workspace files use level-2 ("## Opus Review") because
    # the workspace file has a "# Opus Notes — <Project>" title at the top.
    review_pattern = re.compile(r"^#{1,2} Opus Review", re.MULTILINE)
    boundaries = [m.start() for m in review_pattern.finditer(text)]

    if not boundaries:
        print(f"ERROR: no '# Opus Review' sections found in {path}", file=sys.stderr)
        sys.exit(1)

    # Take the LAST review section
    latest_start = boundaries[-1]
    latest_section = text[latest_start:]

    # Print the review header line
    boundary_line = latest_section.split("\n", 1)[0]
    print(boundary_line)
    print()

    # Subsections are one level deeper than the review header:
    #   harness-root: "# Opus Review" → subsections are "## ..."
    #   workspace:    "## Opus Review" → subsections are "### ..."
    level = len(boundary_line) - len(boundary_line.lstrip("#"))
    sub_prefix = "#" * (level + 1)
    sub_pattern = re.compile(rf"^{sub_prefix} (.+)$", re.MULTILINE)
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


def run_with_carry_forwards(notes_file: Path | None = None) -> None:
    """Call extract_carry_forwards and re-emit any warning as a Note: line in stdout.

    When extract_carry_forwards cannot determine the current session number (e.g. the
    opus_notes.md file has 'carry-forward from S<N>' lines but no 'Opus Review — SN'
    header), it prints a WARNING to stderr.  When invoked as a subprocess or via import,
    that stderr message is discarded — the user sees an empty carry-forwards list with no
    explanation.  This function captures that stderr output and re-emits any warning as a
    'Note:' line in stdout so it reaches the user regardless of invocation mode.
    """
    import io
    import subprocess

    # Run extract_carry_forwards as a subprocess so we can capture its stderr cleanly
    # without interfering with the current process's stderr.
    script = Path(__file__).resolve().parent / "extract_carry_forwards.py"
    cmd = [sys.executable, str(script)]
    if notes_file is not None:
        # Pass notes path via environment; the script's main() uses sys.argv only for
        # --threshold, not for the notes file.  We call via import instead.
        pass

    # Import and call directly, capturing stderr via redirection
    import importlib
    captured_stderr = io.StringIO()
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    # We need a fresh stderr capture around the extract_carry_forwards call
    original_stderr = sys.stderr
    sys.stderr = captured_stderr
    try:
        # Import fresh each time (may already be cached)
        import extract_carry_forwards as _ecf
        _ecf.main(notes_file=notes_file)
    finally:
        sys.stderr = original_stderr

    warning_text = captured_stderr.getvalue().strip()
    if warning_text:
        # Re-emit each warning line as a Note: in stdout so the user sees it
        for line in warning_text.splitlines():
            if line.strip():
                print(f"Note: {line.strip()}")

    print("(run expand_carry_forward.py S<N>#<M> to see full description of any item above)")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument("--with-carry-forwards", action="store_true")
    _parser.add_argument("--opus", default=None, metavar="PATH")
    _args = _parser.parse_args()
    _opus_path = Path(_args.opus) if _args.opus else None
    main(_opus_path)
    if _args.with_carry_forwards:
        run_with_carry_forwards(notes_file=_opus_path)
