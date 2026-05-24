from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .git_ops import _get_root


def _result_file(root: Path | None = None) -> Path:
    return (root or _get_root()) / ".git" / "workflow_result.json"


def _audit_log(root: Path | None = None) -> Path:
    return (root or _get_root()) / ".git" / "workflow_audit.log"


def write_result(
    outcome: str,
    details: str,
    diff: str = "",
    root: Path | None = None,
) -> None:
    _result_file(root).write_text(
        json.dumps(
            {
                "outcome": outcome,
                "timestamp": datetime.now().isoformat(),
                "details": details,
                "diff_preview": diff[:2000],
            },
            indent=2,
        )
    )


def write_audit(
    ticket_id: str,
    state: str,
    details: str = "",
    root: Path | None = None,
) -> None:
    with _audit_log(root).open("a") as f:
        f.write(f"{datetime.now().isoformat()} | {ticket_id} | {state} | {details}\n")
