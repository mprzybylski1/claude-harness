"""
Hash guard for orchestrator self-integrity.

Scope: scripts/workflows/**/*.py ONLY.

This module protects the orchestrator's own code from being modified by a spawned agent.
It is NOT a general change-detector for all repo files.

Strategy specs (strategies/specs/*.yaml) are intentionally excluded here. Adding them
would cause spec changes to be reverted at CHECKING_HASHES instead of flowing through
to AWAITING_ARCHITECTURE_REVIEW — which is the correct protective route. Any change to
strategies/specs/ is caught by `_SAFETY_PREFIXES` in git_ops.py, which routes the outcome
to AWAITING_ARCHITECTURE_REVIEW (diff held, not reverted, human architecture review required
before any commit).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .git_ops import _get_root


def _workflows_dir(root: Path | None = None) -> Path:
    return (root or _get_root()) / "scripts" / "workflows"


def compute(root: Path | None = None) -> dict[str, str]:
    wdir = _workflows_dir(root)
    return {
        str(p.relative_to(wdir.parent.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in wdir.rglob("*.py")
        if p.exists()
    }


def check(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed = [p for p in before if before[p] != after.get(p, "MISSING")]
    added = [p for p in after if p not in before]
    return changed + added
