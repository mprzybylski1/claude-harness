#!/usr/bin/env python3
"""
PostToolUse hook: append one JSON line per tool call to .git/session_tool_log.jsonl.

On by default when harness.yaml has workflow_telemetry: true.
Toggle via: python scripts/tools/toggle_telemetry.py on|off|status
(manages .git/workflow_telemetry_on sentinel and harness.yaml in sync)

Log format (one JSON object per line):
    {"ts": 1700000000.0, "tool": "Edit", "path": "scripts/...",
     "session": "S6", "workspace": "scrabble-score"}

Session/workspace stamping (T057):
  - The tool call's target path(s) are matched against every active workspace's
    declared repos. If the path lies inside a workspace, that workspace's
    sessions.md is read directly to derive S<N>. If no workspace matches,
    harness-root docs/sessions.md is used and "workspace" is "".
  - The hook does NOT read .git/CLAUDE_SESSION_ID. That cache is written by
    current_session.py and gets clobbered by mixed harness/workspace callers,
    so it cannot be trusted for per-call stamping.

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

try:
    import fcntl as _fcntl
except ImportError:
    _fcntl = None

ROOT = Path(__file__).resolve().parents[2]
_SENTINEL = ROOT / ".git" / "workflow_telemetry_on"

_LOG_PATH = ROOT / ".git" / "session_tool_log.jsonl"
_ERR_PATH = ROOT / ".git" / "session_tool_log.errors"
_ERR_STATE_PATH = ROOT / ".git" / "session_tool_log.errors.state"
_DEFAULT_MAX_LINES = 5000

_ERR_RATE_LIMIT = 10
_ERR_WINDOW_SECS = 60


def _max_lines(harness: dict) -> int:
    return int(harness.get("workflow_telemetry_max_lines", _DEFAULT_MAX_LINES))


def _list_workspaces() -> list[tuple[str, dict]]:
    """Return [(slug, cfg), ...] for active workspaces. Wrapped so tests can mock.

    Fails open: returns [] if workspace_config cannot be imported or raises.
    Telemetry must never break tool calls.
    """
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import workspace_config as _wc
        return _wc.list_active_workspaces()
    except Exception as exc:
        _log_error(f"list_active_workspaces failed: {exc}")
        return []


def _candidate_paths(tool_name: str, tool_input: dict) -> list[str]:
    """Extract path-like tokens from the tool input for workspace matching."""
    if tool_name in ("Edit", "Write", "Read", "NotebookEdit"):
        fp = tool_input.get("file_path", "")
        return [fp] if fp else []
    if tool_name == "Bash":
        import shlex
        cmd = tool_input.get("command", "")
        try:
            parts = shlex.split(cmd)
        except ValueError:
            parts = cmd.split()
        tokens: list[str] = []
        for raw in parts:
            t = raw.strip("'\"`")
            if "=" in t and not (t.startswith("/") or t.startswith("~/")):
                t = t.rsplit("=", 1)[1].strip("'\"`")
            if t.startswith("/") or t.startswith("~/"):
                tokens.append(t)
        return tokens
    return []


def _detect_workspace(tool_name: str, tool_input: dict) -> tuple[str, dict | None]:
    """Return (slug, cfg) for the workspace this tool call targets, or ("", None)."""
    paths = _candidate_paths(tool_name, tool_input)
    if not paths:
        return ("", None)
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import workspace_config as _wc
    except Exception as exc:
        _log_error(f"workspace_config import failed: {exc}")
        return ("", None)
    workspaces = _list_workspaces()
    for path in paths:
        for slug, cfg in workspaces:
            try:
                if _wc.is_within_workspace(Path(path).expanduser(), cfg):
                    return (slug, cfg)
            except Exception as exc:
                _log_error(f"workspace match failed for {slug}: {exc}")
    return ("", None)


def _session_for_workspace(ws_dir: Path | None, ws_cfg: dict | None) -> str:
    """Read sessions.md from the workspace (if any) or harness root, return next S<N>.

    Resolves sessions.md without calling workspace_config.internal_dir so it
    works correctly even when ws_dir is None (e.g. workspace_dir() failed in
    main). Priority: cfg['docs_path'] > ws_dir/internal > harness root.
    """
    import re
    if ws_cfg is not None:
        try:
            docs_path = ws_cfg.get("docs_path")
            if docs_path:
                sessions_md = Path(docs_path).expanduser().resolve() / "sessions.md"
            elif ws_dir is not None:
                sessions_md = ws_dir / "internal" / "sessions.md"
            else:
                _log_error("workspace detected but ws_dir is None and no docs_path in cfg")
                return ""
        except Exception as exc:
            _log_error(f"sessions.md path resolution failed: {exc}")
            return ""
    else:
        sessions_md = ROOT / "docs" / "sessions.md"
    try:
        if not sessions_md.exists():
            if ws_cfg is not None:
                _log_error(f"sessions.md missing: {sessions_md}")
            return ""
        text = sessions_md.read_text(encoding="utf-8")
        entries = re.findall(r"^S(\d+)\s+\d{4}-\d{2}-\d{2}:", text, re.MULTILINE)
        if entries:
            return f"S{int(entries[-1]) + 1}"
    except Exception as exc:
        _log_error(f"sessions.md read failed: {exc}")
    return ""


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
        now = time.time()
        count, window_start = 0, 0.0
        try:
            with open(_ERR_STATE_PATH, "a+", encoding="utf-8") as fd:
                if _fcntl is not None:
                    _fcntl.flock(fd.fileno(), _fcntl.LOCK_EX)
                fd.seek(0)
                try:
                    state = json.loads(fd.read())
                    count = int(state["count"])
                    window_start = float(state["window_start"])
                except Exception:
                    pass
                if now - window_start >= _ERR_WINDOW_SECS:
                    count = 0
                    window_start = now
                if count > _ERR_RATE_LIMIT:
                    return
                count += 1
                fd.seek(0)
                fd.truncate()
                fd.write(json.dumps({"count": count, "window_start": window_start}))
        except Exception:
            pass
        if count > _ERR_RATE_LIMIT:
            msg = "[rate-limit engaged — further errors suppressed]"
        with _ERR_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
    except Exception:
        pass


def _yaml_telemetry_enabled() -> bool:
    """Stdlib-only check: is workflow_telemetry: true in harness.yaml?"""
    import re
    harness_yaml = ROOT / "harness.yaml"
    if not harness_yaml.exists():
        return False
    try:
        text = harness_yaml.read_text(encoding="utf-8")
        return bool(re.search(r"^\s*workflow_telemetry\s*:\s*true\s*$", text, re.MULTILINE))
    except Exception:
        return False


def main() -> None:
    # Fast path: sentinel present → telemetry on, skip YAML check.
    # Bootstrap: sentinel absent but harness.yaml says true → create sentinel,
    # then proceed.  This makes telemetry self-activating on a fresh clone
    # without requiring a manual toggle_telemetry.py on.
    if not _SENTINEL.exists():
        if not _yaml_telemetry_enabled():
            sys.exit(0)
        try:
            _SENTINEL.parent.mkdir(parents=True, exist_ok=True)
            _SENTINEL.touch()
        except Exception as exc:
            _log_error(f"bootstrap sentinel create failed: {exc}")
        # Exit without logging this first call — next call hits the fast path.
        # Dropping one record on fresh-clone bootstrap is acceptable.
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

    slug, ws_cfg = _detect_workspace(tool_name, tool_input)
    ws_dir: Path | None = None
    if ws_cfg is not None and not ws_cfg.get("docs_path"):
        # ws_dir only needed when docs_path is absent; errors fall-open.
        try:
            import workspace_config as _wc
            ws_dir = _wc.workspace_dir(slug)
        except Exception:
            ws_dir = None

    record = {
        "ts": time.time(),
        "tool": tool_name,
        "path": _extract_path(tool_name, tool_input),
        "session": _session_for_workspace(ws_dir, ws_cfg),
        "workspace": slug,
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
