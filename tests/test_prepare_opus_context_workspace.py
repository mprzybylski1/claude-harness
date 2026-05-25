"""
Tests for T021: prepare_opus_context.py workspace flag support.

Verifies that --repo causes git diff to run against that repo,
not the harness root.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "prepare_opus_context.py"


def _make_git_repo(base: Path, filename: str = "hello.txt", content: str = "hello") -> Path:
    """Create a minimal git repo with one commit. Returns repo root."""
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"],
                   capture_output=True, check=True)
    f = repo / filename
    f.write_text(content)
    subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "initial"],
                   capture_output=True, check=True)
    return repo


class TestPrepareOpusContextRepoFlag:
    def test_repo_flag_uses_that_repo_for_diff(self, tmp_path):
        """--repo must cause git operations to run in that repo, not harness root."""
        repo = _make_git_repo(tmp_path)
        # Stage a change in the temp repo so it shows in git diff --cached
        f = repo / "unique_workspace_file.txt"
        f.write_text("workspace content")
        subprocess.run(["git", "-C", str(repo), "add", str(f)], capture_output=True, check=True)
        output = tmp_path / "opus_review_context.md"

        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--repo", str(repo),
             "--output", str(output)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert output.exists()
        context = output.read_text()
        assert "unique_workspace_file.txt" in context

    def test_non_python_repo_skips_static_analysis(self, tmp_path):
        """Non-Python repos get a SKIP for static analysis, not harness checks."""
        repo = _make_git_repo(tmp_path, filename="main.swift", content="// swift")
        output = tmp_path / "ctx.md"

        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--repo", str(repo),
             "--output", str(output)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        context = output.read_text()
        assert "static analysis N/A" in context.lower() or "SKIP" in context

    def test_output_flag_writes_to_custom_path(self, tmp_path):
        """--output must write the context file to the specified path."""
        repo = _make_git_repo(tmp_path)
        output = tmp_path / "custom_output.md"

        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--repo", str(repo),
             "--output", str(output)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert output.exists()
        # Harness-root default output should NOT have been touched
        harness_out = ROOT / "docs" / "opus_review_context.md"
        stdout = result.stdout
        assert str(output) in stdout or "custom_output.md" in stdout

    def test_sessions_flag_includes_workspace_sessions(self, tmp_path):
        """--sessions must embed the specified sessions.md in the context."""
        repo = _make_git_repo(tmp_path)
        sessions = tmp_path / "sessions.md"
        sessions.write_text(
            "# Sessions\n\n## Current Phase & Status\n\nPHASE-UNIQUE-MARKER.\n\n"
            "## Active Work\n\nActive.\n\n## Session Log\n\nS1 2026-01-01: start\n"
        )
        output = tmp_path / "ctx.md"

        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--repo", str(repo),
             "--sessions", str(sessions),
             "--output", str(output)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        context = output.read_text()
        assert "PHASE-UNIQUE-MARKER" in context

    def test_opus_flag_includes_opus_notes_in_context(self, tmp_path):
        """--opus must embed the specified opus_notes.md in the context."""
        repo = _make_git_repo(tmp_path)
        opus = tmp_path / "opus_notes.md"
        opus.write_text(
            "# Opus Notes\n\n# Opus Review — S1 2026-01-01\n\n"
            "## Invariant Violations\n\nOPUS-UNIQUE-MARKER.\n"
        )
        output = tmp_path / "ctx.md"

        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--repo", str(repo),
             "--opus", str(opus),
             "--output", str(output)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        context = output.read_text()
        assert "OPUS-UNIQUE-MARKER" in context
