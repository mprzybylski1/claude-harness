#!/usr/bin/env python3
"""
Print the canonical session-close commit message prefix to stdout.

Usage:
    python scripts/tools/session_close_commit_msg.py [--session N]

If --session N is given, use that number directly (avoids reading sessions.md,
which is required when called after Step 1 has already written the session log entry).
Without --session, derives N from sessions.md — only correct if called before Step 1.

Output example (with default harness.yaml session_close_prefix "docs: S"):
    docs: S159 session close —

Append your one-line summary after the dash, e.g.:
    docs: S159 session close — workflow hooks implemented
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from current_session import get_current_session
import harness_config as _hc

_PREFIX = _hc.session_close_prefix()

SESSIONS_MD = Path(__file__).resolve().parents[2] / "docs" / "sessions.md"
_SESSION_ID_FILE = Path(__file__).resolve().parents[2] / ".git" / "CLAUDE_SESSION_ID"


def main() -> None:
    if "--session" in sys.argv:
        idx = sys.argv.index("--session")
        try:
            n = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("ERROR: --session requires an integer argument", file=sys.stderr)
            sys.exit(1)
    elif _SESSION_ID_FILE.exists():
        # Fallback: read session ID persisted by current_session.py during Step 0.
        # By Step 6, sessions.md has the current entry so get_current_session() would
        # return N+1 — the persisted file has the correct N.
        try:
            n = int(_SESSION_ID_FILE.read_text().strip())
            print(f"(using persisted session ID S{n} from {_SESSION_ID_FILE.name})",
                  file=sys.stderr)
        except (OSError, ValueError):
            print(
                "ERROR: .git/CLAUDE_SESSION_ID exists but could not be read. "
                "Pass --session N explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(
            "ERROR: --session N is required.\n"
            "  By Step 6, sessions.md already has the current session entry,\n"
            "  so the no-arg form returns S[N+1] — wrong commit message prefix.\n"
            "  Run 'python scripts/tools/current_session.py' first (writes\n"
            "  .git/CLAUDE_SESSION_ID), then call without --session.\n"
            "  Or pass explicitly: python scripts/tools/session_close_commit_msg.py --session N",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"{_PREFIX}{n} session close — ", end="")


if __name__ == "__main__":
    main()
