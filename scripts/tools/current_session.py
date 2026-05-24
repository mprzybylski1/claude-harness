#!/usr/bin/env python3
"""
Print the current session ID to stdout.

Reads the Session Log in docs/sessions.md, finds the last closed session
entry (S<N> YYYY-MM-DD:), and prints S<N+1>.

This is more reliable than parsing git log because some sessions close
without a "docs: S[N] session close" commit (e.g. brief cycle-check or
pi-status sessions). sessions.md is updated every session close regardless.

Usage:
    python scripts/tools/current_session.py   →  S108

Exits 1 with an error message if no session entry is found.
"""
import re
import sys
from pathlib import Path


SESSIONS_MD = Path(__file__).resolve().parents[2] / "docs" / "sessions.md"


def get_current_session(sessions_path: Path = SESSIONS_MD) -> int:
    """Return the current (in-progress) session number."""
    if not sessions_path.exists():
        print(f"ERROR: {sessions_path} not found", file=sys.stderr)
        sys.exit(1)

    content = sessions_path.read_text()
    matches = re.findall(r"^S(\d+) \d{4}-\d{2}-\d{2}:", content, re.MULTILINE)
    if not matches:
        print("ERROR: no 'S<N> YYYY-MM-DD:' entries found in sessions.md", file=sys.stderr)
        sys.exit(1)

    return int(matches[-1]) + 1


_SESSION_ID_FILE = Path(__file__).resolve().parents[2] / ".git" / "CLAUDE_SESSION_ID"


def persist_session(n: int) -> None:
    """Write session number to .git/CLAUDE_SESSION_ID for session-close fallback."""
    try:
        _SESSION_ID_FILE.write_text(str(n))
    except OSError:
        pass  # non-fatal: .git may not be writable in edge cases


def main() -> None:
    n = get_current_session()
    persist_session(n)
    print(f"S{n}")


if __name__ == "__main__":
    main()
