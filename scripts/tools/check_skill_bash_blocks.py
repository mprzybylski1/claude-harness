"""
scripts/tools/check_skill_bash_blocks.py
Extract every fenced ```bash ... ``` block from a SKILL.md file and run `bash -n`
(syntax check) on each. Exits non-zero on the first failure.

Usage:
    python scripts/tools/check_skill_bash_blocks.py [path/to/SKILL.md]

    If no path is given, defaults to .claude/skills/session-close/SKILL.md.

Purpose: prevent the class of regression introduced in S46 where a backslash inside
a comment silently broke line continuation in the `git add` block.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_SKILL = ROOT / ".claude" / "skills" / "session-close" / "SKILL.md"

_BASH_FENCE_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)


def main() -> None:
    if len(sys.argv) >= 2:
        skill_path = Path(sys.argv[1])
        if not skill_path.is_absolute():
            skill_path = ROOT / skill_path
    else:
        skill_path = _DEFAULT_SKILL

    if not skill_path.exists():
        print(f"SKIP  {skill_path} not found")
        return

    text = skill_path.read_text()
    blocks = _BASH_FENCE_RE.findall(text)

    if not blocks:
        print("No fenced bash blocks found — nothing to check.")
        return

    failed = 0
    for i, block in enumerate(blocks, start=1):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as tmp:
            tmp.write(block)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["bash", "-n", tmp_path],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"FAIL bash block {i}:")
                print(f"  {result.stderr.strip()}")
                print("Block content:")
                for line in block.splitlines():
                    print(f"  {line}")
                failed += 1
            else:
                print(f"  bash block {i}: OK")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    if failed:
        sys.exit(f"{failed} bash block(s) failed syntax check.")
    else:
        print(f"All {len(blocks)} bash block(s) passed.")


if __name__ == "__main__":
    main()
