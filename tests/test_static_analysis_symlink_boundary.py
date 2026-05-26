"""tests/test_static_analysis_symlink_boundary.py

Integration tests for T044: workspace boundary enforcement inside check functions.

Verifies that when scan_root contains symlinks pointing outside the repo boundary,
check functions either skip the symlinked files or (for run_static_analysis) the
tool exits 2. No file outside scan_root must be read.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

from prepare_opus_context import check_test_syntax, check_utcnow, check_bash_blocks


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_git_repo(base: Path, name: str = "repo") -> Path:
    """Create a minimal git repo with one commit. Returns repo root."""
    repo = base / name
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"],
                   capture_output=True, check=True)
    (repo / "placeholder.txt").write_text("placeholder")
    subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "initial"],
                   capture_output=True, check=True)
    return repo


# ── T044: symlink boundary tests ──────────────────────────────────────────────

class TestCheckTestSyntaxSymlinkBoundary:
    """check_test_syntax must not read files outside scan_root via symlinks."""

    def test_symlinked_test_file_outside_repo_is_skipped(self, tmp_path):
        """A symlink in tests/ pointing to a file outside the repo must be skipped.

        The check must not py_compile the outside file. We verify this by placing
        a syntax-error file outside the repo — if the check reads it, it returns
        FAIL; if it skips it, it returns PASS or SKIP (no test files).
        """
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        # Place a file with a syntax error outside the repo
        evil_file = outside_dir / "evil_syntax.py"
        evil_file.write_text("def broken(:\n    pass\n")  # deliberate SyntaxError

        repo = tmp_path / "repo"
        repo.mkdir()
        tests_dir = repo / "tests"
        tests_dir.mkdir()

        # Symlink inside tests/ pointing to the evil file outside repo
        symlink = tests_dir / "test_evil_outside.py"
        symlink.symlink_to(evil_file)

        result = check_test_syntax(repo)

        # The check must NOT return FAIL caused by the outside file.
        # Acceptable outcomes: PASS (no inside test files found/compiled cleanly),
        # SKIP (only symlinks present, skipped), or any result that is NOT FAIL.
        assert not result.startswith("FAIL"), (
            f"check_test_syntax followed symlink outside scan_root and reported FAIL: {result!r}\n"
            "Expected: PASS or SKIP (symlinked file outside boundary must be ignored)"
        )

    def test_symlinked_test_file_inside_repo_is_accepted(self, tmp_path):
        """A symlink pointing to a file INSIDE the repo boundary is fine to check."""
        repo = tmp_path / "repo"
        repo.mkdir()
        tests_dir = repo / "tests"
        tests_dir.mkdir()

        # Real file inside the repo
        real_file = repo / "test_helper_real.py"
        real_file.write_text("def test_ok(): pass\n")

        # Symlink inside tests/ pointing to inside-repo file
        symlink = tests_dir / "test_via_symlink.py"
        symlink.symlink_to(real_file)

        result = check_test_syntax(repo)

        # Should compile cleanly (PASS), not SKIP or FAIL
        assert result.startswith("PASS"), (
            f"check_test_syntax rejected an in-boundary symlink: {result!r}"
        )

    def test_normal_test_file_still_checked(self, tmp_path):
        """Non-symlinked test files must still be checked normally."""
        repo = tmp_path / "repo"
        repo.mkdir()
        tests_dir = repo / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_ok.py").write_text("def test_pass(): pass\n")

        result = check_test_syntax(repo)
        assert result.startswith("PASS"), f"Unexpected result: {result!r}"

    def test_syntax_error_in_normal_file_still_caught(self, tmp_path):
        """A real (non-symlinked) syntax error inside the repo must still be caught."""
        repo = tmp_path / "repo"
        repo.mkdir()
        tests_dir = repo / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_broken.py").write_text("def broken(:\n    pass\n")

        result = check_test_syntax(repo)
        assert result.startswith("FAIL"), f"Expected FAIL for syntax error, got: {result!r}"


class TestCheckUtcnowSymlinkBoundary:
    """check_utcnow must not follow symlinks outside scan_root via grep -r."""

    def test_symlinked_dir_outside_repo_not_grepped(self, tmp_path):
        """A symlinked directory inside scripts/ pointing outside must not be grepped.

        We place a file with 'utcnow' outside the repo. If grep follows the symlink,
        check_utcnow returns WARN. If symlinks are not dereferenced, it returns PASS.
        """
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        # Place a file with utcnow outside the repo
        (outside_dir / "evil_utcnow.py").write_text(
            "import datetime\nnow = datetime.utcnow()\n"
        )

        repo = tmp_path / "repo"
        repo.mkdir()
        scripts_dir = repo / "scripts"
        scripts_dir.mkdir()

        # Symlink inside scripts/ pointing to the outside directory
        symlink_dir = scripts_dir / "evil_outside"
        symlink_dir.symlink_to(outside_dir)

        result = check_utcnow(repo)

        # Must not return WARN caused by the outside file
        assert not result.startswith("WARN"), (
            f"check_utcnow followed symlink outside scan_root and reported WARN: {result!r}\n"
            "Expected: PASS (symlinked directory outside boundary must not be grepped)"
        )

    def test_utcnow_in_normal_file_still_caught(self, tmp_path):
        """A real utcnow usage inside the repo must still be detected."""
        repo = tmp_path / "repo"
        repo.mkdir()
        scripts_dir = repo / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "bad.py").write_text(
            "import datetime\nnow = datetime.utcnow()\n"
        )

        result = check_utcnow(repo)
        assert result.startswith("WARN"), f"Expected WARN for utcnow, got: {result!r}"

    def test_no_utcnow_passes(self, tmp_path):
        """No utcnow in any file must return PASS."""
        repo = tmp_path / "repo"
        repo.mkdir()
        scripts_dir = repo / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "clean.py").write_text(
            "import datetime\nnow = datetime.now(datetime.timezone.utc)\n"
        )

        result = check_utcnow(repo)
        assert result.startswith("PASS"), f"Expected PASS, got: {result!r}"


class TestRunStaticAnalysisSymlinkBoundary:
    """Integration test: run_static_analysis.py with a symlinked file outside repo.

    Since run_static_analysis.py uses workspace config for scan_root and defaults
    to ROOT when no workspace is active, we test via the check functions directly
    (which is how _run_checks_for_repo calls them).

    The contract: a symlink inside scan_root pointing outside must not cause
    any check to read/process the outside file.
    """

    RUN_SA = ROOT / "scripts" / "tools" / "run_static_analysis.py"

    def test_symlink_outside_repo_does_not_cause_fail(self, tmp_path):
        """End-to-end: scan_root with outside symlinks must not produce false FAILs.

        We construct a scan_root with:
        - A clean tests/ directory (would normally PASS check_test_syntax)
        - A symlink in tests/ pointing to an outside file with a syntax error
        - A clean scripts/ directory (would normally PASS check_utcnow)
        - A symlink in scripts/ pointing to an outside dir containing utcnow

        If boundary is enforced, all checks pass (symlinked content is skipped).
        If boundary is violated, checks falsely FAIL/WARN on outside content.
        """
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "evil_syntax.py").write_text("def bad(:\n    pass\n")
        outside_scripts = tmp_path / "outside_scripts"
        outside_scripts.mkdir()
        (outside_scripts / "utcnow_usage.py").write_text(
            "import datetime\nnow = datetime.utcnow()\n"
        )

        repo = tmp_path / "repo"
        repo.mkdir()
        tests_dir = repo / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_clean.py").write_text("def test_ok(): pass\n")
        # Symlink inside tests/ to outside evil file
        (tests_dir / "test_outside_evil.py").symlink_to(outside / "evil_syntax.py")

        scripts_dir = repo / "scripts"
        scripts_dir.mkdir()
        # Symlink inside scripts/ to outside dir with utcnow
        (scripts_dir / "evil_dir").symlink_to(outside_scripts)

        # Run each check directly and verify boundary is respected
        syntax_result = check_test_syntax(repo)
        utcnow_result = check_utcnow(repo)

        assert not syntax_result.startswith("FAIL"), (
            f"check_test_syntax leaked across symlink boundary: {syntax_result!r}"
        )
        assert not utcnow_result.startswith("WARN"), (
            f"check_utcnow leaked across symlink boundary: {utcnow_result!r}"
        )
