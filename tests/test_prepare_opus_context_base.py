"""
Tests for T157 + T155: prepare_opus_context.py diff-base resolution.

Covers:
  - --base SHA explicitly sets the diff base
  - A fresh repo with no session-close anchor falls back to the initial commit
    (empty-tree diff) and produces a non-empty session diff
  - A fallback path warns to stderr and points at --base
  - An invalid --base value is a hard error (exit non-zero)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "prepare_opus_context.py"


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def _init_repo(base: Path) -> Path:
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    return repo


def _commit(repo: Path, filename: str, content: str, message: str) -> str:
    (repo / filename).write_text(content)
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _run_script(repo: Path, output: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--output", str(output), *extra],
        capture_output=True, text=True,
    )


class TestInitialCommitFallback:
    def test_no_anchor_produces_nonempty_committed_diff(self, tmp_path):
        """A repo with commits but no session-close anchor must still diff its
        committed content (T157) — not fall through to an empty main...HEAD."""
        repo = _init_repo(tmp_path)
        _commit(repo, "recipe.py", "FRESH-REPO-DIFF-MARKER\n", "feat: parse")
        output = tmp_path / "ctx.md"

        result = _run_script(repo, output)
        assert result.returncode == 0, result.stderr
        context = output.read_text()
        assert "FRESH-REPO-DIFF-MARKER" in context

    def test_no_anchor_warns_and_points_at_base_flag(self, tmp_path):
        repo = _init_repo(tmp_path)
        _commit(repo, "recipe.py", "x = 1\n", "feat: parse")
        output = tmp_path / "ctx.md"

        result = _run_script(repo, output)
        assert result.returncode == 0, result.stderr
        assert "WARNING" in result.stderr
        assert "--base" in result.stderr


class TestBaseFlag:
    def test_base_flag_scopes_diff_to_after_base(self, tmp_path):
        """--base <c1> must diff c1..HEAD: only the later commit's content shows."""
        repo = _init_repo(tmp_path)
        c1 = _commit(repo, "old.py", "OLD-CONTENT-MARKER\n", "c1")
        _commit(repo, "new.py", "NEW-CONTENT-MARKER\n", "c2")
        output = tmp_path / "ctx.md"

        result = _run_script(repo, output, "--base", c1)
        assert result.returncode == 0, result.stderr
        context = output.read_text()
        assert "NEW-CONTENT-MARKER" in context
        assert "OLD-CONTENT-MARKER" not in context

    def test_invalid_base_exits_nonzero(self, tmp_path):
        repo = _init_repo(tmp_path)
        _commit(repo, "a.py", "a\n", "c1")
        output = tmp_path / "ctx.md"

        result = _run_script(repo, output, "--base", "deadbeefdeadbeef")
        assert result.returncode != 0
        assert "base" in result.stderr.lower()

    def test_base_flag_appears_in_help(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "--base" in result.stdout
