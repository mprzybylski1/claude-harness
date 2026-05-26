#!/usr/bin/env python3
"""
Surface full Opus finding context by ID.

Searches docs/opus_notes.md and docs/archive/opus_notes*.md for the numbered
finding and prints its full text with a source header.

Usage:
    python scripts/tools/expand_carry_forward.py S1#3
    python scripts/tools/expand_carry_forward.py "S1 #3"
    python scripts/tools/expand_carry_forward.py S1#3 --latest
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_default_root = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("HARNESS_ROOT", str(_default_root)))

# "S1#3", "s1 #3", "S3 #12" etc.
_ID_RE = re.compile(r'^[sS](\d+)\s*#\s*(\d+)$')

# Session block headers: "# Opus Review — S9 2026-05-26"
# Deliberately narrow to avoid matching "# Opus Review Notes — Archive S0–S9"
_SESSION_HEAD = re.compile(r'^#\s+Opus Review\s*—\s*S(\d+)', re.MULTILINE)

# Any numbered finding heading: "3. **S1 #3 — ..."
_ANY_FINDING_HEAD = re.compile(r'^\d+\.\s+\*\*[sS]\d+\s*#\s*\d+', re.MULTILINE)


def _parse_id(raw: str) -> tuple[int, int]:
    m = _ID_RE.match(raw.strip())
    if not m:
        print(f"ERROR: invalid finding ID '{raw}' — expected S<N>#<M> e.g. S1#3", file=sys.stderr)
        sys.exit(1)
    return int(m.group(1)), int(m.group(2))


def _opus_files() -> list[Path]:
    files: list[Path] = []
    current = ROOT / "docs" / "opus_notes.md"
    if current.exists():
        files.append(current)
    archive_dir = ROOT / "docs" / "archive"
    if archive_dir.is_dir():
        files.extend(sorted(archive_dir.glob("opus_notes*.md")))
    return files


def _session_at(pos: int, session_positions: list[tuple[int, int]]) -> int:
    """Return the session number of the block that contains pos."""
    sn = 0
    for sp, sn_val in session_positions:
        if sp <= pos:
            sn = sn_val
        else:
            break
    return sn


def _extract_findings(content: str, session_n: int, finding_n: int) -> list[tuple[int, str]]:
    """Return [(session_number, text)] for all occurrences in this content."""
    session_positions = [(m.start(), int(m.group(1))) for m in _SESSION_HEAD.finditer(content)]
    head_positions = [m.start() for m in _ANY_FINDING_HEAD.finditer(content)]

    id_pat = re.compile(
        r'^\d+\.\s+\*\*[sS]' + str(session_n) + r'\s*#\s*' + str(finding_n) + r'[^*\n]*\*\*',
        re.MULTILINE,
    )

    results = []
    for m in id_pat.finditer(content):
        start = m.start()
        end = next((hp for hp in head_positions if hp > start), len(content))
        text = content[start:end].rstrip()
        sn = _session_at(start, session_positions)
        results.append((sn, text))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Surface full Opus finding context by ID.")
    parser.add_argument("finding_id", metavar="S<N>#<M>", help="e.g. S1#3 or 'S1 #3'")
    parser.add_argument("--latest", action="store_true",
                        help="Print only the most recent occurrence")
    args = parser.parse_args()

    session_n, finding_n = _parse_id(args.finding_id)
    canonical = f"S{session_n} #{finding_n}"

    files = _opus_files()
    if not files:
        print("ERROR: no opus_notes.md files found", file=sys.stderr)
        sys.exit(1)

    all_matches: list[tuple[int, str, str]] = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        for sn, text in _extract_findings(content, session_n, finding_n):
            all_matches.append((sn, f.name, text))

    if not all_matches:
        print(f"{canonical} not found in any opus_notes file.", file=sys.stderr)
        sys.exit(1)

    all_matches.sort(key=lambda x: x[0], reverse=True)
    if args.latest:
        all_matches = all_matches[:1]

    for sn, fname, text in all_matches:
        session_label = f"S{sn}" if sn else "unknown session"
        print(f"[From: {fname} — {session_label}]")
        print(text)
        print()


if __name__ == "__main__":
    main()
