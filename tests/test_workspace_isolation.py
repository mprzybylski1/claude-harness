"""tests/test_workspace_isolation.py

Tests for workspace isolation enforcement in workspace_config.py.
Verifies that assert_workspace_boundary() blocks access to paths outside
declared repos and allows access to paths inside them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "tools"))
from workspace_config import is_within_workspace, assert_workspace_boundary


@pytest.fixture()
def workspace(tmp_path):
    """Minimal workspace config with two repos."""
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    repo_a.mkdir()
    repo_b.mkdir()
    return {
        "name": "Test Workspace",
        "repos": [
            {"name": "primary", "path": str(repo_a), "role": "primary"},
            {"name": "secondary", "path": str(repo_b), "role": "secondary"},
        ],
    }


class TestIsWithinWorkspace:
    def test_primary_repo_root_is_within(self, workspace, tmp_path):
        path = tmp_path / "repo-a"
        assert is_within_workspace(path, workspace) is True

    def test_nested_file_in_primary_is_within(self, workspace, tmp_path):
        path = tmp_path / "repo-a" / "src" / "main.py"
        assert is_within_workspace(path, workspace) is True

    def test_secondary_repo_root_is_within(self, workspace, tmp_path):
        path = tmp_path / "repo-b"
        assert is_within_workspace(path, workspace) is True

    def test_nested_file_in_secondary_is_within(self, workspace, tmp_path):
        path = tmp_path / "repo-b" / "components" / "App.tsx"
        assert is_within_workspace(path, workspace) is True

    def test_sibling_dir_is_outside(self, workspace, tmp_path):
        path = tmp_path / "repo-c" / "secret.py"
        assert is_within_workspace(path, workspace) is False

    def test_parent_dir_is_outside(self, workspace, tmp_path):
        assert is_within_workspace(tmp_path, workspace) is False

    def test_path_prefix_collision_blocked(self, workspace, tmp_path):
        # repo-a-evil should not match repo-a
        evil = tmp_path / "repo-a-evil" / "exfiltrate.py"
        assert is_within_workspace(evil, workspace) is False

    def test_absolute_traversal_blocked(self, workspace):
        assert is_within_workspace(Path("/etc/passwd"), workspace) is False

    def test_empty_repos_list_always_outside(self, tmp_path):
        ws = {"name": "empty", "repos": []}
        assert is_within_workspace(tmp_path / "anything.py", ws) is False


class TestAssertWorkspaceBoundary:
    def test_valid_path_does_not_exit(self, workspace, tmp_path):
        path = tmp_path / "repo-a" / "safe.py"
        assert_workspace_boundary(path, workspace)  # must not raise or exit

    def test_invalid_path_exits_with_code_2(self, workspace, tmp_path):
        path = tmp_path / "other-repo" / "secret.py"
        with pytest.raises(SystemExit) as exc_info:
            assert_workspace_boundary(path, workspace)
        assert exc_info.value.code == 2

    def test_error_message_names_workspace(self, workspace, tmp_path, capsys):
        path = tmp_path / "other-repo" / "secret.py"
        with pytest.raises(SystemExit):
            assert_workspace_boundary(path, workspace)
        captured = capsys.readouterr()
        assert "Test Workspace" in captured.err
        assert "WORKSPACE ISOLATION VIOLATION" in captured.err

    def test_error_message_shows_attempted_path(self, workspace, tmp_path, capsys):
        path = tmp_path / "other-repo" / "secret.py"
        with pytest.raises(SystemExit):
            assert_workspace_boundary(path, workspace)
        captured = capsys.readouterr()
        assert str(path.resolve()) in captured.err or "secret.py" in captured.err
