"""
scripts/workflows/implement_ticket.py

Background orchestrator for autonomous ticket implementation. Wires together the
scripts/workflows/lib primitives into one state machine:

    snapshot → spawn agent → watch denied paths → post-checks
    (credit / hash-guard / unauthorized-commit / tests / static analysis)
    → route to AWAITING_REVIEW or AWAITING_ARCHITECTURE_REVIEW,
    reverting to the snapshot on any failure path.

Invoked by the implement-background skill:

    python -m scripts.workflows.implement_ticket T###

`run_workflow()` is the importable entry point exercised by
tests/test_workflow_orchestrator.py. The working tree is ALWAYS clean on any
non-AWAITING_* outcome (revert = `git reset --hard` + `git clean -fd`).

Project-agnostic by design: the denied/safety-critical path lists and the agent
prompt live in lib/watcher.py, lib/git_ops.py, and lib/prompt_builder.py — this
module only sequences the checks.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from .lib import agent_runner, git_ops, hash_guard
from .lib.agent_runner import DEFAULT_TIMEOUT_S
from .lib.notifier import write_audit, write_result
from .lib.prompt_builder import build_prompt
from .lib.watcher import DenylistWatcher

# How often the orchestrator polls the agent/watcher state. Distinct from the
# watcher's own git-status poll interval (watcher.POLL_INTERVAL_S).
_POLL_S = 0.05


# ── lock / preconditions ──────────────────────────────────────────────────────

def _lock_path(root: Path) -> Path:
    return root / ".git" / "workflow.lock"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    except OSError:
        return False
    return True


def _already_running(root: Path) -> bool:
    lock = _lock_path(root)
    if not lock.exists():
        return False
    try:
        pid = int(lock.read_text().strip())
    except (ValueError, OSError):
        return False
    return _pid_alive(pid)


def _dirty_files(root: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True
    ).stdout.strip()


# ── agent lifecycle ───────────────────────────────────────────────────────────

def _await_agent(proc: subprocess.Popen, watcher, timeout_s: int) -> str:
    """Block until the agent terminates for one of four reasons.

    Returns: 'DENYLIST' | 'WATCHER_CRASHED' | 'TIMEOUT' | 'DONE'.
    Violation/crash are checked before natural exit so a watcher kill is never
    mis-reported as a clean exit.
    """
    deadline = time.monotonic() + timeout_s
    while True:
        if watcher is not None and watcher.crashed:
            return "WATCHER_CRASHED"
        if watcher is not None and getattr(watcher, "_violation", None):
            return "DENYLIST"
        if proc.poll() is not None:
            return "DONE"
        if time.monotonic() >= deadline:
            return "TIMEOUT"
        time.sleep(_POLL_S)


def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _revert(ticket_id: str, snap: str, root: Path, reason: str) -> None:
    git_ops.revert_to_snapshot(snap, root)
    write_audit(ticket_id, "REVERTED", reason, root=root)


# ── orchestrator ──────────────────────────────────────────────────────────────

def run_workflow(
    ticket_id: str,
    *,
    root: Path,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    cli_path: str | None = None,
    test_cmd: list[str] | None = None,
    analysis_cmd: list[str] | None = None,
    watcher_class=None,
) -> str:
    """Run the implement-ticket state machine. Returns the outcome string and writes
    it (plus a diff preview) to .git/workflow_result.json."""
    root = Path(root)
    watcher_class = watcher_class or DenylistWatcher
    test_cmd = test_cmd or ["python", "-m", "pytest", "tests/", "-x", "-q"]
    analysis_cmd = analysis_cmd or [sys.executable, "-c", ""]

    # Preconditions (no agent spawned, no lock held yet).
    if _already_running(root):
        write_result("ALREADY_RUNNING", "another workflow holds .git/workflow.lock", root=root)
        return "ALREADY_RUNNING"

    dirty = _dirty_files(root)
    if dirty:
        write_result("DIRTY_WORKING_TREE", f"uncommitted changes present:\n{dirty}", root=root)
        return "DIRTY_WORKING_TREE"

    cli = agent_runner._cli_path(cli_path)
    if not cli.exists():
        write_result("AGENT_UNAVAILABLE", f"agent binary not found: {cli}", root=root)
        return "AGENT_UNAVAILABLE"

    lock = _lock_path(root)
    lock.write_text(str(os.getpid()))
    try:
        snap = git_ops.snapshot(root)
        hashes_before = hash_guard.compute(root)
        prompt = build_prompt(ticket_id, root)

        proc = agent_runner.spawn(prompt, timeout_s=timeout_s, cli_path=cli_path, root=root)
        # Drain stderr in a thread so a chatty agent can't block on a full pipe buffer.
        stderr_buf: list[str] = []
        drain = threading.Thread(
            target=lambda: stderr_buf.extend(proc.stderr or []), daemon=True
        )
        drain.start()

        watcher = watcher_class(proc, root)
        watcher.start()

        reason = _await_agent(proc, watcher, timeout_s)

        _terminate(proc)
        violation = watcher.stop() if hasattr(watcher, "stop") else None
        drain.join(timeout=2)
        stderr = "".join(stderr_buf)

        if reason == "DENYLIST":
            _revert(ticket_id, snap, root, f"denylist violation: {violation}")
            write_result("KILLED_DENYLIST_VIOLATION",
                         f"agent wrote to a denied path: {violation}", root=root)
            return "KILLED_DENYLIST_VIOLATION"

        if reason == "WATCHER_CRASHED":
            _revert(ticket_id, snap, root, "watcher thread crashed")
            write_result("WATCHER_CRASHED",
                         "denylist watcher crashed; agent terminated and reverted", root=root)
            return "WATCHER_CRASHED"

        if reason == "TIMEOUT":
            _revert(ticket_id, snap, root, f"timeout after {timeout_s}s")
            write_result("TIMEOUT", f"agent exceeded the {timeout_s}s budget", root=root)
            return "TIMEOUT"

        # reason == "DONE" — agent exited on its own; run post-checks in priority order.
        if proc.returncode not in (0, None) and agent_runner.detect_credit_exhaustion(stderr):
            _revert(ticket_id, snap, root, "credit exhausted")
            write_result("CREDIT_EXHAUSTED",
                         "agent reported credit/billing exhaustion", root=root)
            return "CREDIT_EXHAUSTED"

        changed = hash_guard.check(hashes_before, hash_guard.compute(root))
        if changed:
            _revert(ticket_id, snap, root, f"orchestrator modified: {changed}")
            write_result("ORCHESTRATOR_MODIFIED",
                         f"agent modified orchestrator files: {changed}", root=root)
            return "ORCHESTRATOR_MODIFIED"

        if git_ops.has_unauthorized_commits(snap, root):
            _revert(ticket_id, snap, root, "unauthorized commit")
            write_result("UNAUTHORIZED_COMMIT", "agent created a git commit", root=root)
            return "UNAUTHORIZED_COMMIT"

        tests = subprocess.run(test_cmd, cwd=root, capture_output=True, text=True)
        if tests.returncode != 0:
            _revert(ticket_id, snap, root, "tests failed")
            write_result("TEST_FAILED", (tests.stdout + tests.stderr)[-2000:], root=root)
            return "TEST_FAILED"

        analysis = subprocess.run(analysis_cmd, cwd=root, capture_output=True, text=True)
        if analysis.returncode != 0:
            _revert(ticket_id, snap, root, "static analysis failed")
            write_result("ANALYSIS_FAILED", (analysis.stdout + analysis.stderr)[-2000:], root=root)
            return "ANALYSIS_FAILED"

        # Clean implementation — preserve the diff for human review (no revert).
        diff = git_ops.diff_since(snap, root)
        if git_ops.touches_safety_critical(snap, root):
            write_audit(ticket_id, "AWAITING_ARCHITECTURE_REVIEW", "", root=root)
            write_result("AWAITING_ARCHITECTURE_REVIEW",
                         "changes touch safety-critical paths — architecture review required",
                         diff, root=root)
            return "AWAITING_ARCHITECTURE_REVIEW"

        write_audit(ticket_id, "AWAITING_REVIEW", "", root=root)
        write_result("AWAITING_REVIEW",
                     "implementation complete; awaiting human review", diff, root=root)
        return "AWAITING_REVIEW"
    finally:
        try:
            if lock.exists() and lock.read_text().strip() == str(os.getpid()):
                lock.unlink()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m scripts.workflows.implement_ticket T###", file=sys.stderr)
        return 2
    outcome = run_workflow(
        argv[0],
        root=git_ops._get_root(),
        cli_path=os.environ.get("CLAUDE_CLI_PATH"),
        timeout_s=int(os.environ.get("WORKFLOW_TIMEOUT_S", DEFAULT_TIMEOUT_S)),
    )
    print(outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
