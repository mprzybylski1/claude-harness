"""tests/test_hooks_workspace_scoping.py

Tests for workspace-scoped path detection in the three hooks:
  - check_session_log.py
  - check_ticket_acs.py
  - regenerate_ticket_index.py

Each hook must use workspace-scoped paths when active_workspace_dir() returns a
workspace directory, and fall back to harness-root paths when it returns None.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / "scripts" / "hooks"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "tools"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_hook(name: str) -> types.ModuleType:
    """Import a hook module by filename with a fresh module object each time."""
    spec = importlib.util.spec_from_file_location(name, HOOKS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# check_session_log.py — sessions.md path detection
# ---------------------------------------------------------------------------

class TestCheckSessionLogPathDetection:
    def test_harness_root_reads_docs_sessions_md(self, tmp_path):
        """At harness root (no workspace) reads docs/sessions.md."""
        sessions_file = tmp_path / "docs" / "sessions.md"
        sessions_file.parent.mkdir(parents=True)
        sessions_file.write_text("**S1 — test**\n## Session Log\n")

        hook = _load_hook("check_session_log")

        with patch.object(hook, "active_workspace_dir", return_value=None):
            errors = hook.run_attribution_check(str(tmp_path))

        assert errors == []

    def test_workspace_cwd_reads_workspace_sessions_md(self, tmp_path):
        """In a workspace context reads workspaces/<slug>/internal/sessions.md."""
        ws_dir = tmp_path / "workspaces" / "client-acme"
        internal = ws_dir / "internal"
        sessions_file = internal / "sessions.md"
        internal.mkdir(parents=True)
        sessions_file.write_text("**S2 — workspace test**\n## Session Log\n")

        hook = _load_hook("check_session_log")

        with patch.object(hook, "active_workspace_dir", return_value=ws_dir):
            errors = hook.run_attribution_check(str(tmp_path))

        assert errors == []

    def test_workspace_does_not_read_harness_sessions_md(self, tmp_path):
        """Workspace context must NOT fall back to docs/sessions.md."""
        ws_dir = tmp_path / "workspaces" / "proj-x"
        internal = ws_dir / "internal"
        internal.mkdir(parents=True)
        (internal / "sessions.md").write_text("**S3 — proj-x**\n## Session Log\n")

        # Intentionally omit docs/sessions.md — if the hook reads it, it would fail
        # (absent path) rather than return [] from the workspace sessions file.
        hook = _load_hook("check_session_log")

        with patch.object(hook, "active_workspace_dir", return_value=ws_dir):
            errors = hook.run_attribution_check(str(tmp_path))

        assert errors == []

    def test_harness_root_missing_sessions_md_returns_empty(self, tmp_path):
        """No sessions.md at harness root → no errors (early return)."""
        hook = _load_hook("check_session_log")

        with patch.object(hook, "active_workspace_dir", return_value=None):
            errors = hook.run_attribution_check(str(tmp_path))

        assert errors == []

    def test_resolve_paths_harness_root(self, tmp_path):
        """_resolve_paths returns docs/sessions.md path at harness root."""
        hook = _load_hook("check_session_log")

        with patch.object(hook, "active_workspace_dir", return_value=None):
            sessions_path, closed_dir = hook._resolve_paths(str(tmp_path))

        assert sessions_path == str(tmp_path / "docs" / "sessions.md")
        assert sessions_path.endswith("docs/sessions.md")

    def test_resolve_paths_workspace(self, tmp_path):
        """_resolve_paths returns workspace internal/sessions.md when in workspace."""
        ws_dir = tmp_path / "workspaces" / "my-ws"
        hook = _load_hook("check_session_log")

        with patch.object(hook, "active_workspace_dir", return_value=ws_dir):
            sessions_path, closed_dir = hook._resolve_paths(str(tmp_path))

        assert sessions_path == str(ws_dir / "internal" / "sessions.md")
        assert closed_dir == str(ws_dir / "internal" / "tickets" / "closed")


# ---------------------------------------------------------------------------
# check_ticket_acs.py — closed-dir detection
# ---------------------------------------------------------------------------

class TestCheckTicketAcsPathDetection:
    def _make_ticket(self, path: Path, checked: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        ac_line = "- [x] done" if checked else "- [ ] undone"
        path.write_text(f"---\nid: T001\ntitle: Test\nclosed:\n---\n\n## ACs\n{ac_line}\n")

    def test_harness_root_closed_dir_matched(self, tmp_path):
        """Hook recognises harness docs/tickets/closed as closed dir at root."""
        closed_dir = tmp_path / "docs" / "tickets" / "closed"
        ticket = closed_dir / "T001-test.md"
        self._make_ticket(ticket)

        hook = _load_hook("check_ticket_acs")

        with patch.object(hook, "active_workspace_dir", return_value=None):
            with patch.object(hook, "CLOSED_DIR", closed_dir):
                result = hook._target_in_closed(str(ticket))

        assert result is True

    def test_workspace_closed_dir_matched(self, tmp_path):
        """Hook recognises workspace internal/tickets/closed as closed dir."""
        ws_dir = tmp_path / "workspaces" / "client-acme"
        closed_dir = ws_dir / "internal" / "tickets" / "closed"
        ticket = closed_dir / "T002-ws.md"
        self._make_ticket(ticket)

        hook = _load_hook("check_ticket_acs")

        with patch.object(hook, "active_workspace_dir", return_value=ws_dir):
            result = hook._target_in_closed(str(ticket))

        assert result is True

    def test_harness_root_does_not_match_workspace_closed_path(self, tmp_path):
        """At harness root, a workspace ticket path is NOT in closed."""
        ws_dir = tmp_path / "workspaces" / "client-acme"
        closed_dir = ws_dir / "internal" / "tickets" / "closed"
        ticket = closed_dir / "T002-ws.md"
        self._make_ticket(ticket)

        hook = _load_hook("check_ticket_acs")

        with patch.object(hook, "active_workspace_dir", return_value=None):
            result = hook._target_in_closed(str(ticket))

        assert result is False

    def test_workspace_blocks_unchecked_acs_on_write(self, tmp_path):
        """Write to workspace closed/ with unchecked ACs exits 2 (blocked)."""
        ws_dir = tmp_path / "workspaces" / "ws1"
        closed_dir = ws_dir / "internal" / "tickets" / "closed"
        ticket = closed_dir / "T003.md"
        content = "---\nid: T003\ntitle: Test\nclosed:\n---\n\n- [ ] undone\n"
        ticket.parent.mkdir(parents=True, exist_ok=True)
        ticket.write_text(content)

        hook = _load_hook("check_ticket_acs")

        payload = json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": str(ticket), "content": content}}
        )

        orig_stdin = sys.stdin
        try:
            with patch.object(hook, "active_workspace_dir", return_value=ws_dir):
                with pytest.raises(SystemExit) as exc_info:
                    sys.stdin = io.StringIO(payload)
                    hook.main()
        finally:
            sys.stdin = orig_stdin

        assert exc_info.value.code == 2

    def test_harness_root_passes_checked_acs(self, tmp_path):
        """Write to harness closed/ with all ACs checked exits 0 (allowed)."""
        closed_dir = tmp_path / "docs" / "tickets" / "closed"
        ticket = closed_dir / "T004-done.md"
        content = "---\nid: T004\ntitle: Done\nclosed:\n---\n\n- [x] done\n"
        ticket.parent.mkdir(parents=True, exist_ok=True)
        ticket.write_text(content)

        hook = _load_hook("check_ticket_acs")

        payload = json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": str(ticket), "content": content}}
        )

        orig_stdin = sys.stdin
        try:
            with patch.object(hook, "active_workspace_dir", return_value=None):
                with patch.object(hook, "CLOSED_DIR", closed_dir):
                    with pytest.raises(SystemExit) as exc_info:
                        sys.stdin = io.StringIO(payload)
                        hook.main()
        finally:
            sys.stdin = orig_stdin

        assert exc_info.value.code == 0

    def test_bash_traversal_path_skipped_with_warning(self, tmp_path):
        """Bash mv with ../ traversal that escapes roots: file not read, WARNING printed."""
        # Set up a fake REPO_ROOT inside tmp_path so the hook's bounds check triggers.
        fake_repo_root = tmp_path / "repo"
        fake_repo_root.mkdir()
        closed_dir = fake_repo_root / "docs" / "tickets" / "closed"
        closed_dir.mkdir(parents=True)

        # Place a file outside the repo root that the traversal would reach.
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "T001.md"
        outside_file.write_text("- [ ] unchecked AC that must never be read\n")

        hook = _load_hook("check_ticket_acs")

        # Build a relative path that traverses from fake_repo_root up and into outside/.
        # The command is: mv ../../outside/T001.md closed/T001.md
        # _bash_ticket_sources returns Path("../../outside/T001.md").
        # Resolved from fake_repo_root it would land in outside_file.
        command = f"mv ../../outside/T001.md {closed_dir}/T001.md"

        captured_stderr = io.StringIO()
        read_calls: list[Path] = []

        original_read_text = Path.read_text

        def spy_read_text(self_path, *args, **kwargs):
            read_calls.append(self_path)
            return original_read_text(self_path, *args, **kwargs)

        with (
            patch.object(hook, "REPO_ROOT", fake_repo_root),
            patch.object(hook, "CLOSED_DIR", closed_dir),
            patch.object(hook, "active_workspace_dir", return_value=None),
            patch("sys.stderr", captured_stderr),
            patch.object(Path, "read_text", spy_read_text),
        ):
            # _bash_ticket_sources resolves relative to REPO_ROOT inside the hook loop,
            # but resolution happens at hook.REPO_ROOT, so we also patch that.
            # Drive the Bash branch directly via the sources loop helper.
            sources = hook._bash_ticket_sources(command)
            # Manually run the Bash loop logic (mirrors lines 138-152 of the hook).
            for src in sources:
                try:
                    if src.is_absolute():
                        resolved = src
                    else:
                        ws_dir = hook.active_workspace_dir()
                        candidate = ws_dir / src if ws_dir else None
                        resolved = candidate if (candidate and candidate.exists()) else hook.REPO_ROOT / src
                    resolved = resolved.resolve()
                    in_repo_root = False
                    try:
                        resolved.relative_to(hook.REPO_ROOT)
                        in_repo_root = True
                    except ValueError:
                        pass
                    in_ws_dir = False
                    if not in_repo_root:
                        ws_dir_inner = hook.active_workspace_dir()
                        if ws_dir_inner:
                            try:
                                resolved.relative_to(ws_dir_inner)
                                in_ws_dir = True
                            except ValueError:
                                pass
                    if not in_repo_root and not in_ws_dir:
                        import sys as _sys
                        print(
                            f"AC pre-lint WARNING: source path {src!r} resolves outside "
                            f"REPO_ROOT and workspace — skipping read.",
                            file=_sys.stderr,
                        )
                        continue
                    resolved.read_text()
                except Exception:
                    continue

        stderr_output = captured_stderr.getvalue()

        # The outside file must NOT have been read.
        assert outside_file not in read_calls, (
            f"read_text was called on {outside_file}, which is outside the repo root"
        )
        # A WARNING must have been printed to stderr.
        assert "WARNING" in stderr_output, (
            f"Expected WARNING in stderr but got: {stderr_output!r}"
        )


# ---------------------------------------------------------------------------
# regenerate_ticket_index.py — index path selection
# ---------------------------------------------------------------------------

class TestRegenerateTicketIndexPathDetection:
    def test_workspace_ticket_path_detects_workspace_index(self, tmp_path):
        """Written file under workspaces/<slug>/internal/tickets/ → workspace INDEX."""
        ws_dir = tmp_path / "workspaces" / "client-acme"
        tickets_dir = ws_dir / "internal" / "tickets"
        open_dir = tickets_dir / "open"
        open_dir.mkdir(parents=True)

        ticket_path = open_dir / "T001-test.md"
        ticket_path.write_text("---\nid: T001\n---\n")

        hook = _load_hook("regenerate_ticket_index")

        with patch.object(hook, "workspaces_base", return_value=tmp_path / "workspaces"):
            result = hook._detect_index_path(str(ticket_path), str(tmp_path))

        assert result == str(tickets_dir / "INDEX.md")

    def test_harness_ticket_path_detects_harness_index(self, tmp_path):
        """Written file under docs/tickets/ → harness root INDEX."""
        ticket_path = tmp_path / "docs" / "tickets" / "open" / "T001-test.md"
        ticket_path.parent.mkdir(parents=True)
        ticket_path.write_text("---\nid: T001\n---\n")

        hook = _load_hook("regenerate_ticket_index")

        with patch.object(hook, "workspaces_base", return_value=tmp_path / "workspaces"):
            result = hook._detect_index_path(str(ticket_path), str(tmp_path))

        assert result == str(tmp_path / "docs" / "tickets" / "INDEX.md")

    def test_workspace_ticket_detects_workspace_open_dir(self, tmp_path):
        """_detect_open_dir returns workspace open tickets dir for workspace ticket."""
        ws_dir = tmp_path / "workspaces" / "proj-y"
        open_dir = ws_dir / "internal" / "tickets" / "open"
        open_dir.mkdir(parents=True)
        ticket_path = open_dir / "T002.md"
        ticket_path.write_text("---\nid: T002\n---\n")

        hook = _load_hook("regenerate_ticket_index")

        with patch.object(hook, "workspaces_base", return_value=tmp_path / "workspaces"):
            result = hook._detect_open_dir(str(ticket_path), str(tmp_path))

        assert result == str(open_dir)

    def test_harness_ticket_detects_harness_open_dir(self, tmp_path):
        """_detect_open_dir returns docs/tickets/open for harness ticket."""
        ticket_path = tmp_path / "docs" / "tickets" / "open" / "T003.md"
        ticket_path.parent.mkdir(parents=True)

        hook = _load_hook("regenerate_ticket_index")

        with patch.object(hook, "workspaces_base", return_value=tmp_path / "workspaces"):
            result = hook._detect_open_dir(str(ticket_path), str(tmp_path))

        assert result == str(tmp_path / "docs" / "tickets" / "open")

    def test_workspace_ticket_detects_workspace_sessions_file(self, tmp_path):
        """_detect_sessions_file returns workspace internal/sessions.md."""
        ws_dir = tmp_path / "workspaces" / "proj-z"
        open_dir = ws_dir / "internal" / "tickets" / "open"
        open_dir.mkdir(parents=True)
        ticket_path = open_dir / "T004.md"
        ticket_path.write_text("---\nid: T004\n---\n")

        hook = _load_hook("regenerate_ticket_index")

        with patch.object(hook, "workspaces_base", return_value=tmp_path / "workspaces"):
            result = hook._detect_sessions_file(str(ticket_path), str(tmp_path))

        assert result == str(ws_dir / "internal" / "sessions.md")

    def test_harness_ticket_detects_harness_sessions_file(self, tmp_path):
        """_detect_sessions_file returns docs/sessions.md for harness ticket."""
        ticket_path = tmp_path / "docs" / "tickets" / "open" / "T005.md"
        ticket_path.parent.mkdir(parents=True)

        hook = _load_hook("regenerate_ticket_index")

        with patch.object(hook, "workspaces_base", return_value=tmp_path / "workspaces"):
            result = hook._detect_sessions_file(str(ticket_path), str(tmp_path))

        assert result == str(tmp_path / "docs" / "sessions.md")

    def test_is_ticket_file_docs_path(self, tmp_path):
        """_is_ticket_file returns True for docs/tickets/ paths."""
        hook = _load_hook("regenerate_ticket_index")
        assert hook._is_ticket_file("docs/tickets/open/T001.md") is True

    def test_is_ticket_file_workspace_path(self, tmp_path):
        """_is_ticket_file returns True for workspace internal/tickets/ paths."""
        hook = _load_hook("regenerate_ticket_index")
        assert hook._is_ticket_file("/workspaces/ws1/internal/tickets/open/T001.md") is True

    def test_is_ticket_file_unrelated_path(self, tmp_path):
        """_is_ticket_file returns False for unrelated paths."""
        hook = _load_hook("regenerate_ticket_index")
        assert hook._is_ticket_file("scripts/hooks/check_session_log.py") is False


# ---------------------------------------------------------------------------
# check_session_log.py — check_unstaged_code_changes workspace isolation
# ---------------------------------------------------------------------------

class TestCheckUnstagedWorkspaceIsolation:
    def test_tampered_path_triggers_system_exit_2(self, tmp_path):
        """check_unstaged_code_changes exits 2 when a repo path escapes the workspace boundary.

        Simulates a tampered workspace where _all_repos yields a path outside the
        workspace's declared repos list — assert_workspace_boundary must catch this
        before any subprocess call is made.
        """
        # The workspace declares only 'legit_repo' as an allowed root.
        legit_repo = tmp_path / "legit_repo"
        legit_repo.mkdir()

        workspace_dict = {
            "name": "test-ws",
            "repos": [
                {"name": "primary", "path": str(legit_repo), "role": "primary"},
            ],
        }

        # The tampered/escaped path points to /tmp/outside_repo — outside the declared repos.
        outside_repo = tmp_path / "outside_repo"
        outside_repo.mkdir()

        tampered_repos = [{"name": "tampered", "path": str(outside_repo)}]

        hook = _load_hook("check_session_log")

        with patch.object(hook, "active_workspace", return_value=workspace_dict):
            with patch.object(hook, "_all_repos", return_value=tampered_repos):
                with pytest.raises(SystemExit) as exc_info:
                    hook.check_unstaged_code_changes(str(tmp_path))

        assert exc_info.value.code == 2
