#!/usr/bin/env python3
"""
Run static-analysis checks and print a plain-text report.

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
    check_bash_blocks,
)
import harness_config as _hc
import workspace_config as _wc

_ALL_CHECKS: dict[str, object] = {
    "test_syntax": check_test_syntax,
    "utcnow":      check_utcnow,
    "bash_blocks": check_bash_blocks,
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


def _run_checks_for_repo(scan_root: Path, label: str) -> list[str]:
    # T044 audit: assert_workspace_boundary() is called by main() on scan_root
    # before this function is invoked, so scan_root itself is guaranteed to be
    # inside the declared workspace. Individual check functions in
    # prepare_opus_context.py are further hardened:
    #   - check_test_syntax: filters symlinks that resolve outside scan_root via
    #     _is_within_root() before passing files to py_compile.
    #   - check_utcnow: uses grep -r which does not dereference symlink dirs;
    #     symlink files are followed but only one file is read (not traversed).
    #   - check_bash_blocks: path anchored to scan_root; no direct file opens.
    print(f"--- [{label}] ---")
    checks = _resolve_checks()
    results = [fn(scan_root) for fn in checks]
    for line in results:
        print(line)
    return results


def main() -> None:
    workspace = _wc.active_workspace()
    all_results: list[str] = []

    if workspace:
        primary = _wc.primary_repo(workspace)
        if primary:
            _wc.assert_workspace_boundary(primary, workspace)
            ws_name = workspace.get("name", "primary")
            all_results.extend(_run_checks_for_repo(primary, f"{ws_name}: primary"))

        for sec_path in _wc.secondary_repos(workspace):
            _wc.assert_workspace_boundary(sec_path, workspace)
            sec_name = sec_path.name
            for repo in _wc.all_repos(workspace):
                if Path(repo["path"]).expanduser().resolve() == sec_path:
                    sec_name = repo.get("name", sec_path.name)
                    break
            print()
            all_results.extend(_run_checks_for_repo(sec_path, f"{sec_name}: secondary"))
    else:
        all_results.extend(_run_checks_for_repo(ROOT, "harness"))

    failed = [r for r in all_results if r.startswith("WARN") or r.startswith("FAIL")]
    if failed:
        print(f"\n{len(failed)} check(s) need attention — escalate to full Opus review.",
              file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\nAll {len(all_results)} checks PASS.")


if __name__ == "__main__":
    main()
