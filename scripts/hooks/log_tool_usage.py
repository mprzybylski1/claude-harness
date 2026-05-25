#!/usr/bin/env python3
"""
PostToolUse hook: append one JSON line per tool call to .git/session_tool_log.jsonl.

Off by default — opt in via harness.yaml:
    workflow_telemetry: true

Log format (one JSON object per line):
    {"ts": 1700000000.0, "tool": "Edit", "path": "scripts/...", "exit": 0, "session": "S6"}

Log location: <harness-root>/.git/session_tool_log.jsonl
  - Inside .git/ so it is never committed or pushed.
  - Rotated (oldest entries discarded) when it exceeds the line threshold.

Rotation threshold: configured via harness.yaml workflow_telemetry_max_lines (default 5000).
"""
from __future__ import annotations

import json
import sys
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
import harness_config as _hc

_LOG_PATH = ROOT / ".git" / "session_tool_log.jsonl"
_DEFAULT_MAX_LINES = 5000


def _telemetry_enabled(harness: dict) -> bool:
    return bool(harness.get("workflow_telemetry", False))


def _max_lines(harness: dict) -> int:
    return int(harness.get("workflow_telemetry_max_lines", _DEFAULT_MAX_LINES))


def _current_session() -> str:
    script = ROOT / "scripts" / "tools" / "current_session.py"
    if not script.exists():
        return ""
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=ROOT)
    return r.stdout.strip() if r.returncode == 0 else ""


def _extract_path(tool_name: str, tool_input: dict) -> str:
    if tool_name in ("Edit", "Write", "Read", "NotebookEdit"):
        return tool_input.get("file_path", "")
    if tool_name == "Bash":
        return tool_input.get("command", "")[:120]
    if tool_name == "Agent":
        return tool_input.get("description", "")[:120]
    return ""


def _rotate_if_needed(path: Path, max_lines: int) -> None:
    if not path.exists():
        return
    lines = path.read_bytes().splitlines()
    if len(lines) > max_lines:
        # Keep only the most recent max_lines entries
        path.write_bytes(b"\n".join(lines[-max_lines:]) + b"\n")


def main() -> None:
    harness = _hc.load()
    if not _telemetry_enabled(harness):
        sys.exit(0)

    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    record = {
        "ts": time.time(),
        "tool": tool_name,
        "path": _extract_path(tool_name, tool_input),
        "exit": 0,
        "session": _current_session(),
    }

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    _rotate_if_needed(_LOG_PATH, _max_lines(harness))


if __name__ == "__main__":
    main()
