#!/usr/bin/env python3
"""
PostToolUse hook: append one JSON line per tool call to .git/session_tool_log.jsonl.

On by default when harness.yaml has workflow_telemetry: true.
Toggle via: python scripts/tools/toggle_telemetry.py on|off|status
(manages .git/workflow_telemetry_on sentinel and harness.yaml in sync)

Log format (one JSON object per line):
    {"ts": 1700000000.0, "tool": "Edit", "path": "scripts/...",
     "session": "S6", "workspace": "scrabble-score",
     "claude_session_uuid": "e693d4fb-..."}

Session/workspace stamping (T137, was T057):
  - Attribution is by the ACTIVE session, read from .claude/.active_workspace via
    workspace_config.read_session_state (cwd-independent), NOT by the path of the
    touched file. A workspace session stamps (slug, that workspace's S<N>); a
    harness/undeclared session stamps ("", harness S<N>). Every call in a session
    therefore carries that session's (workspace, S<N>), so analyze_tool_log's
    (workspace, session) filter never collides across layers (SR-010). The prior
    path-based scheme (T057) under-attributed any call that didn't touch a declared
    repo file (bare Bash, harness-file reads) to the harness layer.
  - claude_session_uuid = the native JSONL transcript filename — a live join key
    to richer per-call data (tokens, full I/O) without a parallel logger. Sourced
    from the stdin payload's session_id (then transcript_path stem, then the
    CLAUDE_CODE_SESSION_ID env var as last resort); the env var alone is unset in
    many session contexts, which left ~68% of records with an empty uuid (T156).
    The join itself is deferred (see T141 ticket).
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

# Set to True after the first one-shot bootstrap/state-error message is emitted to
# stderr, so subsequent calls in the same process don't repeat it.
_BOOTSTRAP_STDERR_LOGGED = False


def _max_lines(harness: dict) -> int:
    return int(harness.get("workflow_telemetry_max_lines", _DEFAULT_MAX_LINES))


def _active_workspace_and_sessions_md() -> tuple[str, Path | None]:
    """Resolve (workspace, sessions_md) from the session-declared state (T137).

    Attribution is by the ACTIVE session, read from .claude/.active_workspace via
    workspace_config (cwd-independent), NOT by the path of the touched file:
      - workspace session → (slug, that workspace's sessions.md)
      - harness / undeclared → ("", harness docs/sessions.md)

    This is the SR-008/009/010 helper convergence — the same resolver
    generate_ticket_index.py uses (T136). A session's records all carry that
    session's (workspace, S<N>), so analyze_tool_log's (workspace, session)
    filter never collides across layers (the SR-010 bug).

    Fails open: any error → ("", harness sessions.md). Telemetry must never break
    a tool call.
    """
    harness_sessions = ROOT / "docs" / "sessions.md"
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import workspace_config as _wc
        state, slug = _wc.read_session_state(root=ROOT)
        if state == _wc.STATE_WORKSPACE:
            paths = _wc.workspace_paths(slug, root=ROOT)
            if paths is not None:
                return (slug, paths[1])
            _log_error(f"active workspace '{slug}' has no resolvable internal dir")
            return (slug, None)
        return ("", harness_sessions)
    except Exception as exc:
        _log_error(f"active-workspace resolution failed: {exc}")
        return ("", harness_sessions)


def _session_from_sessions_md(sessions_md: Path | None) -> str:
    """Derive S<N> (last-logged + 1) from a sessions.md, or '' on any failure.

    NOTE (T137 / T139): last-logged+1 over-counts by one for records written
    after the running session's Session Log line is appended at close. This is
    the same timing skew T139 fixed for SR stamping; it is pre-existing here
    (path-based stamping had it too) and out of scope for T137. The live
    claude_session_uuid field is the stable join key that lets a future pass
    reconcile attribution against the native transcript regardless of the skew.
    """
    if sessions_md is None:
        return ""
    import re
    try:
        if not sessions_md.exists():
            return ""
        text = sessions_md.read_text(encoding="utf-8")
        entries = re.findall(r"^S(\d+)\s+\d{4}-\d{2}-\d{2}:", text, re.MULTILINE)
        if entries:
            return f"S{int(entries[-1]) + 1}"
    except Exception as exc:
        _log_error(f"session derivation failed: {exc}")
    return ""


def _session_uuid(payload: dict) -> str:
    """Return the native session/transcript UUID for the join key (T156).

    Source priority:
      1. payload["session_id"] — Claude Code always includes it in the PostToolUse
         stdin payload (the same payload this hook reads tool_name from).
      2. stem of payload["transcript_path"] — the transcript filename IS the UUID.
      3. CLAUDE_CODE_SESSION_ID env var — last resort; it is unset in many session
         contexts, which left ~68% of records with an empty uuid (the original bug).
    """
    sid = payload.get("session_id")
    if sid:
        return str(sid)
    tp = payload.get("transcript_path")
    if tp:
        return Path(str(tp)).stem
    return os.environ.get("CLAUDE_CODE_SESSION_ID", "")


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
    global _BOOTSTRAP_STDERR_LOGGED
    # Bootstrap guard: if .git/ doesn't exist we can't rate-limit or write to the
    # error log. Emit one-shot to stderr to surface the problem, then return.
    if not _ERR_STATE_PATH.parent.exists():
        if not _BOOTSTRAP_STDERR_LOGGED:
            _BOOTSTRAP_STDERR_LOGGED = True
            print(f"[bootstrap: {msg}]", file=sys.stderr)
        return
    try:
        now = time.time()
        count, window_start = 0, 0.0
        state_ok = False
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
                state_ok = True
        except Exception:
            pass
        if not state_ok:
            # State file I/O failed (disk full, flock exhausted, bad permissions).
            # Rate-limit state is unknowable; write one-shot to stderr instead of
            # falling through to _ERR_PATH, which would bypass the cap entirely.
            if not _BOOTSTRAP_STDERR_LOGGED:
                _BOOTSTRAP_STDERR_LOGGED = True
                print(f"[rate-limit-state-error: {msg}]", file=sys.stderr)
            return
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

    workspace, sessions_md = _active_workspace_and_sessions_md()

    record = {
        "ts": time.time(),
        "tool": tool_name,
        "path": _extract_path(tool_name, tool_input),
        "session": _session_from_sessions_md(sessions_md),
        "workspace": workspace,
        # Live join key to the native JSONL transcript (filename == this UUID).
        # Enables an on-demand join for richer per-call data (tokens, full I/O)
        # without a parallel logger — see the deferred join ticket. Sourced from the
        # stdin payload (session_id / transcript_path), which is reliably present
        # unlike the env var (T156).
        "claude_session_uuid": _session_uuid(payload),
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
