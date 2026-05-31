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


class TestFailClosedDifferentiation:
    """T142: a missing *confidentiality-enforcing* hook script must fail closed
    (stderr + exit 2); every other hook still fails open (exit 0).

    Rationale (see T142): the original Opus suggestion named three "enforcement"
    hooks, but a matcher-by-matcher deadlock analysis shows a fail-closed *default*
    deadlocks via check_ticket_acs (matcher Edit|Write|Bash → blocks all recovery
    surfaces). So the design is default fail-OPEN with an explicit fail-CLOSED list
    of exactly one hook: check_cross_layer_writes (Inv 2/4 enforcer, Edit|Write-only
    → Bash survives as a `git checkout` recovery surface).
    """

    def _wrapper_in_empty_dir(self, tmp_path: Path) -> Path:
        """Copy run_hook.sh into a dir with NO hook scripts, so every <name>.py
        resolves as missing. Lets us drive the script-not-found branch by name."""
        import shutil

        wrapper = tmp_path / "run_hook.sh"
        shutil.copyfile(WRAPPER, wrapper)
        return wrapper

    def _run_missing(self, tmp_path: Path, name: str) -> subprocess.CompletedProcess:
        wrapper = self._wrapper_in_empty_dir(tmp_path)
        return subprocess.run(
            ["bash", str(wrapper), name],
            input="{}",
            capture_output=True,
            text=True,
            cwd="/tmp",
        )

    def test_missing_confidentiality_hook_fails_closed(self, tmp_path):
        result = self._run_missing(tmp_path, "check_cross_layer_writes")
        assert result.returncode == 2, (result.returncode, result.stderr)
        assert result.stderr.strip(), "fail-closed must emit a visible stderr warning"
        assert "check_cross_layer_writes" in result.stderr

    def test_missing_process_hook_fails_open_no_deadlock(self, tmp_path):
        # check_ticket_acs matches Edit|Write|Bash; fail-closed here would block
        # every recovery surface. It MUST stay fail-open.
        result = self._run_missing(tmp_path, "check_ticket_acs")
        assert result.returncode == 0, (result.returncode, result.stderr)

    def test_missing_fix_commit_hook_fails_open(self, tmp_path):
        result = self._run_missing(tmp_path, "check_fix_commit_has_code")
        assert result.returncode == 0, (result.returncode, result.stderr)

    def test_missing_telemetry_hook_fails_open(self, tmp_path):
        result = self._run_missing(tmp_path, "log_tool_usage")
        assert result.returncode == 0, (result.returncode, result.stderr)

    def test_fail_closed_set_is_named_in_wrapper(self):
        # Guard against silent scope creep: the FAIL_CLOSED declaration is exactly
        # {check_cross_layer_writes}. A future confidentiality enforcer must be
        # added here deliberately (the accepted residual tradeoff in T142). Inspect
        # the declaration line, not the whole file — the process hooks are named in
        # the rationale comment, which is fine.
        text = WRAPPER.read_text(encoding="utf-8")
        decl = [ln for ln in text.splitlines() if ln.strip().startswith("FAIL_CLOSED=")]
        assert len(decl) == 1, f"expected one FAIL_CLOSED= line, got {decl}"
        line = decl[0]
        assert "check_cross_layer_writes" in line
        assert "check_ticket_acs" not in line
        assert "check_fix_commit_has_code" not in line