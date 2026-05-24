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

# Priority tiers for signal blocks when truncating. Tier 0 fills first (safety-critical);
# tier 3 is trimmed first. Files not matching any tier get tier 1 (default).
_TIER_CORE = ("core/", "strategies/runtime.py", "execution/", "main.py")   # tier 0
_TIER_SCRIPTS = ("scripts/", ".claude/")                                    # tier 1 (same as default)
_TIER_TESTS = ("tests/",)                                                   # tier 2
_TIER_RESEARCH = ("research/",)                                             # tier 3


def _priority_tier(path: str) -> int:
    if any(path.startswith(p) or path == p.rstrip("/") for p in _TIER_CORE):
        return 0
    if any(path.startswith(p) for p in _TIER_RESEARCH):
        return 3
    if any(path.startswith(p) for p in _TIER_TESTS):
        return 2
    return 1


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


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
    - Signal blocks are filled in priority order: core/strategies/execution/main.py first,
      then other, then tests/, then research/ — so safety-critical code is never truncated
      at the expense of test or research files.
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
    test_files = sorted((root / "tests").glob("test_*.py"))
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
    """2. Grep for deprecated datetime.utcnow() in production directories."""
    prod_dirs = ["core", "data", "execution", "infra", "research", "scripts", "strategies"]
    existing = [str(root / d) for d in prod_dirs if (root / d).exists()]
    if not existing:
        return "SKIP  no production directories found"
    r = subprocess.run(
        ["grep", "-rn", "--include=*.py",
         "--exclude=prepare_opus_context.py",   # avoid self-match on grep pattern string
         "--exclude=run_static_analysis.py",    # imports check_utcnow — not a usage site
         "utcnow"] + existing,
        capture_output=True, text=True,
    )
    hits = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if hits:
        return ("WARN  deprecated datetime.utcnow() usage:\n"
                + "\n".join(f"  {h}" for h in hits))
    return "PASS  no datetime.utcnow() in production code"


def check_eval_exec(root: Path) -> str:
    """3. AST scan for eval()/exec() Call nodes in strategies/ (closed indicator set invariant).

    AST-based (not grep) so comments and docstrings are not matched.
    """
    import ast as _ast
    eval_hits = []
    for py_file in sorted((root / "strategies").rglob("*.py")):
        try:
            tree = _ast.parse(py_file.read_text())
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Call):
                func = node.func
                name = (
                    func.id if isinstance(func, _ast.Name) else
                    func.attr if isinstance(func, _ast.Attribute) else None
                )
                if name in ("eval", "exec"):
                    rel = py_file.relative_to(root)
                    eval_hits.append(f"  {rel}:{node.lineno}: {name}()")
    if eval_hits:
        return ("FAIL  eval()/exec() calls found in strategies/ (invariant violation):\n"
                + "\n".join(eval_hits))
    return "PASS  no eval()/exec() calls in strategies/"


def check_sql_mutations(root: Path) -> str:
    """4. Grep for UPDATE/DELETE SQL strings in audit_log.py (append-only invariant).

    Pattern matches a quote character immediately before the SQL keyword to avoid
    matching docstring prose like "never UPDATE or DELETE".

    Also scans scripts/tools/migrate_*.py for DELETE strings and reports them as
    INFO (not FAIL) — migration scripts are permitted under the
    architecture_invariants.md operator carve-out (T257 S166), but must be flagged
    so Opus can verify the six carve-out requirements are met.
    """
    audit = root / "infra" / "audit_log.py"
    if not audit.exists():
        return "SKIP  infra/audit_log.py not found"
    r = subprocess.run(
        ["grep", "-nE", r"""['"](UPDATE|DELETE) """, str(audit)],
        capture_output=True, text=True,
    )
    hits = [ln for ln in r.stdout.splitlines() if ln.strip()]
    if hits:
        return ("FAIL  UPDATE/DELETE SQL string in infra/audit_log.py (invariant violation):\n"
                + "\n".join(f"  {h}" for h in hits))

    # Search both tools/ (legacy location) and migrations/ for migrate_*.py.
    # glob() on a non-existent dir returns an empty iterator — no exists() guard needed.
    migrate_scripts = sorted(
        list((root / "scripts" / "tools").glob("migrate_*.py"))
        + list((root / "scripts" / "migrations").glob("migrate_*.py"))
    )
    migrate_hits = []
    for script in migrate_scripts:
        # Use word-boundary pattern (not quote-prefix) so multiline SQL strings are caught.
        r2 = subprocess.run(
            ["grep", "-niE", r"\b(UPDATE|DELETE)\b", str(script)],
            capture_output=True, text=True,
        )
        for ln in r2.stdout.splitlines():
            if ln.strip():
                migrate_hits.append(f"  {script.name}: {ln.strip()}")
    if migrate_hits:
        return (
            "PASS  no UPDATE/DELETE SQL in infra/audit_log.py\n"
            "INFO  migration scripts with DELETE/UPDATE (operator carve-out — verify six requirements in architecture_invariants.md):\n"
            + "\n".join(migrate_hits)
        )
    return "PASS  no UPDATE/DELETE SQL strings in infra/audit_log.py"



# Return values that indicate real exception swallowing (bare defaults / None / falsy literals).
# Returns of a constructed result object (e.g. return SomeResult(passed=False, ...)) are
# the documented fail-closed pattern and must NOT be flagged.
_SWALLOW_RETURN = re.compile(
    r"""^\s*(?:
        pass
        | return \s* (?:None|False|0\.0|0|\[\]|\{\}|""|'')? \s* (?:\#.*)?
    )$""",
    re.VERBOSE,
)


def check_exception_swallowing(root: Path) -> str:
    """5. Heuristic scan for exception swallowing in core/ (pass or bare-default return).

    Pure-Python line scanner — avoids grep context-line format ambiguity.

    Flags: except clause followed immediately (next non-blank line) by:
      - pass
      - return  (bare, no value)
      - return None / False / 0 / 0.0 / [] / {} / "" / ''

    Does NOT flag: return of a constructed result object (e.g. the documented
    fail-closed pattern: ``return SomeResult(passed=False, reason=str(e))``),
    a named variable, or a function call. Also does not flag re-raise (raise) or
    logging patterns.

    This is a heuristic — findings need manual verification.
    """
    swallowed = []
    for py_file in sorted((root / "core").rglob("*.py")):
        try:
            lines = py_file.read_text().splitlines()
        except OSError:
            continue
        rel = py_file.relative_to(root)
        for i, line in enumerate(lines):
            if not re.search(r"\bexcept\b", line):
                continue
            # Scan forward for the first non-empty continuation line
            for j in range(i + 1, min(i + 4, len(lines))):
                next_line = lines[j]
                if not next_line.strip():
                    continue  # skip blank lines
                if _SWALLOW_RETURN.match(next_line):
                    swallowed.append(
                        f"  {rel}:{i + 1}: {line.strip()} → {next_line.strip()}"
                    )
                break  # stop at first non-blank line regardless
    if swallowed:
        return ("WARN  possible exception swallowing in core/ (verify manually):\n"
                + "\n".join(swallowed[:10]))
    return "PASS  no obvious exception swallowing in core/"


def check_bash_blocks(root: Path) -> str:
    """6. Run check_skill_bash_blocks.py to validate bash fenced blocks in SKILL.md."""
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


def check_spec_status_enum(root: Path) -> str:
    """7. Verify every strategies/specs/*.yaml has a status: value in StrategyStatus enum (T226).

    Catches the S141+S142 pattern where specs used status: "killed" before the enum had that
    value, causing SpecLoader.load_all to silently swallow ValidationErrors every cron run.
    """
    specs_dir = root / "strategies" / "specs"
    if not specs_dir.exists():
        return "SKIP  strategies/specs/ not found"

    # Extract valid values directly from the enum source to avoid importing the module
    schemas_src = (root / "core" / "schemas.py").read_text()
    enum_block_match = re.search(
        r"class StrategyStatus.*?(?=\nclass |\Z)", schemas_src, re.DOTALL
    )
    if not enum_block_match:
        return "SKIP  StrategyStatus enum not found in core/schemas.py"
    valid_values = set(re.findall(r'"([^"]+)"', enum_block_match.group()))

    status_re = re.compile(r'^\s*status:\s*["\']?(\w+)["\']?', re.MULTILINE)
    mismatches = []
    for yaml_file in sorted(specs_dir.glob("*.yaml")):
        text = yaml_file.read_text()
        m = status_re.search(text)
        if not m:
            continue
        val = m.group(1)
        if val not in valid_values:
            mismatches.append(f"  {yaml_file.name}: status={val!r} not in StrategyStatus enum")

    if mismatches:
        return ("FAIL  spec files with invalid status enum value (SpecLoader will swallow ValidationError):\n"
                + "\n".join(mismatches))
    return f"PASS  all {sum(1 for _ in specs_dir.glob('*.yaml'))} spec files have valid StrategyStatus values"


def _static_analysis(root: Path = ROOT) -> str:
    """
    Run all 7 pre-flight invariant checks. Returns a human-readable summary.
    Opus reads this section instead of reading source files to verify findings.
    Each check returns PASS / WARN / FAIL / SKIP with details on failure.
    """
    checks = [
        check_test_syntax,
        check_utcnow,
        check_eval_exec,
        check_sql_mutations,
        check_exception_swallowing,
        check_bash_blocks,
        check_spec_status_enum,
    ]
    return "\n".join(fn(root) for fn in checks)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
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
    log_out = _run(["git", "log", "--oneline", f"--grep={_SESSION_CLOSE_PREFIX}", "-20"]).stdout
    log_lines = [ln.strip() for ln in log_out.splitlines() if ln.strip()]
    if log_lines:
        base_sha = log_lines[0].split()[0]

    if base_sha:
        log = _run(["git", "log", f"{base_sha}..HEAD", "--oneline"]).stdout
        parts.append(_section(
            f"Commits since last session-close ({base_sha[:12]})",
            log.strip() or "(none — all changes are uncommitted)",
        ))
    else:
        parts.append("## Warning\n\nNo prior 'session close' commit found.\n")

    # ── Session diff ──────────────────────────────────────────────────────────
    if base_sha:
        diff = _run(["git", "diff", f"{base_sha}..HEAD"]).stdout
        diff_stat = _run(["git", "diff", f"{base_sha}..HEAD", "--stat"]).stdout
    else:
        diff = _run(["git", "diff", "main...HEAD"]).stdout
        diff_stat = _run(["git", "diff", "main...HEAD", "--stat"]).stdout

    capped_diff, was_truncated, truncated_paths = _apply_diff_cap(diff.strip(), MAX_DIFF_LINES)
    if was_truncated:
        parts.append(_section("Session diff — stat (full diff truncated)", diff_stat))
        parts.append(_section(
            f"Session diff — priority-ordered, cap {MAX_DIFF_LINES} signal lines "
            f"(core/strategies/execution first; docs/tickets/ and docs/archive/ excluded; governance appended in full)",
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
    unstaged = _run(["git", "diff", "HEAD"]).stdout
    staged = _run(["git", "diff", "--cached"]).stdout
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
                           _static_analysis()))

    # ── Trimmed docs/sessions.md ──────────────────────────────────────────────
    sessions_path = ROOT / "docs" / "sessions.md"
    if sessions_path.exists():
        trimmed = _trim_sessions_md(sessions_path.read_text())
        parts.append(_section("docs/sessions.md (trimmed)", trimmed))

    # ── docs/architecture_invariants.md ──────────────────────────────────────
    inv_path = ROOT / "docs" / "architecture_invariants.md"
    if inv_path.exists():
        parts.append(_section("docs/architecture_invariants.md", inv_path.read_text()))

    # ── Ticket TEMPLATE.md (embedded — do not read docs/tickets/TEMPLATE.md) ─
    template_path = ROOT / "docs" / "tickets" / "TEMPLATE.md"
    if template_path.exists():
        parts.append(_section(
            "Ticket template (use this when creating new tickets — "
            "do NOT read docs/tickets/TEMPLATE.md separately)",
            template_path.read_text(),
        ))

    OUT.write_text("\n---\n\n".join(parts))
    size_kb = OUT.stat().st_size // 1024 + 1
    diff_line_count = len(diff.strip().splitlines())
    print(f"Written {OUT.relative_to(ROOT)} ({size_kb}KB, {diff_line_count} diff lines)")


if __name__ == "__main__":
    main()
