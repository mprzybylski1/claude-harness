"""
Tests for T080: check_fix_commit_has_code.py PreToolUse hook.

Covers the four AC cases plus edge cases for command parsing.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "hooks" / "check_fix_commit_has_code.py"


def _run_hook(command: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True,
    )


def _run_hook_tool(tool_name: str, command: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True,
    )


# ── Helpers to build a real git repo for staged-file checks ──────────────────

def _make_git_repo(path: Path) -> None:
    for cmd in [
        ["git", "init", "-q", str(path)],
        ["git", "-C", str(path), "config", "user.email", "t@t.com"],
        ["git", "-C", str(path), "config", "user.name", "Test"],
        ["git", "-C", str(path), "config", "commit.gpgsign", "false"],
    ]:
        subprocess.run(cmd, check=True, capture_output=True)


def _run_hook_in_repo(repo: Path, command: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True,
        cwd=str(repo),
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
    )


# ── AC cases ─────────────────────────────────────────────────────────────────

class TestFixCommitHasCode:

    # (a) fix(T001): with no code staged → blocked
    def test_fix_commit_no_code_staged_blocked(self, tmp_path):
        _make_git_repo(tmp_path)
        # Stage only a docs file
        docs_file = tmp_path / "some_notes.md"
        docs_file.write_text("notes")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(docs_file)],
                       check=True, capture_output=True)

        result = _run_hook_in_repo(tmp_path, 'git commit -m "fix(T001): a fix"')
        assert result.returncode != 0, f"Expected block, got 0\nstdout={result.stdout}\nstderr={result.stderr}"
        assert "T001" in result.stderr or "T001" in result.stdout, \
            f"Expected ticket ID in output:\n{result.stderr}"

    # (b) fix(T001): with scripts/foo.py staged → allowed
    def test_fix_commit_with_code_staged_allowed(self, tmp_path):
        _make_git_repo(tmp_path)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        code_file = scripts_dir / "foo.py"
        code_file.write_text("# code")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(code_file)],
                       check=True, capture_output=True)

        result = _run_hook_in_repo(tmp_path, 'git commit -m "fix(T001): a fix"')
        assert result.returncode == 0, f"Expected allow, got non-zero\nstderr={result.stderr}"

    # (c) docs: ... with no code staged → allowed
    def test_docs_commit_no_code_staged_allowed(self, tmp_path):
        _make_git_repo(tmp_path)
        docs_file = tmp_path / "NOTES.md"
        docs_file.write_text("notes")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(docs_file)],
                       check=True, capture_output=True)

        result = _run_hook_in_repo(tmp_path, 'git commit -m "docs: S17 session close"')
        assert result.returncode == 0, f"Expected allow for docs: commit\nstderr={result.stderr}"

    # (d) fix(T001): with only docs/archive/T001-...md staged → blocked
    def test_fix_commit_only_archive_staged_blocked(self, tmp_path):
        _make_git_repo(tmp_path)
        archive_dir = tmp_path / "docs" / "archive"
        archive_dir.mkdir(parents=True)
        archive_file = archive_dir / "T001-fix-the-thing.md"
        archive_file.write_text("closed ticket")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(archive_file)],
                       check=True, capture_output=True)

        result = _run_hook_in_repo(tmp_path, 'git commit -m "fix(T001): fix the thing"')
        assert result.returncode != 0, f"Expected block for archive-only staged commit\nstderr={result.stderr}"

    # Hook does not block non-Bash tool names
    def test_non_bash_tool_ignored(self):
        result = _run_hook_tool("Edit", 'fix(T001): this is not a commit')
        assert result.returncode == 0

    # Hook does not block commands that aren't git commit
    def test_non_commit_bash_ignored(self, tmp_path):
        result = _run_hook('git status')
        assert result.returncode == 0

    # --no-verify bypass
    def test_no_verify_bypasses_check(self, tmp_path):
        _make_git_repo(tmp_path)
        # No files staged — would normally be blocked
        result = _run_hook_in_repo(tmp_path, 'git commit --no-verify -m "fix(T001): bypass"')
        assert result.returncode == 0, \
            f"--no-verify must bypass the hook\nstderr={result.stderr}"

    # tests/ prefix also counts as code
    def test_tests_file_satisfies_code_check(self, tmp_path):
        _make_git_repo(tmp_path)
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_foo.py"
        test_file.write_text("def test_x(): pass")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(test_file)],
                       check=True, capture_output=True)

        result = _run_hook_in_repo(tmp_path, 'git commit -m "fix(T042): add test"')
        assert result.returncode == 0

    # Multi-word ticket prefix variants
    def test_fix_prefix_case_sensitive(self, tmp_path):
        """'Fix(T001):' (capital F) must not be treated as a fix commit."""
        _make_git_repo(tmp_path)
        result = _run_hook_in_repo(tmp_path, 'git commit -m "Fix(T001): wrong case"')
        assert result.returncode == 0, "Capital-F Fix must not trigger the hook"

    def test_error_message_suggests_files_flag(self, tmp_path):
        """Blocked commit message must suggest close_ticket.py --files."""
        _make_git_repo(tmp_path)
        docs_file = tmp_path / "notes.md"
        docs_file.write_text("x")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(docs_file)],
                       check=True, capture_output=True)

        result = _run_hook_in_repo(tmp_path, 'git commit -m "fix(T099): missing code"')
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "--files" in combined or "close_ticket" in combined, \
            f"Expected --files suggestion in output:\n{combined}"


class TestWorkspaceAwareness:
    """T086: hook must query the correct git repo when git -C <path> is used."""

    def test_workspace_commit_with_code_staged_allowed(self, tmp_path):
        """git -C <project> commit fix(TXXX): → allowed when code is staged in project repo."""
        project = tmp_path / "project"
        project.mkdir()
        _make_git_repo(project)
        scripts_dir = project / "scripts"
        scripts_dir.mkdir()
        code = scripts_dir / "app.py"
        code.write_text("# v1")
        subprocess.run(["git", "-C", str(project), "add", str(code)],
                       check=True, capture_output=True)

        command = f'git -C {project} commit -m "fix(T042): workspace fix"'
        result = _run_hook_in_repo(tmp_path, command)
        assert result.returncode == 0, \
            f"Expected allow for workspace commit with code staged\nstderr={result.stderr}"

    def test_workspace_commit_archive_only_blocked(self, tmp_path):
        """git -C <project> commit fix(TXXX): → blocked when only archive/ is staged."""
        project = tmp_path / "project"
        project.mkdir()
        _make_git_repo(project)
        archive_dir = project / "docs" / "archive"
        archive_dir.mkdir(parents=True)
        archive_file = archive_dir / "T042-foo.md"
        archive_file.write_text("closed")
        subprocess.run(["git", "-C", str(project), "add", str(archive_file)],
                       check=True, capture_output=True)

        command = f'git -C {project} commit -m "fix(T042): workspace fix"'
        result = _run_hook_in_repo(tmp_path, command)
        assert result.returncode != 0, \
            f"Expected block for workspace commit with only archive staged\nstderr={result.stderr}"

    def test_workspace_archive_at_any_depth_excluded(self, tmp_path):
        """Paths containing 'archive' anywhere in the tree are excluded from code count."""
        project = tmp_path / "project"
        project.mkdir()
        _make_git_repo(project)
        # Workspace-style path: .harness/archive/T042-foo.md
        ws_archive = project / ".harness" / "archive"
        ws_archive.mkdir(parents=True)
        archive_file = ws_archive / "T042-foo.md"
        archive_file.write_text("closed")
        subprocess.run(["git", "-C", str(project), "add", str(archive_file)],
                       check=True, capture_output=True)

        command = f'git -C {project} commit -m "fix(T042): workspace fix"'
        result = _run_hook_in_repo(tmp_path, command)
        assert result.returncode != 0, \
            f"Expected block for commit with only .harness/archive staged\nstderr={result.stderr}"
