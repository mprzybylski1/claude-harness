#!/usr/bin/env python3
"""
Print aged Opus carry-forward items from docs/opus_notes.md.

Finds all "carry-forward N sessions" patterns, deduplicates by description,
and prints those at or above the threshold sorted by age descending.

Usage:
    python scripts/tools/extract_carry_forwards.py [--threshold N]

Default threshold: 5 sessions. Output is empty if none qualify.
Called by session-start (Step 1.6) to surface stale issues proactively.
"""
import re
import sys
from pathlib import Path

NOTES_FILE = Path(__file__).resolve().parents[2] / "docs" / "opus_notes.md"
DEFAULT_THRESHOLD = 5


def extract(threshold: int = DEFAULT_THRESHOLD, notes_file: Path | None = None) -> list[tuple[int, str]]:
    path = notes_file if notes_file is not None else NOTES_FILE
    if not path.exists():
        return []

    text = path.read_text()
    found: dict[str, int] = {}     # norm_key -> max count
    original: dict[str, str] = {}  # norm_key -> display description

    for line in text.splitlines():
        m = re.search(r'carry.forward\s+(\d+)\s+sessions', line, re.IGNORECASE)
        if not m:
            continue
        count = int(m.group(1))
        if count < threshold:
            continue

        # First **...** block = description; skip if it IS the carry-forward phrase
        desc_m = re.search(r'\*\*(.+?)\*\*', line)
        if desc_m and not re.search(r'carry.forward', desc_m.group(1), re.IGNORECASE):
            desc = desc_m.group(1)
        else:
            # Fall back: text before the first em-dash or end of line, stripped
            desc = re.split(r'\s+—\s+|\s+--\s+', line)[0].strip().lstrip('- ').strip('*')

        key = re.sub(r'\s+', ' ', desc).lower()[:60]
        if key not in found or found[key] < count:
            found[key] = count
            original[key] = desc

    return sorted(
        [(found[k], original[k]) for k in found],
        key=lambda x: -x[0],
    )


def main(notes_file: Path | None = None) -> None:
    threshold = DEFAULT_THRESHOLD
    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        try:
            threshold = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("ERROR: --threshold requires an integer argument", file=sys.stderr)
            sys.exit(1)

    items = extract(threshold, notes_file=notes_file)
    if not items:
        print(f"(no Opus carry-forwards >= {threshold} sessions)")
        return

    print(f"Opus carry-forwards (>= {threshold} sessions):")
    for count, desc in items:
        print(f"  {count:>2}s: {desc}")


if __name__ == "__main__":
    main()
