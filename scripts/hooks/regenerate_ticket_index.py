#!/usr/bin/env python3
"""
PostToolUse hook: regenerate docs/tickets/INDEX.md after any ticket file changes.
Also validates closed: attribution when writing to docs/tickets/closed/.

Fires on Edit/Write. Checks whether the affected file is under docs/tickets/.
If yes:
  1. Regenerates INDEX.md (silent on success, exits 1 on generator failure).
  2. If the file is under docs/tickets/closed/, parses its closed: frontmatter field
     and warns if it doesn't start with the current session ID (T016 enforcement).

This makes INDEX.md impossible to be stale — it updates immediately whenever
any ticket file is created, modified, or moved.
"""
import json
import os
import re
import subprocess
import sys


def get_current_session(project_root: str) -> str | None:
    """Get current session ID from current_session.py."""
    script = os.path.join(project_root, "scripts", "tools", "current_session.py")
    if not os.path.exists(script):
        return None
    r = subprocess.run([sys.executable, script], cwd=project_root,
                       capture_output=True, text=True)
    if r.returncode == 0:
        return r.stdout.strip()
    return None


def check_closed_attribution(file_path: str, project_root: str) -> None:
    """Warn if closed: field doesn't match current session (T016 enforcement)."""
    if "docs/tickets/closed/" not in file_path:
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

    current = get_current_session(project_root)
    if current and not closed_value.startswith(current):
        print(
            f"WARNING (T016): {os.path.basename(file_path)} has closed: '{closed_value}' "
            f"but current session is {current}. "
            f"Update the closed: field to start with {current}.",
            file=sys.stderr,
        )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    # Extract the file path from the tool input
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Only fire for ticket files
    if "docs/tickets/" not in file_path:
        sys.exit(0)

    # Find project root (settings.json is at .claude/settings.json relative to root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))

    # Attribution check (T016) for closed/ writes
    check_closed_attribution(file_path, project_root)

    # Regenerate INDEX.md
    generator = os.path.join(project_root, "scripts", "tools", "generate_ticket_index.py")
    result = subprocess.run(
        [sys.executable, generator],
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
