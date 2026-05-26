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


def _parse_fix_commit(tokens: list[str]) -> tuple[str, str | None] | None:
    """Return (ticket_id, git_cwd) if tokens are a fix(TXXX): git commit, else None.

    git_cwd is the path from `-C <path>` if present, else None (use hook's cwd).
    Handles: `git commit`, `git -C <path> commit`, `git --git-dir=... commit`.
    """
    try:
        git_idx = tokens.index("git")
    except ValueError:
        return None

    # Walk past git flags to find "commit"
    git_cwd: str | None = None
    i = git_idx + 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == "commit":
            break
        if tok in ("-C", "--work-tree", "--git-dir") and i + 1 < len(tokens):
            if tok == "-C":
                git_cwd = tokens[i + 1]
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        # Non-option, non-"commit" subcommand — not a commit call
        return None
    else:
        return None

    commit_idx = i  # index of "commit" token

    # --no-verify → bypass
    if "--no-verify" in tokens:
        return None

    # Find -m <message> — scan only tokens after "commit" to avoid matching
    # flags that appear before the subcommand in malformed invocations.
    for j, tok in enumerate(tokens[commit_idx + 1:], start=commit_idx + 1):
        if tok == "-m" and j + 1 < len(tokens):
            msg = tokens[j + 1]
            m = re.match(r"^fix\(T(\d+)\):", msg)
            if m:
                return f"T{m.group(1)}", git_cwd
        if tok.startswith("-m") and len(tok) > 2:
            msg = tok[2:].strip("\"'")
            m = re.match(r"^fix\(T(\d+)\):", msg)
            if m:
                return f"T{m.group(1)}", git_cwd

    return None


_TICKET_FILE_RE = re.compile(r"^T\d+-.+\.md$")


def _is_archive_path(path: str) -> bool:
    """Return True for ticket files (T###-*.md) — archive moves are not code.

    Uses the filename pattern rather than directory names so that legitimate
    code directories named 'archive' or 'tickets' are not misclassified.
    """
    return bool(_TICKET_FILE_RE.match(Path(path).name))


def _staged_code_files(code_prefixes: tuple[str, ...], git_cwd: str | None = None) -> list[str]:
    """Return staged file paths that match code_prefixes."""
    cmd = ["git"]
    if git_cwd:
        cmd += ["-C", git_cwd]
    cmd += ["diff", "--cached", "--name-only"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return []
        staged = result.stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return []

    code_files = []
    for path in staged:
        if _is_archive_path(path):
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

    parsed = _parse_fix_commit(tokens)
    if parsed is None:
        sys.exit(0)
    ticket_id, git_cwd = parsed

    code_prefixes = _code_paths()
    code_files = _staged_code_files(code_prefixes, git_cwd)

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
