"""Tests for T147: close_ticket.py --commit flag and commit prefix derivation.

Commit prefix: fix(T###) when --files includes non-.md code files, docs(T###) otherwise.
Multi-root guard: --commit refuses when staged files span multiple git roots.
Index-clean guard: --commit refuses when the index contains unrelated staged changes.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
import close_ticket  # noqa: E402


class TestCommitPrefix:
    def test_code_files_yield_fix_prefix(self):
        files = [Path("src/main.py"), Path("tests/test_main.py")]
        assert close_ticket._commit_prefix("T099", files) == "fix(T099):"

    def test_only_md_files_yield_docs_prefix(self):
        files = [Path("docs/notes.md")]
        assert close_ticket._commit_prefix("T099", files) == "docs(T099):"

    def test_no_files_yield_docs_prefix(self):
        assert close_ticket._commit_prefix("T099", []) == "docs(T099):"

    def test_mixed_files_yield_fix_prefix(self):
        files = [Path("README.md"), Path("src/lib.py")]
        assert close_ticket._commit_prefix("T099", files) == "fix(T099):"

    def test_non_md_non_py_still_fix(self):
        files = [Path("config.yaml")]
        assert close_ticket._commit_prefix("T099", files) == "fix(T099):"


class TestCollectStagedRoots:
    """_collect_staged_roots returns the set of git roots involved in a close."""

    def test_single_root(self):
        paths = [Path("/repo/a.md"), Path("/repo/b.py")]
        with patch.object(close_ticket, "_git_root_for", return_value=("/repo", "")):
            roots = close_ticket._collect_staged_roots(paths)
        assert roots == {"/repo"}

    def test_multiple_roots(self):
        def fake_root(p):
            if "harness" in str(p):
                return ("/harness", "")
            return ("/project", "")

        paths = [Path("/harness/sr.md"), Path("/project/archive/t.md")]
        with patch.object(close_ticket, "_git_root_for", side_effect=fake_root):
            roots = close_ticket._collect_staged_roots(paths)
        assert roots == {"/harness", "/project"}

    def test_none_root_excluded(self):
        paths = [Path("/repo/a.md"), Path("/outside/b.md")]
        def fake_root(p):
            if "outside" in str(p):
                return (None, "not a repo")
            return ("/repo", "")

        with patch.object(close_ticket, "_git_root_for", side_effect=fake_root):
            roots = close_ticket._collect_staged_roots(paths)
        assert roots == {"/repo"}

    def test_empty_paths(self):
        roots = close_ticket._collect_staged_roots([])
        assert roots == set()


class TestCommitMultiRootRefusal:
    """--commit must refuse when staged files span multiple git roots."""

    def test_multi_root_exits_2(self, capsys):
        roots = {"/repo-a", "/repo-b"}
        msg = "fix(T099): did the thing"
        with pytest.raises(SystemExit) as exc:
            close_ticket._refuse_multi_root_commit(roots, "T099", msg)
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "multiple git roots" in err.lower()
        assert "/repo-a" in err or "/repo-b" in err

    def test_single_root_does_not_exit(self):
        roots = {"/repo"}
        close_ticket._refuse_multi_root_commit(roots, "T099", "fix(T099): x")


class TestCheckIndexClean:
    """_check_index_clean exits 2 when unrelated staged changes are present."""

    def _run(self, porcelain_output: str, expected_paths: list[Path], ticket_path: Path):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = porcelain_output
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            close_ticket._check_index_clean("/repo", expected_paths, ticket_path)

    def test_clean_index_passes(self):
        # Index contains only the archive dest and the ticket deletion — no unexpected paths.
        ticket = Path("/repo/docs/tickets/open/T099-foo.md")
        dest = Path("/repo/docs/archive/T099-foo.md")
        porcelain = f"D  docs/tickets/open/T099-foo.md\nA  docs/archive/T099-foo.md\n"
        self._run(porcelain, [dest], ticket)  # should not raise

    def test_unrelated_staged_file_exits_2(self, capsys):
        ticket = Path("/repo/docs/tickets/open/T099-foo.md")
        dest = Path("/repo/docs/archive/T099-foo.md")
        porcelain = (
            f"D  docs/tickets/open/T099-foo.md\n"
            f"A  docs/archive/T099-foo.md\n"
            f"M  src/unrelated.py\n"  # unrelated staged change
        )
        with pytest.raises(SystemExit) as exc:
            self._run(porcelain, [dest], ticket)
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "unrelated staged changes" in err.lower() or "beyond what" in err

    def test_unstaged_changes_ignored(self):
        # Column 0 is space → unstaged; column 1 is M → modified in working tree.
        ticket = Path("/repo/docs/tickets/open/T099-foo.md")
        dest = Path("/repo/docs/archive/T099-foo.md")
        porcelain = (
            f"D  docs/tickets/open/T099-foo.md\n"
            f"A  docs/archive/T099-foo.md\n"
            f" M src/unstaged.py\n"  # working-tree-only, not staged
        )
        self._run(porcelain, [dest], ticket)  # should not raise

    def test_git_status_failure_exits_2(self, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stdout = ""
        mock_result.stderr = "fatal: not a git repo"
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(SystemExit) as exc:
                close_ticket._check_index_clean(
                    "/repo",
                    [Path("/repo/docs/archive/T099-foo.md")],
                    Path("/repo/docs/tickets/open/T099-foo.md"),
                )
        assert exc.value.code == 2


