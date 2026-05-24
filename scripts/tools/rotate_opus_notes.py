"""
scripts/tools/rotate_opus_notes.py
Pre-rotate docs/opus_notes.md before the Opus post-session review.

Archives the oldest Opus Review section(s) to the appropriate decade-bucket
archive file in docs/archive/, leaving exactly 1 section in opus_notes.md.
When Opus appends its review, the file will then contain exactly 2 sections.

Called from session-close skill Step 3 (before generating the Opus review
context). Must be called before the Opus agent runs, not after.

Usage:
    python scripts/tools/rotate_opus_notes.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
NOTES = ROOT / "docs" / "opus_notes.md"
ARCHIVE_DIR = ROOT / "docs" / "archive"

# Matches the start of each review section at the beginning of a line.
# Group 1 captures the session number so we can route to the right archive bucket.
_SECTION_RE = re.compile(r"^# Opus Review — S(\d+)", re.MULTILINE)


def _archive_path(session_n: int) -> Path:
    decade_start = (session_n // 10) * 10
    decade_end = decade_start + 9
    return ARCHIVE_DIR / f"opus_notes_S{decade_start}-S{decade_end}.md"


def _archive_header(decade_start: int, decade_end: int) -> str:
    return (
        f"# Opus Review Notes — Archive S{decade_start}–S{decade_end}\n\n"
        "Archived from `docs/opus_notes.md`. All findings are either fixed or "
        "tracked in `docs/tickets/`.\n"
        "Use `grep` to search. Do not load into session context.\n\n"
        "---\n"
    )


def rotate() -> None:
    """Archive oldest section(s) until opus_notes.md has exactly 1 review."""
    content = NOTES.read_text()
    initial_count = len(_SECTION_RE.findall(content))

    if initial_count <= 1:
        print(f"opus_notes.md has {initial_count} section(s) — no rotation needed.")
        return

    rotated = 0
    while True:
        content = NOTES.read_text()
        matches = list(_SECTION_RE.finditer(content))
        if len(matches) <= 1:
            break

        # The file header is everything before the first review section.
        first = matches[0]
        header_block = content[: first.start()]

        # The oldest section runs from the first match to the start of the second.
        second_start = matches[1].start()
        oldest_section = content[first.start() : second_start].rstrip()
        remainder = content[second_start:]

        session_n = int(first.group(1))
        archive_path = _archive_path(session_n)

        if not archive_path.exists():
            decade_start = (session_n // 10) * 10
            decade_end = decade_start + 9
            archive_path.write_text(_archive_header(decade_start, decade_end))
            print(f"Created archive {archive_path.relative_to(ROOT)}")

        # Append to archive, then rewrite opus_notes.md.
        archive_text = archive_path.read_text().rstrip()
        archive_path.write_text(archive_text + "\n\n" + oldest_section + "\n\n\n")
        NOTES.write_text(header_block + remainder)

        print(f"Archived S{session_n} review → {archive_path.relative_to(ROOT)}")
        rotated += 1

    final_count = len(_SECTION_RE.findall(NOTES.read_text()))
    print(
        f"Rotation complete: {rotated} section(s) archived. "
        f"opus_notes.md now has {final_count} section(s)."
    )
    if final_count != 1:
        import sys
        sys.exit(
            f"ERROR: expected 1 section after rotation, got {final_count}. "
            "Inspect docs/opus_notes.md before proceeding."
        )


if __name__ == "__main__":
    rotate()
