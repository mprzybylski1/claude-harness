#!/usr/bin/env python3
"""
Print aged Opus carry-forward items from docs/opus_notes.md.

Matches two patterns Opus actually uses:
  1. "carry-forward N sessions"       — explicit count
  2. "carry-forward from S<N>"        — age = current_session - N

Deduplicates by description and prints items at or above the threshold,
sorted by age descending.

Usage:
    python scripts/tools/extract_carry_forwards.py [--threshold N]

Default threshold: 2 sessions. Output is empty if none qualify.
Called by session-start (Step 1.6) to surface stale issues proactively.
"""
import re
import sys
from pathlib import Path

NOTES_FILE = Path(__file__).resolve().parents[2] / "docs" / "opus_notes.md"
DEFAULT_THRESHOLD = 2

# Pattern 1: explicit count — "carry-forward 3 sessions"
_PAT_COUNT = re.compile(r'carry.forward\s+(\d+)\s+sessions', re.IGNORECASE)
# Pattern 2: session reference — "carry-forward from S7"
_PAT_SESSION = re.compile(r'carry.forward\s+from\s+S(\d+)', re.IGNORECASE)


def _current_session_number(notes_file: Path) -> int | None:
    """Derive the session number from the most recent '# Opus Review — SN' header."""
    text = notes_file.read_text(encoding="utf-8")
    headers = re.findall(r'^#{1,2} Opus Review.*?S(\d+)', text, re.MULTILINE)
    if headers:
        return int(headers[-1])
    return None


def _extract_description(line: str) -> str:
    """Best-effort description from a carry-forward line."""
    desc_m = re.search(r'\*\*(.+?)\*\*', line)
    if desc_m and not re.search(r'carry.forward', desc_m.group(1), re.IGNORECASE):
        return desc_m.group(1)
    return re.split(r'\s+—\s+|\s+--\s+', line)[0].strip().lstrip('- ').strip('*')


def extract(threshold: int = DEFAULT_THRESHOLD, notes_file: Path | None = None) -> list[tuple[int, str]]:
    path = notes_file if notes_file is not None else NOTES_FILE
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    current_sn = _current_session_number(path)

    found: dict[str, int] = {}     # norm_key -> max age
    original: dict[str, str] = {}  # norm_key -> display description

    session_ref_lines = [ln for ln in text.splitlines() if _PAT_SESSION.search(ln)]
    if session_ref_lines and current_sn is None:
        import sys as _sys
        print(
            "WARNING: extract_carry_forwards.py found 'carry-forward from S<N>' lines but "
            "no 'Opus Review — SN' header in notes file — session-reference pattern disabled",
            file=_sys.stderr,
        )

    for line in text.splitlines():
        count: int | None = None

        m1 = _PAT_COUNT.search(line)
        if m1:
            count = int(m1.group(1))

        m2 = _PAT_SESSION.search(line)
        if m2 and current_sn is not None:
            age = current_sn - int(m2.group(1))
            if age > 0:
                count = max(count, age) if count is not None else age

        if count is None or count < threshold:
            continue

        desc = _extract_description(line)
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
