"""Load harness.yaml configuration with project-specific fallbacks.

All values are optional — if harness.yaml is absent or a key is missing,
scripts fall back to their current hardcoded behaviour so this project
continues to work unchanged when harness.yaml is not present.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_HARNESS_PATH = _ROOT / "harness.yaml"


def load() -> dict:
    """Return the harness.yaml dict, or {} if absent or unreadable."""
    if not _HARNESS_PATH.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(_HARNESS_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def session_close_prefix(harness: dict | None = None) -> str:
    """Return the session-close commit message prefix (default: 'docs: S')."""
    if harness is None:
        harness = load()
    return harness.get("session_close_prefix", "docs: S")


def code_paths(harness: dict | None = None) -> tuple[str, ...]:
    """Return the tuple of path prefixes that classify a session as 'code'."""
    if harness is None:
        harness = load()
    paths = harness.get("code_paths")
    if paths:
        return tuple(paths)
    # Default: current trading-project hardcoded list
    return (
        "core/",
        "data/",
        "execution/",
        "infra/",
        "research/",
        "strategies/",
        "dashboard/",
        "tests/",
        "main.py",
        "config.yaml",
        "requirements.txt",
    )


def tickets_dir(harness: dict | None = None) -> str:
    """Return the relative path to the open tickets directory."""
    if harness is None:
        harness = load()
    return harness.get("tickets_dir", "docs/tickets/open")


def static_analysis_checks(harness: dict | None = None) -> list[str] | None:
    """Return the list of check names to run, or None to run all checks.

    If harness.yaml specifies static_analysis_checks, only those named checks
    are run. If the key is absent, None is returned and all checks run (default).
    Check names correspond to prepare_opus_context.py function names without the
    'check_' prefix, e.g. 'test_syntax', 'eval_exec', 'sql_mutations'.
    """
    if harness is None:
        harness = load()
    return harness.get("static_analysis_checks", None)
