#!/usr/bin/env python3
"""
PostToolUse hook: run bash -n syntax check on any SKILL.md file that was just written.

Fires on Edit/Write. If the modified file is under .claude/skills/ and ends with .md,
runs check_skill_bash_blocks.py on that specific file.

Exits 0 silently on pass or skip (non-skill file).
Exits 1 with error output if any bash block fails — Claude Code surfaces this immediately.

This catches the S46 class of regression (broken backslash in git add block) the moment
a skill file is edited, rather than waiting until the next Opus context generation.
"""
import json
import os
import subprocess
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Only fire for skill markdown files
    if ".claude/skills/" not in file_path or not file_path.endswith(".md"):
        sys.exit(0)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    checker = os.path.join(project_root, "scripts", "tools", "check_skill_bash_blocks.py")

    result = subprocess.run(
        [sys.executable, checker, file_path],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"ERROR: bash block syntax check failed for {os.path.basename(file_path)}:",
              file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        sys.exit(1)

    # Silent success
    sys.exit(0)


if __name__ == "__main__":
    main()
