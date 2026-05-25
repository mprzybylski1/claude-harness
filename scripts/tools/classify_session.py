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
    scripts/, src/, lib/, tests/ (harness defaults from harness.yaml)
    Override per-repo by placing a harness.yaml in the repo root.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_config as _hc

# Safety-adjacent governance files: trigger full Opus even in a docs session
SAFETY_ADJACENT = (
    "docs/architecture_invariants.md",
    "config.yaml",
)


def _get_last_session_close_sha(close_prefix: str, cwd: Path | None = None) -> str:
    """Return the SHA of the most recent session-close commit."""
    result = subprocess.run(
        ["git", "log", "--oneline", "--format=%H %s"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return ""
    prefix = re.escape(close_prefix)
    pattern = re.compile(rf"^([0-9a-f]+) {prefix}\d+ session close")
    for line in result.stdout.splitlines():
        m = pattern.match(line.strip())
        if m:
            return m.group(1)
    return ""


def _changed_files(since_sha: str, cwd: Path | None = None) -> list[str]:
    """Return all files changed since since_sha plus any uncommitted changes."""
    files: set[str] = set()

    if since_sha:
        r = subprocess.run(
            ["git", "diff", f"{since_sha}..HEAD", "--name-only"],
            capture_output=True, text=True, cwd=cwd,
        )
        if r.returncode == 0:
            files.update(f.strip() for f in r.stdout.splitlines() if f.strip())

    # Uncommitted changes
    r = subprocess.run(
        ["git", "diff", "HEAD", "--name-only"],
        capture_output=True, text=True, cwd=cwd,
    )
    if r.returncode == 0:
        files.update(f.strip() for f in r.stdout.splitlines() if f.strip())

    # Untracked files that were Written this session (new tickets etc.)
    r = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, cwd=cwd,
    )
    if r.returncode == 0:
        files.update(f.strip() for f in r.stdout.splitlines() if f.strip())

    return sorted(files)


def classify(files: list[str], code_prefixes: tuple[str, ...]) -> str:
    for f in files:
        if any(f.startswith(p) for p in code_prefixes):
            return "code"
        if f in SAFETY_ADJACENT:
            return "code"  # safety-adjacent → full Opus
    return "docs"


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=None, metavar="PATH",
                   help="Primary repo path for git operations (default: CWD)")
    args = p.parse_args()
    cwd = Path(args.repo).resolve() if args.repo else None

    harness = _hc.load_for_repo(cwd) if cwd else _hc.load()
    code_prefixes = _hc.code_paths(harness)
    close_prefix = _hc.session_close_prefix(harness)

    sha = _get_last_session_close_sha(close_prefix, cwd=cwd)
    if not sha:
        repo_label = str(cwd) if cwd else "CWD"
        print(
            f"WARNING: no session-close anchor found in {repo_label}; defaulting to 'code'. "
            f"Check session_close_prefix in harness.yaml or ensure a session-close commit exists.",
            file=sys.stderr,
        )
        print("code")
        return

    files = _changed_files(sha, cwd=cwd)
    print(classify(files, code_prefixes))


if __name__ == "__main__":
    main()
