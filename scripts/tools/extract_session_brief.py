#!/usr/bin/env python3
"""
Extract the session briefing sections from docs/sessions.md.

Prints:
  - The full ## Current Phase & Status section (gate criteria, what's done/remaining)
  - The full ## Active Work section (current session state)
  - The last 5 lines of the ## Session Log section

This gives session-start all the session state it needs (~500 tokens) without
loading the full sessions.md (~1500+ tokens as the log grows).

Usage (from project root):
    python scripts/tools/extract_session_brief.py

Output goes to stdout. Exits 1 if sessions.md is not found or cannot be parsed.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SESSIONS_FILE = ROOT / "docs" / "sessions.md"
ERRORS_FILE = ROOT / ".git" / "session_tool_log.errors"
SESSION_LOG_KEEP = 5
HOOK_ERRORS_KEEP = 5


def extract_section(content: str, heading: str) -> str | None:
    """Extract content between a ## heading and the next ## heading."""
    pattern = re.compile(
        r"^## " + re.escape(heading) + r"\s*\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(1).rstrip() if m else None


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--sessions", default=None, metavar="PATH")
    p.add_argument("--errors", default=None, metavar="PATH")
    args, _ = p.parse_known_args()
    sessions_file = Path(args.sessions) if args.sessions else SESSIONS_FILE
    errors_file = Path(args.errors) if args.errors else ERRORS_FILE

    if not sessions_file.exists():
        print(f"ERROR: {sessions_file} not found", file=sys.stderr)
        sys.exit(1)

    content = sessions_file.read_text()

    # Current Phase & Status section
    phase_status = extract_section(content, "Current Phase & Status")
    if phase_status is None:
        print("ERROR: could not find '## Current Phase & Status' section", file=sys.stderr)
        sys.exit(1)

    # Active Work section
    active_work = extract_section(content, "Active Work")
    if active_work is None:
        print("ERROR: could not find '## Active Work' section", file=sys.stderr)
        sys.exit(1)

    tickets_closed_count = active_work.count("Tickets closed:")
    if tickets_closed_count > 1:
        print(
            f"WARNING: Active Work contains 'Tickets closed:' {tickets_closed_count} times "
            "— section may not have been fully replaced (orphan content from prior session)",
            file=sys.stderr,
        )

    # Session Log — last N lines only
    session_log = extract_section(content, "Session Log")
    if session_log is None:
        print("ERROR: could not find '## Session Log' section", file=sys.stderr)
        sys.exit(1)

    log_lines = [ln for ln in session_log.splitlines() if re.match(r"^S\d+", ln.strip())]
    recent_lines = log_lines[-SESSION_LOG_KEEP:]

    # Hook errors — tail last N lines of .git/session_tool_log.errors
    from collections import deque
    hook_errors_tail: list[str] = []
    if errors_file.exists():
        with errors_file.open(encoding="utf-8", errors="replace") as _ef:
            hook_errors_tail = [
                ln for ln in deque(_ef, maxlen=HOOK_ERRORS_KEEP * 2)
                if ln.strip()
            ][-HOOK_ERRORS_KEEP:]

    # Output
    print("## Current Phase & Status")
    print()
    print(phase_status)
    print()
    print("## Active Work")
    print()
    print(active_work)
    print()
    print(f"## Session Log (last {SESSION_LOG_KEEP})")
    print()
    for line in recent_lines:
        print(line)
    print()
    print(f"## Hook errors (last {HOOK_ERRORS_KEEP})")
    print()
    if hook_errors_tail:
        for line in hook_errors_tail:
            print(line)
    else:
        print("none")


if __name__ == "__main__":
    main()
