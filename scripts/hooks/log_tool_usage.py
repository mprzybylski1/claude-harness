#!/usr/bin/env python3
"""
PostToolUse hook: append one JSON line per tool call to .git/session_tool_log.jsonl.

Off by default — enable via: python scripts/tools/toggle_telemetry.py on
(creates .git/workflow_telemetry_on sentinel and sets harness.yaml flag)

Log format (one JSON object per line):
    {"ts": 1700000000.0, "tool": "Edit", "path": "scripts/...", "exit": 0, "session": "S6"}

Log location: <harness-root>/.git/session_tool_log.jsonl
  - Inside .git/ so it is never committed or pushed.
  - Rotated (oldest entries discarded) when it exceeds the line threshold.

Rotation threshold: configured via harness.yaml workflow_telemetry_max_lines (default 5000).

Errors (non-JSON-parse failures) are written to .git/session_tool_log.errors
so they surface without breaking tool calls.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SENTINEL = ROOT / ".git" / "workflow_telemetry_on"

_LOG_PATH = ROOT / ".git" / "session_tool_log.jsonl"
_ERR_PATH = ROOT / ".git" / "session_tool_log.errors"
_DEFAULT_MAX_LINES = 5000


def _max_lines(harness: dict) -> int:
    return int(harness.get("workflow_telemetry_max_lines", _DEFAULT_MAX_LINES))


def _current_session() -> str:
    """Read session ID from .git cache, then fall back to deriving from sessions.md."""
    # Fast path: .git/CLAUDE_SESSION_ID (written by session_close_commit_msg.py).
    # The file stores a bare integer (e.g. "6"); normalise to "S6".
    claude_id = ROOT / ".git" / "CLAUDE_SESSION_ID"
    if claude_id.exists():
        val = claude_id.read_text().strip()
        if val:
            return val if val.startswith("S") else f"S{val}"
    # Slow path: re-derive from sessions.md — no subprocess; use the same regex
    # current_session.py uses.
    try:
        import re
        sessions_md = ROOT / "docs" / "sessions.md"
        if sessions_md.exists():
            text = sessions_md.read_text(encoding="utf-8")
            entries = re.findall(r"^S(\d+)\s+\d{4}-\d{2}-\d{2}:", text, re.MULTILINE)
            if entries:
                return f"S{int(entries[-1]) + 1}"
    except Exception:
        pass
    return ""


def _extract_path(tool_name: str, tool_input: dict) -> str:
    if tool_name in ("Edit", "Write", "Read", "NotebookEdit"):
        return tool_input.get("file_path", "")
    if tool_name == "Bash":
        return tool_input.get("command", "")[:120]
    if tool_name == "Agent":
        return tool_input.get("description", "")[:120]
    return ""


def _extract_exit(payload: dict) -> int:
    """Best-effort exit code from tool_response; defaults to 0."""
    response = payload.get("tool_response", {})
    if isinstance(response, dict):
        code = response.get("exit_code")
        if code is not None:
            return int(code)
    return 0


def _rotate_if_needed(path: Path, max_lines: int) -> None:
    if not path.exists():
        return
    try:
        content = path.read_bytes()
        lines = content.splitlines()
        if len(lines) <= max_lines:
            return
        trimmed = b"\n".join(lines[-max_lines:]) + b"\n"
        # Write atomically via temp file + rename
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(trimmed)
        os.replace(str(tmp), str(path))
    except Exception as exc:
        _log_error(f"rotation failed: {exc}")


def _log_error(msg: str) -> None:
    try:
        with _ERR_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
    except Exception:
        pass


def main() -> None:
    # Sentinel-file fast exit: check for .git/workflow_telemetry_on before
    # importing harness_config (which pays a PyYAML + file-read cost).
    # Sentinel is created/removed by scripts/tools/toggle_telemetry.py.
    if not _SENTINEL.exists():
        sys.exit(0)

    sys.path.insert(0, str(ROOT / "scripts" / "tools"))
    import harness_config as _hc
    harness = _hc.load()

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)
    except Exception as exc:
        _log_error(f"stdin read failed: {exc}")
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    record = {
        "ts": time.time(),
        "tool": tool_name,
        "path": _extract_path(tool_name, tool_input),
        "exit": _extract_exit(payload),
        "session": _current_session(),
    }

    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        _log_error(f"append failed: {exc}")
        sys.exit(0)

    _rotate_if_needed(_LOG_PATH, _max_lines(harness))


if __name__ == "__main__":
    main()
