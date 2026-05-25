#!/usr/bin/env python3
"""
Run the 6 static-analysis checks and print a plain-text report.

Exits 0 if all checks PASS.
Exits 1 if any check produces WARN or FAIL.

Usage (from project root):
    python scripts/tools/run_static_analysis.py

Used by the docs-only session-close path to verify no invariant violations
without generating the full Opus review context. If this exits 1, escalate
to a full Opus review regardless of session type.
"""
import sys
from pathlib import Path

# Import check functions from prepare_opus_context without running main()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_opus_context import (
    ROOT,
    check_test_syntax,
    check_utcnow,
    check_eval_exec,
    check_sql_mutations,
    check_exception_swallowing,
    check_bash_blocks,
    check_spec_status_enum,
)
import harness_config as _hc
import workspace_config as _wc

_ALL_CHECKS: dict[str, object] = {
    "test_syntax":          check_test_syntax,
    "utcnow":               check_utcnow,
    "eval_exec":            check_eval_exec,
    "sql_mutations":        check_sql_mutations,
    "exception_swallowing": check_exception_swallowing,
    "bash_blocks":          check_bash_blocks,
    "spec_status_enum":     check_spec_status_enum,
}


def _resolve_checks() -> list:
    """Return the list of check functions to run.

    If harness.yaml specifies static_analysis_checks, use that subset.
    Otherwise run all checks (default behaviour).
    """
    names = _hc.static_analysis_checks()
    if names is None:
        return list(_ALL_CHECKS.values())
    resolved = []
    for name in names:
        fn = _ALL_CHECKS.get(name)
        if fn is None:
            print(f"WARNING: unknown check '{name}' in harness.yaml static_analysis_checks — skipped",
                  file=sys.stderr)
        else:
            resolved.append(fn)
    return resolved


def main() -> None:
    # Enforce workspace isolation: static analysis must only scan declared repos.
    workspace = _wc.active_workspace()
    scan_root = ROOT
    if workspace:
        primary = _wc.primary_repo(workspace)
        if primary:
            _wc.assert_workspace_boundary(primary, workspace)
            scan_root = primary

    checks = _resolve_checks()
    results = [fn(scan_root) for fn in checks]
    for line in results:
        print(line)

    failed = [r for r in results if r.startswith("WARN") or r.startswith("FAIL")]
    if failed:
        print(f"\n{len(failed)} check(s) need attention — escalate to full Opus review.",
              file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\nAll {len(results)} checks PASS.")


if __name__ == "__main__":
    main()
