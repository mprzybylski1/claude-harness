import json
import re
from pathlib import Path


def test_hook_commands_have_no_hardcoded_paths():
    settings = json.loads((Path(__file__).parent.parent / ".claude/settings.json").read_text())
    for hook_group in settings.get("hooks", {}).values():
        for entry in hook_group:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                assert not re.search(r"/(home|Users)/", cmd), (
                    f"Hardcoded path in hook command: {cmd}"
                )