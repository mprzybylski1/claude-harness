#!/usr/bin/env python3
"""
Classify the current session as 'code' or 'docs'.

Compares all changed files (committed + uncommitted) since the last
session-close commit against the set of production code paths.

Prints 'code' if any changed file is under a production path.
Prints 'docs' if all changed files are docs/governance/tooling only.

Usage:
    python scripts/tools/classify_session.py   →  code
    python scripts/tools/classify_session.py   →  docs

Exit codes: 0 always (classification itself never fails).
If git is unavailable, prints 'code' conservatively.

Production paths (any match → 'code'):
    core/, data/, execution/, infra/, research/, strategies/,
    main.py, dashboard/, tests/, config.yaml, requirements.txt
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_config as _hc

_HARNESS = _hc.load()

# Any changed file whose path starts with one of these prefixes → code session
# Read from harness.yaml if present; fall back to trading-project defaults.
CODE_PREFIXES = _hc.code_paths(_HARNESS)

# Safety-adjacent governance files: trigger full Opus even in a docs session
SAFETY_ADJACENT = (
    "docs/architecture_invariants.md",
    "config.yaml",
    # compliance_engine.py is already caught by core/ prefix above
)


def _get_last_session_close_sha() -> str:
    """Return the SHA of the most recent session-close commit."""
    result = subprocess.run(
        ["git", "log", "--oneline", "--format=%H %s"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    prefix = re.escape(_hc.session_close_prefix(_HARNESS))
    pattern = re.compile(rf"^([0-9a-f]+) {prefix}\d+ session close")
    for line in result.stdout.splitlines():
        m = pattern.match(line.strip())
        if m:
            return m.group(1)
    return ""


def _changed_files(since_sha: str) -> list[str]:
    """Return all files changed since since_sha plus any uncommitted changes."""
    files: set[str] = set()

    if since_sha:
        r = subprocess.run(
            ["git", "diff", f"{since_sha}..HEAD", "--name-only"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            files.update(f.strip() for f in r.stdout.splitlines() if f.strip())

    # Uncommitted changes
    r = subprocess.run(
        ["git", "diff", "HEAD", "--name-only"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        files.update(f.strip() for f in r.stdout.splitlines() if f.strip())

    # Untracked files that were Written this session (new tickets etc.)
    r = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        files.update(f.strip() for f in r.stdout.splitlines() if f.strip())

    return sorted(files)


def classify(files: list[str]) -> str:
    for f in files:
        if any(f.startswith(p) for p in CODE_PREFIXES):
            return "code"
        if f in SAFETY_ADJACENT:
            return "code"  # safety-adjacent → full Opus
    return "docs"


def main() -> None:
    sha = _get_last_session_close_sha()
    if not sha:
        # Can't find anchor — be conservative
        print("code")
        return

    files = _changed_files(sha)
    print(classify(files))


if __name__ == "__main__":
    main()
