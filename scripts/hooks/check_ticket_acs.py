#!/usr/bin/env python3
"""
PreToolUse hook: block writing a ticket to closed/ if unchecked ACs remain.

Fires on Edit, Write, and Bash before the tool executes.

Edit/Write: acts when the target file_path is inside docs/tickets/closed/.
Bash: acts when the command contains mv/cp/git-mv that would land a .md file
  inside docs/tickets/closed/ — reads the source file content pre-move.

Scans the resulting content for `- [ ]` items that lack a DEFERRED or N/A
annotation. Exits 2 (block) with a descriptive message if any are found.

Valid inline resolutions (case-insensitive, anywhere on the line):
  — DEFERRED to T[N]   marks item as deferred to a successor ticket
  — N/A                marks item as not applicable
  — NOT APPLICABLE     same as N/A
"""
import json
import re
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLOSED_DIR = REPO_ROOT / "docs" / "tickets" / "closed"

EXEMPT_PATTERNS = re.compile(r"\bDEFERRED\b|\bN/A\b|\bNOT APPLICABLE\b", re.IGNORECASE)


def _target_in_closed(file_path: str) -> bool:
    try:
        resolved = Path(file_path).resolve()
        return resolved == CLOSED_DIR or CLOSED_DIR in resolved.parents
    except Exception as e:
        print(f"AC pre-lint: path resolution failed for {file_path!r}: {e}", file=sys.stderr)
        return False


def _unchecked(content: str) -> list[str]:
    return [
        line.strip()
        for line in content.splitlines()
        if re.match(r"\s*-\s+\[ \]", line) and not EXEMPT_PATTERNS.search(line)
    ]


def _bash_ticket_sources(command: str) -> list[Path]:
    """
    Return source .md paths being moved/copied into closed/ by a Bash command.
    Handles: mv, cp, git mv (single or chained with && ; ||).
    """
    sources: list[Path] = []
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        # Skip shell operators
        if tok in ("&&", "||", ";", "|"):
            i += 1
            continue
        # mv <src> <dst>  or  cp <src> <dst>
        if tok in ("mv", "cp") and i + 2 < len(tokens):
            src, dst = tokens[i + 1], tokens[i + 2]
            if _target_in_closed(dst) and src.endswith(".md"):
                sources.append(Path(src))
            i += 3
            continue
        # git mv <src> <dst>
        if tok == "git" and i + 3 < len(tokens) and tokens[i + 1] == "mv":
            src, dst = tokens[i + 2], tokens[i + 3]
            if _target_in_closed(dst) and src.endswith(".md"):
                sources.append(Path(src))
            i += 4
            continue
        i += 1

    return sources


def _block(label: str, items: list[str]) -> None:
    print(
        f"AC pre-lint BLOCKED — {len(items)} unchecked item(s) in {label}:\n"
        + "\n".join(f"  {item}" for item in items)
        + "\nTick each item, add '— DEFERRED to T[N]', or add '— N/A: <reason>' "
        "before moving to closed/.",
        file=sys.stderr,
    )
    sys.exit(2)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    # ── Edit / Write ─────────────────────────────────────────────────────────
    if tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        if not _target_in_closed(file_path):
            sys.exit(0)

        if tool_name == "Write":
            content = tool_input.get("content", "")
        else:  # Edit — only the incoming new_string can introduce unchecked ACs
            content = tool_input.get("new_string", "")

        items = _unchecked(content)
        if items:
            _block(Path(file_path).name, items)

    # ── Bash (mv / cp / git mv into closed/) ─────────────────────────────────
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if "closed" not in command:
            sys.exit(0)

        for src in _bash_ticket_sources(command):
            try:
                # Resolve relative to REPO_ROOT if not absolute
                resolved = src if src.is_absolute() else REPO_ROOT / src
                content = resolved.read_text()
            except Exception:
                continue
            items = _unchecked(content)
            if items:
                _block(src.name, items)

    sys.exit(0)


if __name__ == "__main__":
    main()
