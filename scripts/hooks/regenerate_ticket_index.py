#!/usr/bin/env python3
"""
PostToolUse hook: regenerate docs/tickets/INDEX.md after any ticket file changes.
Also validates closed: attribution when writing to docs/tickets/closed/.

Fires on Edit/Write. Checks whether the affected file is under docs/tickets/
or under workspaces/<slug>/internal/tickets/.
If yes:
  1. Regenerates INDEX.md (silent on success, exits 1 on generator failure).
  2. If the file is under a closed/ directory, parses its closed: frontmatter field
     and warns if it doesn't start with the current session ID (T016 enforcement).

This makes INDEX.md impossible to be stale — it updates immediately whenever
any ticket file is created, modified, or moved.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
from workspace_config import active_workspace_dir, workspaces_base, load_workspace, internal_dir as _internal_dir


def get_current_session(project_root: str, sessions_file: str | None = None) -> str | None:
    """Get current session ID from current_session.py."""
    script = os.path.join(project_root, "scripts", "tools", "current_session.py")
    if not os.path.exists(script):
        return None
    cmd = [sys.executable, script]
    if sessions_file:
        cmd += ["--sessions", sessions_file]
    r = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.strip()
    return None


# Module-level cache of docs_path ticket roots → workspace dir. Populated once per
# process on first slow-path call. Eliminates O(edits × workspaces) YAML loads (T043).
_docs_path_cache: dict[str, Path] | None = None


def _get_docs_path_map() -> dict[str, Path]:
    """Return {str(docs/tickets path): ws_dir} built once per process."""
    global _docs_path_cache
    if _docs_path_cache is not None:
        return _docs_path_cache
    result: dict[str, Path] = {}
    try:
        ws_base = workspaces_base()
        if ws_base.exists():
            for ws_dir in sorted(ws_base.iterdir()):
                if not ws_dir.is_dir() or ws_dir.name == "archive":
                    continue
                cfg = load_workspace(ws_dir)
                if not cfg or not cfg.get("docs_path"):
                    continue
                docs = _internal_dir(ws_dir, cfg)
                result[str(docs / "tickets")] = ws_dir
    except Exception:
        pass
    _docs_path_cache = result
    return result


def _detect_workspace_from_path(file_path: str) -> Path | None:
    """Return workspace dir if file_path is under any workspace's internal/tickets/."""
    try:
        ws_base = workspaces_base()
        resolved = Path(file_path).resolve()

        # Fast path: standard harness-local layout (workspaces/<slug>/internal/tickets/)
        try:
            rel = resolved.relative_to(ws_base)
            parts = rel.parts
            if len(parts) >= 3 and parts[1] == "internal" and parts[2] == "tickets":
                return ws_base / parts[0]
        except ValueError:
            pass

        # Slow path: file may be under a custom docs_path in a workspace repo.
        # Uses a module-level cache so YAML is loaded once per process (T043).
        docs_map = _get_docs_path_map()
        resolved_str = str(resolved)
        for tickets_root, ws_dir in docs_map.items():
            if resolved_str.startswith(tickets_root + os.sep) or resolved_str == tickets_root:
                return ws_dir
    except Exception:
        pass
    return None


def _docs_for_workspace(ws_dir: Path) -> Path:
    """Return the docs root for a workspace dir."""
    cfg = load_workspace(ws_dir)
    return _internal_dir(ws_dir, cfg)


def _detect_index_path(file_path: str, project_root: str) -> str:
    """Return the INDEX.md path to regenerate based on the written file's location."""
    ws_dir = _detect_workspace_from_path(file_path)
    if ws_dir:
        return str(_docs_for_workspace(ws_dir) / "tickets" / "INDEX.md")
    return str(Path(project_root) / "docs" / "tickets" / "INDEX.md")


def _detect_open_dir(file_path: str, project_root: str) -> str:
    """Return the open tickets directory based on the written file's location."""
    ws_dir = _detect_workspace_from_path(file_path)
    if ws_dir:
        return str(_docs_for_workspace(ws_dir) / "tickets" / "open")
    return str(Path(project_root) / "docs" / "tickets" / "open")


def _detect_sessions_file(file_path: str, project_root: str) -> str:
    """Return the sessions.md path based on the written file's location."""
    ws_dir = _detect_workspace_from_path(file_path)
    if ws_dir:
        return str(_docs_for_workspace(ws_dir) / "sessions.md")
    return str(Path(project_root) / "docs" / "sessions.md")


def _is_closed_ticket(file_path: str) -> bool:
    """Return True if the file is under a tickets/closed/ directory."""
    # Lexical parts only — Path.resolve() follows symlinks and can diverge across Python
    # versions; path-component check does not require the file to exist (S9 #9).
    parts = Path(file_path).parts
    for i in range(1, len(parts)):
        if parts[i - 1] == "tickets" and parts[i] == "closed":
            return True
    return False


def check_closed_attribution(file_path: str, project_root: str) -> None:
    """Warn if closed: field doesn't match current session (T016 enforcement)."""
    if not _is_closed_ticket(file_path):
        return
    if not os.path.exists(file_path):
        return

    with open(file_path) as f:
        content = f.read()

    # Extract closed: field from frontmatter
    match = re.search(r"^closed:\s*(.+)$", content, re.MULTILINE)
    if not match:
        return  # no closed: field yet — skip
    closed_value = match.group(1).strip()
    if not closed_value:
        return  # empty — skip

    sessions_file = _detect_sessions_file(file_path, project_root)
    current = get_current_session(project_root, sessions_file)
    if current and not closed_value.startswith(current):
        print(
            f"WARNING (T016): {os.path.basename(file_path)} has closed: '{closed_value}' "
            f"but current session is {current}. "
            f"Update the closed: field to start with {current}.",
            file=sys.stderr,
        )


def _is_ticket_file(file_path: str) -> bool:
    """Return True if file_path is under any tickets/ directory."""
    if "docs/tickets/" in file_path or "/internal/tickets/" in file_path:
        return True
    # Support custom docs_path — check workspace scan only when "/tickets/" appears
    if "/tickets/" not in file_path:
        return False
    return _detect_workspace_from_path(file_path) is not None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    # Extract the file path from the tool input
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Only fire for ticket files
    if not _is_ticket_file(file_path):
        sys.exit(0)

    # Find project root (settings.json is at .claude/settings.json relative to root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))

    # Attribution check (T016) for closed/ writes
    check_closed_attribution(file_path, project_root)

    # Determine paths based on the written file's location
    index_path = _detect_index_path(file_path, project_root)
    open_dir = _detect_open_dir(file_path, project_root)
    sessions_file = _detect_sessions_file(file_path, project_root)

    # Regenerate INDEX.md
    generator = os.path.join(project_root, "scripts", "tools", "generate_ticket_index.py")
    result = subprocess.run(
        [
            sys.executable, generator,
            "--tickets-dir", open_dir,
            "--output", index_path,
            "--sessions-file", sessions_file,
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"ERROR: generate_ticket_index.py failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Silent success — INDEX.md updated, no noise to the agent
    sys.exit(0)


if __name__ == "__main__":
    main()
