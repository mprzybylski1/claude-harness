"""
Tests for T023: workspace.py cmd_create should add opus_review_context.md
to the project repo's .gitignore when docs_path is set.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

from workspace import _add_opus_context_to_gitignore


def _make_git_repo(base: Path) -> Path:
    """Create a minimal git repo. Returns repo root."""
    repo = base / "project_repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"],
                   capture_output=True, check=True)
    # Need at least one commit for git commands to work properly
    (repo / "README.md").write_text("# Project")
    subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"],
                   capture_output=True, check=True)
    return repo


class TestAddOpusContextToGitignore:
    def test_creates_gitignore_when_absent(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        docs_path = repo / ".harness"
        docs_path.mkdir()

        _add_opus_context_to_gitignore(docs_path)

        gitignore = repo / ".gitignore"
        assert gitignore.exists()
        assert ".harness/opus_review_context.md" in gitignore.read_text()

    def test_appends_to_existing_gitignore(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        docs_path = repo / ".harness"
        docs_path.mkdir()
        gitignore = repo / ".gitignore"
        gitignore.write_text("*.pyc\n__pycache__/\n")

        _add_opus_context_to_gitignore(docs_path)

        content = gitignore.read_text()
        assert "*.pyc" in content
        assert ".harness/opus_review_context.md" in content

    def test_idempotent_when_entry_already_present(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        docs_path = repo / ".harness"
        docs_path.mkdir()
        gitignore = repo / ".gitignore"
        gitignore.write_text(".harness/opus_review_context.md\n")

        _add_opus_context_to_gitignore(docs_path)

        content = gitignore.read_text()
        # Entry should appear exactly once
        assert content.count(".harness/opus_review_context.md") == 1

    def test_nested_docs_path_uses_correct_relative_path(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        docs_path = repo / "infra" / "harness" / "docs"
        docs_path.mkdir(parents=True)

        _add_opus_context_to_gitignore(docs_path)

        gitignore = repo / ".gitignore"
        assert gitignore.exists()
        assert "infra/harness/docs/opus_review_context.md" in gitignore.read_text()

    def test_skips_when_not_in_git_repo(self, tmp_path):
        docs_path = tmp_path / "not_a_repo" / "docs"
        docs_path.mkdir(parents=True)

        # Should not raise, just no-op
        _add_opus_context_to_gitignore(docs_path)

        assert not (tmp_path / ".gitignore").exists()

    def test_skips_when_docs_path_is_inside_harness_repo(self):
        """docs_path inside the harness root itself must not write to harness .gitignore."""
        harness_gitignore = ROOT / ".gitignore"
        before = harness_gitignore.read_text() if harness_gitignore.exists() else None

        # Use a real subdirectory of the harness repo as docs_path
        docs_path = ROOT / "docs"
        _add_opus_context_to_gitignore(docs_path)

        after = harness_gitignore.read_text() if harness_gitignore.exists() else None
        assert before == after, "harness .gitignore must not change for same-repo docs_path"
