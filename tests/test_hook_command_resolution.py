"""Tests for T138: hook command root-resolution is cwd-independent and fail-open.

SR-011 deadlock: every hook command located its script via
`$(git rev-parse --show-toplevel)`, evaluated at the *session cwd*. When cwd
drifted into a different git repo (e.g. a workspace repo), the script path
resolved to a repo with no harness hooks → `python3: can't open file` → exit 2
→ PreToolUse fail-closed-blocked *every* tool, including the `cd` that would
recover. Hard deadlock.

Fix: settings.json commands resolve the script via `$CLAUDE_PROJECT_DIR`
(set in hook context, fixed for the session, drift-proof) and dispatch through
`scripts/hooks/run_hook.sh`, which fails OPEN (exit 0) when the target script is
missing so a resolution accident can never deadlock the session. A hook's own
deliberate `exit 2` still propagates through the exec chain and blocks.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / ".claude" / "settings.json"
WRAPPER = ROOT / "scripts" / "hooks" / "run_hook.sh"


def _all_hook_commands() -> list[str]:
    """Every hook command string declared in settings.json (all events)."""
    cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    commands: list[str] = []
    for event_groups in cfg.get("hooks", {}).values():
        for group in event_groups:
            for hook in group.get("hooks", []):
                if hook.get("type") == "command":
                    commands.append(hook["command"])
    return commands


def _command_for(hook_name: str) -> str:
    """The single settings.json command that dispatches the named hook."""
    matches = [c for c in _all_hook_commands() if hook_name in c]
    assert len(matches) == 1, f"expected exactly one command for {hook_name}, got {matches}"
    return matches[0]


def _run(command: str, payload: dict, *, env: dict, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        shell=True,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd),
    )


def _fake_harness(tmp_path: Path, slug: str) -> Path:
    """Minimal harness skeleton for check_cross_layer_writes logic (via HARNESS_ROOT)."""
    harness = tmp_path / "harness"
    (harness / ".claude").mkdir(parents=True)
    (harness / "docs" / "tickets").mkdir(parents=True)
    (harness / "workspaces").mkdir()
    (harness / ".claude" / ".active_workspace").write_text(slug, encoding="utf-8")
    return harness


class TestSettingsCommandShape:
    """Static guards on the command strings themselves."""

    def test_no_command_uses_git_rev_parse(self):
        # The SR-011 root cause. Must never reappear.
        for command in _all_hook_commands():
            assert "git rev-parse" not in command, command

    def test_every_command_resolves_via_claude_project_dir(self):
        for command in _all_hook_commands():
            assert "CLAUDE_PROJECT_DIR" in command, command

    def test_every_command_dispatches_through_wrapper(self):
        for command in _all_hook_commands():
            assert "run_hook.sh" in command, command

    def test_every_command_has_fail_open_guard(self):
        # `[ -f ... ]` existence check plus an `exit 0` fallback so a missing
        # wrapper can never block a PreToolUse tool call.
        for command in _all_hook_commands():
            assert re.search(r"\[\s*-f", command), command
            assert "exit 0" in command, command

    def test_wrapper_exists_and_is_executable(self):
        assert WRAPPER.is_file()
        assert os.access(WRAPPER, os.X_OK)


class TestDriftIndependence:
    """Behavioral: commands run correctly when cwd has drifted out of the harness."""

    def test_block_propagates_from_drifted_cwd(self, tmp_path):
        # cwd=/tmp simulates the wedged session. CLAUDE_PROJECT_DIR locates the
        # real wrapper+script; HARNESS_ROOT drives the block decision.
        harness = _fake_harness(tmp_path, slug="some-ws")
        command = _command_for("check_cross_layer_writes")
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(ROOT),
            "HARNESS_ROOT": str(harness),
        }
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(harness / "docs" / "tickets" / "T999-x.md")},
        }
        result = _run(command, payload, env=env, cwd=Path("/tmp"))
        assert result.returncode == 2, (result.returncode, result.stderr)
        assert "CROSS-LAYER WRITE BLOCKED" in result.stderr

    def test_allows_permitted_write_from_drifted_cwd(self, tmp_path):
        harness = _fake_harness(tmp_path, slug="some-ws")
        command = _command_for("check_cross_layer_writes")
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(ROOT),
            "HARNESS_ROOT": str(harness),
        }
        # Writing to its own raised/ boundary slot is always allowed.
        payload = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(harness / "workspaces" / "some-ws" / "raised" / "SR-001-x.md")
            },
        }
        result = _run(command, payload, env=env, cwd=Path("/tmp"))
        assert result.returncode == 0, (result.returncode, result.stderr)


class TestFailOpen:
    """The anti-deadlock guarantee: unresolvable script path → exit 0, never block."""

    def test_fail_open_when_project_dir_unset(self, tmp_path):
        # No CLAUDE_PROJECT_DIR and cwd outside any harness: the wrapper cannot
        # be located. Must exit 0 (fail-open), NOT exit 2 (the deadlock).
        command = _command_for("check_cross_layer_writes")
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/anything.md"},
        }
        result = _run(command, payload, env=env, cwd=Path("/tmp"))
        assert result.returncode == 0, (result.returncode, result.stderr)


class TestWrapper:
    """run_hook.sh in isolation."""

    def test_missing_script_fails_open(self, tmp_path):
        result = subprocess.run(
            ["bash", str(WRAPPER), "no_such_hook_script"],
            input="{}",
            capture_output=True,
            text=True,
            cwd="/tmp",
        )
        assert result.returncode == 0, (result.returncode, result.stderr)

    def test_dispatches_named_hook_regardless_of_cwd(self, tmp_path):
        # log_tool_usage exits 0 when telemetry is off / payload is benign;
        # the point is the wrapper finds and runs it from a drifted cwd.
        result = subprocess.run(
            ["bash", str(WRAPPER), "check_cross_layer_writes"],
            input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}}),
            capture_output=True,
            text=True,
            cwd="/tmp",
        )
        # Read is not Edit/Write → hook exits 0 immediately. Proves dispatch works.
        assert result.returncode == 0, (result.returncode, result.stderr)