"""Tests for T152: detect gitignored docs_path at session-start."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "check_docs_path_gitignored.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_docs_path_gitignored", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_git_repo(path: Path) -> None:
    for cmd in [
        ["git", "-C", str(path), "init", "-q"],
        ["git", "-C", str(path), "config", "user.email", "t@test.com"],
        ["git", "-C", str(path), "config", "user.name", "Test"],
    ]:
        subprocess.run(cmd, check=True, capture_output=True)


class TestCheckDocsPathGitignored:

    def test_warns_when_docs_path_is_gitignored(self, tmp_path):
        repo = tmp_path / "myrepo"
        repo.mkdir()
        _make_git_repo(repo)
        docs = repo / ".harness"
        docs.mkdir()
        (repo / ".gitignore").write_text(".harness/\n")
        subprocess.run(
            ["git", "-C", str(repo), "add", ".gitignore"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "init"],
            check=True, capture_output=True,
        )

        harness = tmp_path / "harness"
        ws_dir = harness / "workspaces" / "test-ws"
        ws_dir.mkdir(parents=True)
        (ws_dir / "workspace.yaml").write_text(yaml.dump({
            "name": "Test",
            "type": "personal",
            "status": "active",
            "repos": [{"name": "repo", "path": str(repo), "role": "primary"}],
            "docs_path": str(docs),
        }))

        mod = _load_module()
        result = mod.check_gitignored("test-ws", root=harness)
        assert result is not None
        assert "gitignored" in result
        assert "will not sync" in result

    def test_silent_when_docs_path_not_gitignored(self, tmp_path):
        repo = tmp_path / "myrepo"
        repo.mkdir()
        _make_git_repo(repo)
        docs = repo / ".harness"
        docs.mkdir()

        harness = tmp_path / "harness"
        ws_dir = harness / "workspaces" / "test-ws"
        ws_dir.mkdir(parents=True)
        (ws_dir / "workspace.yaml").write_text(yaml.dump({
            "name": "Test",
            "type": "personal",
            "status": "active",
            "repos": [{"name": "repo", "path": str(repo), "role": "primary"}],
            "docs_path": str(docs),
        }))

        mod = _load_module()
        result = mod.check_gitignored("test-ws", root=harness)
        assert result is None

    def test_silent_when_no_docs_path(self, tmp_path):
        harness = tmp_path / "harness"
        ws_dir = harness / "workspaces" / "test-ws"
        ws_dir.mkdir(parents=True)
        (ws_dir / "workspace.yaml").write_text(yaml.dump({
            "name": "Test",
            "type": "personal",
            "status": "active",
            "repos": [{"name": "repo", "path": "~/myrepo", "role": "primary"}],
        }))

        mod = _load_module()
        result = mod.check_gitignored("test-ws", root=harness)
        assert result is None

    def test_silent_when_docs_path_does_not_exist(self, tmp_path):
        harness = tmp_path / "harness"
        ws_dir = harness / "workspaces" / "test-ws"
        ws_dir.mkdir(parents=True)
        (ws_dir / "workspace.yaml").write_text(yaml.dump({
            "name": "Test",
            "type": "personal",
            "status": "active",
            "repos": [{"name": "repo", "path": "~/myrepo", "role": "primary"}],
            "docs_path": str(tmp_path / "nonexistent" / ".harness"),
        }))

        mod = _load_module()
        result = mod.check_gitignored("test-ws", root=harness)
        assert result is None

    def test_cli_prints_warning(self, tmp_path):
        repo = tmp_path / "myrepo"
        repo.mkdir()
        _make_git_repo(repo)
        docs = repo / ".harness"
        docs.mkdir()
        (repo / ".gitignore").write_text(".harness/\n")
        subprocess.run(
            ["git", "-C", str(repo), "add", ".gitignore"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "init"],
            check=True, capture_output=True,
        )

        harness = tmp_path / "harness"
        ws_dir = harness / "workspaces" / "test-ws"
        ws_dir.mkdir(parents=True)
        (ws_dir / "workspace.yaml").write_text(yaml.dump({
            "name": "Test",
            "type": "personal",
            "status": "active",
            "repos": [{"name": "repo", "path": str(repo), "role": "primary"}],
            "docs_path": str(docs),
        }))

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "test-ws"],
            capture_output=True, text=True,
            env={**__import__("os").environ, "HARNESS_ROOT": str(harness)},
        )
        assert result.returncode == 0
        assert "gitignored" in result.stdout
