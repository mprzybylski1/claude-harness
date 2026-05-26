"""
scripts/tools/prepare_opus_context.py
Pre-builds docs/opus_review_context.md before the Opus post-session review.

Consolidates into one file:
  - Session diff (committed changes since last session-close + any uncommitted changes)
  - Trimmed docs/sessions.md (phase/gate status + active work + last 10 session log entries)
  - docs/architecture_invariants.md
  - Static analysis results (pre-run checks so Opus never reads source files to verify)
  - Ticket TEMPLATE.md (so Opus never reads it separately when creating tickets)

Reduces Opus tool calls by:
  - Eliminating repeated file reads and git subprocess calls inside the agent
  - Providing pre-computed answers to invariant check questions
  - Embedding the ticket template inline

IMPORTANT: The static analysis section is load-bearing for Opus invariant checks.
The Opus review prompt instructs Opus to trust these results without re-reading source files.
Do not modify the static-analysis check functions without updating tests/test_prepare_opus_context.py.

Called from session-close skill Step 4.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs" / "opus_review_context.md"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_config as _hc
_HARNESS = _hc.load()
_SESSION_CLOSE_PREFIX = _hc.session_close_prefix(_HARNESS)

MAX_DIFF_LINES = 600    # truncate very large diffs — stat shown first
SESSION_LOG_KEEP = 10   # number of recent session log entries to include

# Diff-cap filtering: these path prefixes are excluded from line counting so that
# batch ticket/archive additions don't trigger truncation of code changes.
_DIFF_CAP_EXCLUDE = ("docs/tickets/", "docs/archive/")

# Governance files: always shown in full even when the cap triggers.
_DIFF_ALWAYS_INCLUDE = ("scripts/tools/prepare_opus_context.py",
                        ".claude/skills/session-close/SKILL.md")

# Priority tiers for diff-cap truncation. Tier 0 fills first; tier 2 trimmed first.
# Files not matching any tier get tier 1 (default).
_TIER_CORE = ("scripts/tools/", "scripts/hooks/")  # tier 0 — harness core logic
_TIER_TESTS = ("tests/",)                          # tier 2


def _priority_tier(path: str) -> int:
    if any(path.startswith(p) for p in _TIER_CORE):
        return 0
    if any(path.startswith(p) for p in _TIER_TESTS):
        return 2
    return 1


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path = ROOT, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def _split_diff_files(diff: str) -> list[tuple[str, str]]:
    """Split a unified diff into (file_path, block_text) pairs.

    file_path is the b/ path from the diff --git header, e.g. 'core/schemas.py'.
    Returns an empty list if diff is empty.
    """
    blocks: list[tuple[str, str]] = []
    current_path = ""
    current_lines: list[str] = []
    for ln in diff.splitlines(keepends=True):
        if ln.startswith("diff --git "):
            if current_lines:
                blocks.append((current_path, "".join(current_lines)))
            parts = ln.split(" b/", 1)
            current_path = parts[1].strip() if len(parts) > 1 else ln
            current_lines = [ln]
        else:
            current_lines.append(ln)
    if current_lines:
        blocks.append((current_path, "".join(current_lines)))
    return blocks


def _apply_diff_cap(diff: str, cap: int) -> tuple[str, bool, list[str]]:
    """Apply line cap to a diff, excluding noise paths and preserving governance files.

    Returns (display_diff, was_truncated, truncated_paths).
    - docs/tickets/ and docs/archive/ blocks are excluded from line counting.
    - Governance files (_DIFF_ALWAYS_INCLUDE) are appended in full even when cap hits.
    - Signal blocks are filled in priority order: scripts/tools/ and scripts/hooks/ first,
      then other, then tests/ — so harness core logic is never truncated at the expense
      of test files.
    - truncated_paths lists file paths that were cut; empty when nothing was truncated.
    """
    if not diff.strip():
        return diff, False, []

    blocks = _split_diff_files(diff)
    noise = {p for p, _ in blocks if any(p.startswith(x) for x in _DIFF_CAP_EXCLUDE)}
    governance = {p for p, _ in blocks if any(x in p for x in _DIFF_ALWAYS_INCLUDE)}
    signal = [(p, d) for p, d in blocks if p not in noise and p not in governance]
    governance_blocks = [(p, d) for p, d in blocks if p in governance]

    signal_line_count = sum(len(d.splitlines()) for p, d in signal)
    if signal_line_count <= cap:
        return diff, False, []

    # Over cap: fill by priority tier (0 = core first, 3 = research last)
    sorted_signal = sorted(signal, key=lambda x: _priority_tier(x[0]))
    kept: list[str] = []
    truncated_paths: list[str] = []
    used = 0
    first_overflow = True
    for path, d in sorted_signal:
        lines = d.splitlines(keepends=True)
        if used + len(lines) <= cap:
            kept.append(d)
            used += len(lines)
        elif first_overflow and cap - used > 0:
            # Partial-slice the first block that overflows — T114. Subsequent blocks are
            # dropped entirely. Ensures a single large core/ file always has content for Opus.
            remaining = cap - used
            kept.append("".join(lines[:remaining]))
            used = cap
            first_overflow = False
        else:
            truncated_paths.append(path)

    truncated_diff = "".join(kept)
    if governance_blocks:
        truncated_diff += "\n\n# (governance files — always shown in full)\n"
        truncated_diff += "".join(d for _, d in governance_blocks)
    return truncated_diff, True, truncated_paths


def _section(title: str, body: str, fence: str = "") -> str:
    if fence:
        return f"## {title}\n\n```{fence}\n{body.strip()}\n```\n"
    return f"## {title}\n\n{body.strip()}\n"


# ── sessions.md trimming ──────────────────────────────────────────────────────

def _trim_sessions_md(content: str) -> str:
    """
    Return a trimmed view of sessions.md:
      - Current Phase & Status section (gate criteria)
      - Active Work section (this session's changes)
      - Last SESSION_LOG_KEEP entries from the Session Log
    Drops the preamble and the full historical log to save tokens.
    """
    lines = content.splitlines()

    def _section_start(heading: str) -> int | None:
        for i, ln in enumerate(lines):
            if ln.strip() == heading:
                return i
        return None

    phase_idx = _section_start("## Current Phase & Status")
    active_idx = _section_start("## Active Work")
    log_idx = _section_start("## Session Log")

    if any(x is None for x in (phase_idx, active_idx, log_idx)):
        return content  # fallback: full file

    phase_block = "\n".join(lines[phase_idx:active_idx]).rstrip()
    active_block = "\n".join(lines[active_idx:log_idx]).rstrip()

    log_entries = [
        ln for ln in lines[log_idx:]
        if re.match(r"^S\d+ \d{4}-\d{2}-\d{2}:", ln)
    ]
    kept = log_entries[-SESSION_LOG_KEEP:]
    omitted = len(log_entries) - len(kept)
    log_block = (
        "## Session Log\n\n"
        f"*(Showing last {len(kept)} of {len(log_entries)} entries"
        + (f"; {omitted} older entries omitted" if omitted else "")
        + ")*\n\n"
        + "\n".join(kept)
    )

    return f"{phase_block}\n\n---\n\n{active_block}\n\n---\n\n{log_block}"


# ── Static analysis ───────────────────────────────────────────────────────────

# ── Individual static-analysis checks ────────────────────────────────────────
# Each function takes a repo root Path, returns one PASS / WARN / FAIL / SKIP line.
# Tests in tests/test_prepare_opus_context.py call these directly without running
# the full context-builder.

def check_test_syntax(root: Path) -> str:
    """1. Compile every test_*.py — catches SyntaxErrors before Opus review."""
    tests_dir = root / "tests"
    if not tests_dir.exists():
        return "SKIP  no tests/ directory found"
    test_files = sorted(tests_dir.glob("test_*.py"))
    if not test_files:
        return "SKIP  no test_*.py files found"
    errors = []
    for f in test_files:
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", str(f)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            errors.append(f"  {f.name}: {r.stderr.strip()}")
    if errors:
        return "FAIL  test syntax errors:\n" + "\n".join(errors)
    return f"PASS  {len(test_files)} test files compile cleanly (no SyntaxError)"


def check_utcnow(root: Path) -> str:
    """2. Grep for deprecated datetime.utcnow() in scripts/ and tests/."""
    prod_dirs = ["scripts", "tests"]
    existing = [str(root / d) for d in prod_dirs if (root / d).exists()]
    if not existing:
        return "SKIP  no production directories found (scripts/ and tests/ absent)"
    r = subprocess.run(
        ["grep", "-rn", "--include=*.py",
         "--exclude=prepare_opus_context.py",   # avoid self-match on grep pattern string
         "--exclude=run_static_analysis.py",    # imports check_utcnow — not a usage site
         "--exclude=harness_config.py",         # docstring lists 'utcnow' as example name
         "utcnow"] + existing,
        capture_output=True, text=True,
    )
    hits = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if hits:
        return ("WARN  deprecated datetime.utcnow() usage:\n"
                + "\n".join(f"  {h}" for h in hits))
    return "PASS  no datetime.utcnow() in production code"


def check_bash_blocks(root: Path) -> str:
    """3. Run check_skill_bash_blocks.py to validate bash fenced blocks in SKILL.md."""
    check_script = root / "scripts" / "tools" / "check_skill_bash_blocks.py"
    if not check_script.exists():
        return "SKIP  check_skill_bash_blocks.py not found"
    r = subprocess.run(
        [sys.executable, str(check_script)],
        capture_output=True, text=True, cwd=root,
    )
    if r.returncode != 0:
        return f"FAIL  bash blocks in SKILL.md:\n  {r.stdout.strip() or r.stderr.strip()}"
    return f"PASS  {r.stdout.strip()}"


def _is_python_project(root: Path) -> bool:
    return any((root / f).exists() for f in (
        "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    )) or bool(list(root.glob("*.py")))


def _static_analysis(root: Path = ROOT) -> str:
    """
    Run pre-flight invariant checks. Returns a human-readable summary.
    Opus reads this section instead of reading source files to verify findings.
    Each check returns PASS / WARN / FAIL / SKIP with details on failure.
    """
    if root != ROOT and not _is_python_project(root):
        return "SKIP  static analysis N/A for this repo type (no Python project structure detected)"
    checks = [
        check_test_syntax,
        check_utcnow,
        check_bash_blocks,
    ]
    return "\n".join(fn(root) for fn in checks)


# ── Main ─────────────────────────────────────────────────────────────────────

def _parse_args() -> "argparse.Namespace":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=None, metavar="PATH",
                   help="Primary repo path for git diff (default: harness root)")
    p.add_argument("--sessions", default=None, metavar="PATH",
                   help="Path to sessions.md (default: docs/sessions.md in harness root)")
    p.add_argument("--opus", default=None, metavar="PATH",
                   help="Path to opus_notes.md to include in context (default: omitted)")
    p.add_argument("--output", default=None, metavar="PATH",
                   help="Output path (default: docs/opus_review_context.md in harness root)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    repo_root = Path(args.repo).resolve() if args.repo else ROOT
    sessions_path = Path(args.sessions) if args.sessions else ROOT / "docs" / "sessions.md"
    opus_path = Path(args.opus) if args.opus else None
    out_path = Path(args.output) if args.output else OUT

    def run(cmd: list[str]) -> subprocess.CompletedProcess:
        return _run(cmd, cwd=repo_root)

    parts: list[str] = []

    parts.append(
        "# Opus Review Context\n\n"
        "Auto-generated by `scripts/tools/prepare_opus_context.py`. Do not edit manually.\n\n"
        "**Read this file first.** It contains the session diff, trimmed sessions.md, "
        "architecture invariants, static analysis results, and the ticket template.\n"
        "**Do NOT read any other file unless you are actively writing to it.**\n"
        "The static analysis section answers invariant check questions — no source file reads needed."
    )

    # ── Git log since last session close ─────────────────────────────────────
    base_sha: str | None = None
    log_out = run(["git", "log", "--oneline", f"--grep={_SESSION_CLOSE_PREFIX}", "-20"]).stdout
    log_lines = [ln.strip() for ln in log_out.splitlines() if ln.strip()]
    if log_lines:
        base_sha = log_lines[0].split()[0]

    if base_sha:
        log = run(["git", "log", f"{base_sha}..HEAD", "--oneline"]).stdout
        parts.append(_section(
            f"Commits since last session-close ({base_sha[:12]})",
            log.strip() or "(none — all changes are uncommitted)",
        ))
    else:
        parts.append("## Warning\n\nNo prior 'session close' commit found.\n")

    # ── Session diff ──────────────────────────────────────────────────────────
    if base_sha:
        diff = run(["git", "diff", f"{base_sha}..HEAD"]).stdout
        diff_stat = run(["git", "diff", f"{base_sha}..HEAD", "--stat"]).stdout
    else:
        r_diff = run(["git", "diff", "main...HEAD"])
        diff = r_diff.stdout
        diff_stat = run(["git", "diff", "main...HEAD", "--stat"]).stdout
        if r_diff.returncode != 0 or not diff.strip():
            print(
                "WARNING: no session-close anchor found and 'git diff main...HEAD' returned "
                "no output — diff may be empty because the default branch is not 'main'. "
                "Pass --repo or ensure a session-close commit exists.",
                file=sys.stderr,
            )

    capped_diff, was_truncated, truncated_paths = _apply_diff_cap(diff.strip(), MAX_DIFF_LINES)
    if was_truncated:
        parts.append(_section("Session diff — stat (full diff truncated)", diff_stat))
        parts.append(_section(
            f"Session diff — priority-ordered, cap {MAX_DIFF_LINES} signal lines "
            f"(scripts/tools/ and scripts/hooks/ first; docs/tickets/ and docs/archive/ excluded; governance appended in full)",
            capped_diff + "\n\n...(truncated — read individual files only if actively writing to them)",
            fence="diff",
        ))
        parts.append(_section(
            "Files truncated (not shown in diff above — Opus: note confidence qualifiers apply)",
            "\n".join(f"- {p}" for p in truncated_paths) or "(none)",
        ))
    else:
        parts.append(_section(
            "Session diff (committed)",
            diff.strip() or "(no committed changes this session)",
            fence="diff",
        ))

    # ── Uncommitted / staged changes ──────────────────────────────────────────
    unstaged = run(["git", "diff", "HEAD"]).stdout
    staged = run(["git", "diff", "--cached"]).stdout
    extra = (staged + unstaged).strip()
    if extra:
        extra_capped, extra_truncated, extra_cut = _apply_diff_cap(extra, 400)
        if extra_truncated:
            extra_capped += "\n\n...(truncated)"
        parts.append(_section("Uncommitted / staged changes", extra_capped, fence="diff"))
        if extra_cut:
            parts.append(_section(
                "Uncommitted files truncated",
                "\n".join(f"- {p}" for p in extra_cut),
            ))

    # ── Static analysis ───────────────────────────────────────────────────────
    parts.append(_section("Static analysis (pre-run — do not re-check by reading source files)",
                           _static_analysis(repo_root)))

    # ── Trimmed docs/sessions.md ──────────────────────────────────────────────
    if sessions_path.exists():
        trimmed = _trim_sessions_md(sessions_path.read_text())
        parts.append(_section("docs/sessions.md (trimmed)", trimmed))

    # ── docs/opus_notes.md (when provided via --opus) ─────────────────────────
    if opus_path:
        if opus_path.exists():
            parts.append(_section("docs/opus_notes.md (last review)", opus_path.read_text()))
        else:
            print(f"WARNING: --opus {opus_path} not found, skipping", file=sys.stderr)

    # ── docs/architecture_invariants.md ──────────────────────────────────────
    # When --repo is given, prefer the repo's own invariants file.
    # When --repo is absent, repo_root == ROOT, so the file is harness root (S9 #10).
    inv_path = repo_root / "docs" / "architecture_invariants.md"
    if args.repo and inv_path.exists():
        inv_source = "repo-local"
    elif args.repo:
        inv_path = ROOT / "docs" / "architecture_invariants.md"
        inv_source = "harness fallback"
    else:
        inv_source = "harness root"
    if inv_path.exists():
        parts.append(_section(
            f"docs/architecture_invariants.md  [Source: {inv_source} — {inv_path}]",
            inv_path.read_text(),
        ))

    # ── Ticket TEMPLATE.md (embedded — do not read docs/tickets/TEMPLATE.md) ─
    # Prefer repo-local template; fall back to harness root.
    template_path = repo_root / "docs" / "tickets" / "TEMPLATE.md"
    if not template_path.exists():
        template_path = ROOT / "docs" / "tickets" / "TEMPLATE.md"
    if template_path.exists():
        parts.append(_section(
            "Ticket template (use this when creating new tickets — "
            "do NOT read docs/tickets/TEMPLATE.md separately)",
            template_path.read_text(),
        ))

    out_path.write_text("\n---\n\n".join(parts))
    size_kb = out_path.stat().st_size // 1024 + 1
    diff_line_count = len(diff.strip().splitlines())
    try:
        display_path = out_path.relative_to(ROOT)
    except ValueError:
        display_path = out_path
    print(f"Written {display_path} ({size_kb}KB, {diff_line_count} diff lines)")


if __name__ == "__main__":
    main()
