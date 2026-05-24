"""
tests/test_workflow_orchestrator.py

Integration tests for the Python-orchestrated background agent workflow.
All tests use a temp git repo fixture — no real repo state is touched.

Shim scripts act as fake claude CLI binaries, writing specific files and
exiting to simulate different agent behaviours.
"""
from __future__ import annotations

import json
import subprocess
import textwrap
import threading
import time
from pathlib import Path

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def git_repo(tmp_path):
    """Minimal temp git repo with the directory structure the orchestrator expects."""
    repo = tmp_path / "repo"
    repo.mkdir()

    sub = subprocess.run
    cap = dict(check=True, capture_output=True)

    sub(["git", "init", str(repo)], **cap)
    sub(["git", "config", "user.email", "test@test.com"], cwd=repo, **cap)
    sub(["git", "config", "user.name", "Test"], cwd=repo, **cap)
    sub(["git", "config", "commit.gpgsign", "false"], cwd=repo, **cap)

    # Directory structure
    for d in [
        "core", "execution", "data", "strategies",
        "infra", "scripts/workflows/lib",
        "docs/tickets/open",
    ]:
        (repo / d).mkdir(parents=True, exist_ok=True)

    # Minimal orchestrator files for hash guard
    (repo / "scripts/workflows/__init__.py").write_text("")
    (repo / "scripts/workflows/lib/__init__.py").write_text("")
    (repo / "scripts/workflows/implement_ticket.py").write_text("# orchestrator\n")

    # Governance files
    (repo / "docs/architecture_invariants.md").write_text("# Invariants\nTest only.\n")
    (repo / "config.yaml").write_text("mode: paper\n")
    (repo / "infra/audit_log.py").write_text("# audit log\n")

    # Test ticket
    (repo / "docs/tickets/open/T001-test-ticket.md").write_text(
        "---\ntitle: Test Ticket\nphase: 4\n---\n# T001 Test\n"
        "## Acceptance Criteria\n- [x] Done\n"
    )

    sub(["git", "add", "-A"], cwd=repo, **cap)
    sub(["git", "commit", "-m", "initial commit"], cwd=repo, **cap)
    return repo


def _shim(tmp_path: Path, name: str, body: str) -> Path:
    """Write a Python shim as a fake claude CLI binary."""
    script = tmp_path / name
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import os, pathlib, subprocess, sys, time\n"
        + textwrap.dedent(body)
    )
    script.chmod(0o755)
    return script


def _run(git_repo, shim_path, test_cmd=None, analysis_cmd=None, timeout_s=8, watcher_class=None):
    from scripts.workflows import implement_ticket
    return implement_ticket.run_workflow(
        "T001",
        root=git_repo,
        timeout_s=timeout_s,
        cli_path=str(shim_path),
        test_cmd=test_cmd or ["python", "-c", ""],
        analysis_cmd=analysis_cmd or ["python", "-c", ""],
        watcher_class=watcher_class,
    )


def _result(git_repo) -> dict:
    return json.loads((git_repo / ".git" / "workflow_result.json").read_text())


def _audit(git_repo) -> str:
    p = git_repo / ".git" / "workflow_audit.log"
    return p.read_text() if p.exists() else ""


def _is_clean(git_repo) -> bool:
    r = subprocess.run(
        ["git", "status", "--porcelain"], cwd=git_repo, capture_output=True, text=True
    )
    return r.stdout.strip() == ""


def _head_sha(git_repo) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=git_repo, text=True
    ).strip()


# ── test 1 — denylist violation ───────────────────────────────────────────────

def test_denylist_violation_kills_agent_and_reverts(git_repo, tmp_path):
    """Agent writes to config.yaml (denied) and sleeps — watcher kills it, reverts."""
    shim = _shim(tmp_path, "shim1.py", """
pathlib.Path("config.yaml").write_text("evil: true\\n")
time.sleep(60)
""")
    snap = _head_sha(git_repo)
    outcome = _run(git_repo, shim)

    assert outcome == "KILLED_DENYLIST_VIOLATION"
    assert _result(git_repo)["outcome"] == "KILLED_DENYLIST_VIOLATION"
    assert _is_clean(git_repo)
    assert _head_sha(git_repo) == snap
    assert "REVERTED" in _audit(git_repo)
    # config.yaml must be back to original content
    assert "evil" not in (git_repo / "config.yaml").read_text()


# ── test 2 — orchestrator hash change ─────────────────────────────────────────

def test_orchestrator_hash_change_reverts(git_repo, tmp_path):
    """Agent adds a new file to scripts/workflows/ and exits — hash guard catches it."""
    shim = _shim(tmp_path, "shim2.py", """
pathlib.Path("scripts/workflows/lib/evil_module.py").write_text("# injected\\n")
# exit immediately so watcher doesn't fire (scripts/workflows/ not in DENIED_PATHS)
""")
    snap = _head_sha(git_repo)
    outcome = _run(git_repo, shim)

    assert outcome == "ORCHESTRATOR_MODIFIED"
    assert _is_clean(git_repo)
    assert _head_sha(git_repo) == snap
    assert not (git_repo / "scripts/workflows/lib/evil_module.py").exists()


# ── test 3 — unauthorized commit ──────────────────────────────────────────────

def test_unauthorized_commit_detected_and_reverted(git_repo, tmp_path):
    """Agent runs git commit — detected and reverted to snapshot SHA."""
    shim = _shim(tmp_path, "shim3.py", """
pathlib.Path("data/agent_file.py").write_text("# agent\\n")
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "agent commit"], check=True)
""")
    snap = _head_sha(git_repo)
    outcome = _run(git_repo, shim)

    assert outcome == "UNAUTHORIZED_COMMIT"
    assert _is_clean(git_repo)
    assert _head_sha(git_repo) == snap  # reverted to snapshot


# ── test 4 — test failure ─────────────────────────────────────────────────────

def test_test_failure_reverts(git_repo, tmp_path):
    """Agent edits a file cleanly; tests fail — reverted with test output."""
    shim = _shim(tmp_path, "shim4.py", """
pathlib.Path("data/market_data.py").write_text("# agent edit\\n")
""")
    snap = _head_sha(git_repo)
    outcome = _run(
        git_repo, shim,
        test_cmd=["python", "-c", "import sys; sys.exit(1)"],
    )

    assert outcome == "TEST_FAILED"
    assert _is_clean(git_repo)
    assert _head_sha(git_repo) == snap
    assert not (git_repo / "data/market_data.py").exists()


# ── test 5 — clean implementation → AWAITING_REVIEW ─────────────────────────

def test_clean_implementation_reaches_awaiting_review(git_repo, tmp_path):
    """Agent edits data/market_data.py; tests and analysis pass — AWAITING_REVIEW."""
    shim = _shim(tmp_path, "shim5.py", """
pathlib.Path("data/market_data.py").write_text("# clean edit\\n")
""")
    outcome = _run(git_repo, shim)

    assert outcome == "AWAITING_REVIEW"
    result = _result(git_repo)
    assert result["outcome"] == "AWAITING_REVIEW"
    assert "market_data.py" in result["diff_preview"]
    # Working tree is dirty (changes preserved for review)
    assert (git_repo / "data/market_data.py").exists()


# ── test 6 — core touch → AWAITING_ARCHITECTURE_REVIEW ───────────────────────

def test_core_touch_escalates_to_arch_review(git_repo, tmp_path):
    """Agent edits core/risk_engine.py; tests pass — escalated to architecture review."""
    shim = _shim(tmp_path, "shim6.py", """
pathlib.Path("core/risk_engine.py").write_text("# core edit\\n")
""")
    outcome = _run(git_repo, shim)

    assert outcome == "AWAITING_ARCHITECTURE_REVIEW"
    result = _result(git_repo)
    assert "risk_engine" in result["diff_preview"]


# ── test 7 — double denylist violation → single revert ───────────────────────

def test_double_denylist_violation_single_revert(git_repo, tmp_path):
    """Agent writes two denied files simultaneously — exactly one revert, clean tree."""
    shim = _shim(tmp_path, "shim7.py", """
pathlib.Path("config.yaml").write_text("evil: true\\n")
pathlib.Path("docs/architecture_invariants.md").write_text("# erased\\n")
time.sleep(60)
""")
    snap = _head_sha(git_repo)
    outcome = _run(git_repo, shim)

    assert outcome == "KILLED_DENYLIST_VIOLATION"
    assert _is_clean(git_repo)
    assert _head_sha(git_repo) == snap
    # Both files must be restored
    assert "evil" not in (git_repo / "config.yaml").read_text()
    assert "erased" not in (git_repo / "docs/architecture_invariants.md").read_text()


# ── test 8 — watcher thread crash ────────────────────────────────────────────

def test_watcher_thread_crash_kills_agent_and_reverts(git_repo, tmp_path):
    """Watcher thread raises immediately — agent terminated, working tree clean."""
    from scripts.workflows.lib.watcher import DenylistWatcher

    class CrashingWatcher(DenylistWatcher):
        def run(self) -> None:
            self._exception = RuntimeError("simulated watcher crash")
            self._stop_event.set()

    # Shim that sleeps (would run indefinitely without watcher kill)
    shim = _shim(tmp_path, "shim8.py", "time.sleep(60)\n")
    snap = _head_sha(git_repo)
    outcome = _run(git_repo, shim, watcher_class=CrashingWatcher)

    assert outcome == "WATCHER_CRASHED"
    assert _is_clean(git_repo)
    assert _head_sha(git_repo) == snap


# ── test 9 — timeout ─────────────────────────────────────────────────────────

def test_agent_timeout_reverts(git_repo, tmp_path):
    """Agent exceeds timeout budget — terminated and reverted."""
    shim = _shim(tmp_path, "shim9.py", "time.sleep(300)\n")
    snap = _head_sha(git_repo)
    outcome = _run(git_repo, shim, timeout_s=3)

    assert outcome == "TIMEOUT"
    assert _is_clean(git_repo)
    assert _head_sha(git_repo) == snap


# ── test 10 — concurrent invocation blocked ───────────────────────────────────

def test_concurrent_invocation_blocked(git_repo, tmp_path):
    """Lock file already present — workflow returns ALREADY_RUNNING immediately."""
    import os
    lock = git_repo / ".git" / "workflow.lock"
    lock.write_text(str(os.getpid()))  # own PID — process is alive

    shim = _shim(tmp_path, "shim10.py", "")  # never reached
    outcome = _run(git_repo, shim)

    assert outcome == "ALREADY_RUNNING"
    assert _result(git_repo)["outcome"] == "ALREADY_RUNNING"
    lock.unlink()  # cleanup


# ── test 11 — touches_safety_critical unit test ───────────────────────────────

def test_touches_safety_critical_without_commit(git_repo):
    """touches_safety_critical() sees working-tree changes without any commit (R1 fix)."""
    from scripts.workflows.lib.git_ops import snapshot, touches_safety_critical

    snap = snapshot(git_repo)
    (git_repo / "core" / "risk_engine.py").write_text("# modified\n")

    assert touches_safety_critical(snap, git_repo) is True

    # Confirm no new commit exists
    log = subprocess.check_output(
        ["git", "log", "--oneline"], cwd=git_repo, text=True
    ).strip().splitlines()
    assert len(log) == 1  # only the initial commit


# ── test 12 — credit exhaustion ───────────────────────────────────────────────

def test_credit_exhaustion_surfaces_named_failure(git_repo, tmp_path):
    """Agent exits non-zero with credit error in stderr — CREDIT_EXHAUSTED, no retry."""
    shim = _shim(tmp_path, "shim12.py", """
import sys
print("Error: insufficient credits - you have exceeded your usage limit", file=sys.stderr)
sys.exit(1)
""")
    outcome = _run(git_repo, shim)

    assert outcome == "CREDIT_EXHAUSTED"
    result = _result(git_repo)
    assert result["outcome"] == "CREDIT_EXHAUSTED"
    assert _is_clean(git_repo)


# ── test 13 — agent binary unavailable ───────────────────────────────────────

def test_agent_unavailable_surfaces_named_failure(git_repo, tmp_path):
    """CLAUDE_CLI_PATH points to a nonexistent binary — AGENT_UNAVAILABLE immediately."""
    nonexistent = str(tmp_path / "no_such_binary")
    outcome = _run(git_repo, nonexistent)

    assert outcome == "AGENT_UNAVAILABLE"
    result = _result(git_repo)
    assert result["outcome"] == "AGENT_UNAVAILABLE"
    assert _is_clean(git_repo)


# ── test 14 — detect_credit_exhaustion patterns ───────────────────────────────

def test_detect_credit_exhaustion_matches_known_patterns():
    """detect_credit_exhaustion returns True for each registered pattern."""
    from scripts.workflows.lib.agent_runner import detect_credit_exhaustion

    positive_cases = [
        "Error: credit balance is zero",
        "you have insufficient credits remaining",
        "exceeded your usage limit for this period",
        "please update your billing information",
        "quota exceeded for this account",
        "rate limit reached",
    ]
    for msg in positive_cases:
        assert detect_credit_exhaustion(msg), f"should match: {msg!r}"
        assert detect_credit_exhaustion(msg.upper()), f"should match uppercase: {msg!r}"

    negative_cases = [
        "",
        "command not found: claude",
        "connection refused",
        "no such file or directory",
    ]
    for msg in negative_cases:
        assert not detect_credit_exhaustion(msg), f"should not match: {msg!r}"


# ── test 15 — dirty working tree blocked ──────────────────────────────────────

def test_dirty_working_tree_refused(git_repo, tmp_path):
    """Uncommitted changes in working tree → DIRTY_WORKING_TREE, no agent spawned."""
    # Modify a tracked file (config.yaml is committed in the fixture)
    (git_repo / "config.yaml").write_text("mode: dirty\n")

    shim = _shim(tmp_path, "shim15.py", "")  # never reached
    outcome = _run(git_repo, shim)

    assert outcome == "DIRTY_WORKING_TREE"
    result = _result(git_repo)
    assert result["outcome"] == "DIRTY_WORKING_TREE"
    assert "config.yaml" in result["details"]
