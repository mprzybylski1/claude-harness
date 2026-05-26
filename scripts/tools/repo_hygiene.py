#!/usr/bin/env python3
"""
Scan the repo for known-stale patterns: retired infrastructure, dead docs, old references.

WARN: could mislead or waste time (operational artifacts that suggest something works when it doesn't)
INFO: housekeeping drift — clutters but doesn't harm

Exit 0 always. All findings are advisory — nothing here blocks the session.

Usage:
    python scripts/tools/repo_hygiene.py             # WARN + INFO
    python scripts/tools/repo_hygiene.py --warn-only  # WARN only
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Paths (relative to REPO_ROOT) where stale references are expected / intentional.
# Files under these prefixes are skipped for all grep patterns.
ALWAYS_SKIP = {
    "docs/archive/",
    "docs/tickets/closed/",
    ".claude/memory/",
    "docs/sessions.md",
    "docs/opus_notes.md",
    "docs/opus_review_context.md",
    ".git/",
    "__pycache__/",
    ".pyc",
    # This script's own source — don't flag its own pattern strings
    "scripts/tools/repo_hygiene.py",
    # Virtual environment — never contains project stale refs
    "venv/",
    # Research output files and backtest results — historical record, not operational
    "research/results/",
    "research/contexts/",
    # Data files
    "data/",
    # Logs
    "logs/",
}

TEXT_EXTENSIONS = {
    ".py", ".md", ".yaml", ".yml", ".json", ".sh", ".txt", ".rst"
}


# ── Stale-file checks ────────────────────────────────────────────────────────
# (severity, rel_path, action_hint)
STALE_FILES = [
    (
        "WARN",
        ".github/workflows/deploy.yml",
        "Pi deploy workflow — still triggers on push to v3; targets retired self-hosted runner; disable or delete",
    ),
    (
        "WARN",
        "scripts/setup_pi.sh",
        "Pi setup script — Pi retired Apr 2026; safe to delete",
    ),
    (
        "WARN",
        "docs/raspberry-pi-setup.md",
        "Pi setup guide — Pi retired; move to docs/archive/ or delete",
    ),
    (
        "WARN",
        "docs/pi_regression_test_plan.md",
        "Pi regression test plan — Pi retired; move to docs/archive/ or delete",
    ),
    (
        "INFO",
        ".claude/skills/pi-status/SKILL.md",
        "pi-status skill — Pi retired; this skill is now a no-op; consider removing",
    ),
    (
        "INFO",
        "docs/gate_check_phase2_S87.md",
        "Phase 2 gate check doc — historical record; consider moving to docs/archive/",
    ),
    (
        "INFO",
        "docs/gate_check_phase3_S87.md",
        "Phase 3 gate check doc — historical record; consider moving to docs/archive/",
    ),
    (
        "INFO",
        "docs/phase3_strategy_validation_checklist.md",
        "Phase 3 validation checklist — Phase 3 closed S114; consider archiving",
    ),
]


# ── Grep-pattern checks ──────────────────────────────────────────────────────
# (severity, label, compiled_regex, extra_skip_prefixes, context_hint)
GREP_PATTERNS = [
    (
        "WARN",
        "pi-ip",
        re.compile(r"192\.168\.1\.171"),
        # CLAUDE.md has an intentional historical mention — still worth showing,
        # it's a candidate for pruning the infrastructure section.
        # test_repo_hygiene.py uses the IP as fixture data to test this very pattern.
        {"tests/test_repo_hygiene.py"},
        "Pi host IP — Pi retired; update or remove",
    ),
    (
        "WARN",
        "update_system_state-pi-row",
        re.compile(r"Pi `192\.168\.1\.171`.*Active"),
        set(),
        "Hardcoded 'Active' Pi row — Pi is retired; fix template in update_system_state.py",
    ),
    (
        "INFO",
        "retired-strategy-in-docs",
        re.compile(r"plumbing_test"),
        # spec file, ibkr variant, test fixtures, test suite, and known docs are valid
        {
            "strategies/specs/plumbing_test_v1.yaml",
            "strategies/specs_ibkr_test/",
            "tests/",
            "docs/tickets/",
            "CLAUDE.md",                   # explicitly documents it as "retired (S146)"
            "docs/project_plan.md",        # static planning blueprint, not operational
            "README.md",                   # architecture tree enumerates files; now labelled "Retired"
        },
        "Retired strategy plumbing_test_v1 mentioned — verify reference is intentional",
    ),
    (
        "INFO",
        "readme-stale-infra",
        re.compile(r"Raspberry Pi|raspberry pi", re.IGNORECASE),
        {
            "docs/raspberry-pi-setup.md",   # stale file already flagged
            ".github/workflows/deploy.yml", # stale file already flagged
            ".claude/skills/pi-status/",
            "CLAUDE.md",                    # intentional historical context
            # IBKR runbook ARM64 section is architecture docs — still relevant
            "docs/ibkr_gateway_runbook.md",
        },
        "Raspberry Pi reference — Pi retired; check if still accurate",
    ),
    (
        "INFO",
        "settings-local-stale-scp",
        re.compile(r"scp pi@192\.168"),
        set(),
        "Stale scp permission in settings.local.json — Pi retired; remove these allow entries",
    ),
]


# ────────────────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: str
    category: str
    location: str    # "path:line" or just "path" for file checks
    detail: str
    hint: str


def _is_exempt(rel: str) -> bool:
    for prefix in ALWAYS_SKIP:
        if rel.startswith(prefix) or rel == prefix.rstrip("/"):
            return True
    return False


def _is_extra_exempt(rel: str, extra: set[str]) -> bool:
    for prefix in extra:
        if rel.startswith(prefix) or rel == prefix.rstrip("/"):
            return True
    return False


def check_test_imports(tests_dir: Path) -> list[Finding]:
    """WARN for each test file that fails pytest --collect-only (broken imports).

    Best-effort: if pytest is unavailable or the tests dir doesn't exist, returns [].
    """
    if not tests_dir.is_dir():
        return []
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", str(tests_dir)],
            capture_output=True, text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []

    if result.returncode == 0:
        return []

    findings = []
    combined = result.stdout + result.stderr
    # Pytest reports "ERROR collecting <file>" and "ImportError: ..." lines
    for line in combined.splitlines():
        if "ERROR collecting" in line or "ImportError" in line or "ModuleNotFoundError" in line:
            findings.append(Finding(
                severity="WARN",
                category="test-import-error",
                location="tests/",
                detail=line.strip()[:120],
                hint="Fix the import error — broken test files prevent the full suite from running",
            ))
    return findings


def check_stale_files() -> list[Finding]:
    findings = []
    for severity, rel, hint in STALE_FILES:
        path = REPO_ROOT / rel
        if path.exists():
            findings.append(Finding(
                severity=severity,
                category="stale-file",
                location=rel,
                detail="file exists",
                hint=hint,
            ))
    return findings


def check_grep_patterns() -> list[Finding]:
    findings = []
    all_files = [
        p for p in REPO_ROOT.rglob("*")
        if p.is_file() and p.suffix in TEXT_EXTENSIONS
    ]

    for severity, label, pattern, extra_skip, hint in GREP_PATTERNS:
        for path in all_files:
            rel = str(path.relative_to(REPO_ROOT))
            if _is_exempt(rel) or _is_extra_exempt(rel, extra_skip):
                continue
            try:
                for lineno, line in enumerate(
                    path.read_text(errors="replace").splitlines(), 1
                ):
                    if pattern.search(line):
                        excerpt = line.strip()[:80]
                        findings.append(Finding(
                            severity=severity,
                            category=label,
                            location=f"{rel}:{lineno}",
                            detail=excerpt,
                            hint=hint,
                        ))
            except OSError:
                continue

    return findings


_DIGEST_STALE_DAYS = 8   # Miss one Friday → warn on next Monday session


def check_stale_ops_digest() -> list[Finding]:
    """WARN if the weekly ops digest has not been written in over 8 days.

    Only fires when logs/digests/ exists (i.e. cron has run at least once).
    Silent on a fresh clone — avoids false alarms before the system is set up.
    """
    digests_dir = REPO_ROOT / "logs" / "digests"
    if not digests_dir.exists():
        return []

    digest_files = sorted(digests_dir.glob("weekly_*.md"))
    if not digest_files:
        return [Finding(
            severity="WARN",
            category="stale-ops-digest",
            location="logs/digests/",
            detail="directory exists but no weekly_*.md found",
            hint="Weekly ops digest never produced — check cron: 0 22 * * 5 (Friday 22:00 BST)",
        )]

    latest = max(digest_files, key=lambda p: p.stat().st_mtime)
    age_days = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
    if age_days > _DIGEST_STALE_DAYS:
        return [Finding(
            severity="WARN",
            category="stale-ops-digest",
            location=str(latest.relative_to(REPO_ROOT)),
            detail=f"{age_days}d old (threshold {_DIGEST_STALE_DAYS}d) — expected weekly Friday 22:00 BST",
            hint="Weekly ops digest is stale — verify cron is installed and running",
        )]

    return []


def main() -> None:
    warn_only = "--warn-only" in sys.argv

    tests_dir = REPO_ROOT / "tests"
    for i, arg in enumerate(sys.argv):
        if arg == "--tests-dir" and i + 1 < len(sys.argv):
            tests_dir = Path(sys.argv[i + 1])
            break

    findings = (
        check_stale_files()
        + check_grep_patterns()
        + check_stale_ops_digest()
        + check_test_imports(tests_dir)
    )

    if warn_only:
        findings = [f for f in findings if f.severity == "WARN"]

    warns = [f for f in findings if f.severity == "WARN"]
    infos = [f for f in findings if f.severity == "INFO"]

    if not findings:
        level = "WARN" if warn_only else "WARN + INFO"
        print(f"(repo hygiene clean — no findings at {level})")
        return

    print(f"Repo hygiene: {len(warns)} WARN, {len(infos)} INFO\n")

    for severity, group in (("WARN", warns), ("INFO", infos)):
        if not group or (warn_only and severity == "INFO"):
            continue
        print(f"=== {severity} ===")
        for f in group:
            print(f"  [{f.category}]  {f.location}")
            print(f"    {f.hint}")
            if f.detail != "file exists":
                print(f"    → {f.detail}")
        print()


if __name__ == "__main__":
    main()
