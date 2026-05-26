#!/usr/bin/env python3
"""
PreToolUse hook: block `git commit -m "fix(TXXX): ..."` when no code is staged.

Fires on Bash tool calls only. Non-Bash tools and non-commit commands exit 0
immediately.

Rules:
  - Only acts when the commit message prefix is `fix(T<digits>):` (lowercase, exact).
  - Allows `--no-verify` to bypass, consistent with git hook conventions.
  - Scans `git diff --cached --name-only` for files matching harness code_paths.
  - Blocks (exit 2) if no code files are staged, printing the ticket ID and a
    suggestion to use `close_ticket.py --files`.
  - docs/archive/ files are explicitly excluded from the "code" count.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

_DEFAULT_CODE_PATHS = ("scripts/", "src/", "lib/", "tests/")


def _code_paths() -> tuple[str, ...]:
    try:
        import harness_config as _hc
        return _hc.code_paths(_hc.load())
    except Exception:
        return _DEFAULT_CODE_PATHS


def _parse_fix_commit(tokens: list[str]) -> str | None:
    """Return ticket ID if tokens are a fix(TXXX): git commit, else None."""
    # Must be a git commit command
    try:
        git_idx = tokens.index("git")
    except ValueError:
        return None
    if git_idx + 1 >= len(tokens) or tokens[git_idx + 1] != "commit":
        return None

    # --no-verify → bypass
    if "--no-verify" in tokens:
        return None

    # Find -m <message>
    for i, tok in enumerate(tokens):
        if tok == "-m" and i + 1 < len(tokens):
            msg = tokens[i + 1]
            m = re.match(r"^fix\(T(\d+)\):", msg)
            if m:
                return f"T{m.group(1)}"
        # Also handle -m"message" (no space) — shlex handles this, but guard anyway
        if tok.startswith("-m") and len(tok) > 2:
            msg = tok[2:].strip("\"'")
            m = re.match(r"^fix\(T(\d+)\):", msg)
            if m:
                return f"T{m.group(1)}"

    return None


def _staged_code_files(code_prefixes: tuple[str, ...]) -> list[str]:
    """Return staged file paths that match code_prefixes."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return []
        staged = result.stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return []

    code_files = []
    for path in staged:
        # Exclude docs/archive/ explicitly — archive moves are not code
        if path.startswith("docs/archive/") or path.startswith("docs/tickets/"):
            continue
        if any(path.startswith(prefix) for prefix in code_prefixes):
            code_files.append(path)
    return code_files


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    ticket_id = _parse_fix_commit(tokens)
    if ticket_id is None:
        sys.exit(0)

    code_prefixes = _code_paths()
    code_files = _staged_code_files(code_prefixes)

    if not code_files:
        print(
            f"BLOCKED: fix({ticket_id}) commit has no code files staged.\n"
            f"  Stage code/test files first, or use close_ticket.py --files to stage them.\n"
            f"  To bypass: add --no-verify to the git commit command.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
