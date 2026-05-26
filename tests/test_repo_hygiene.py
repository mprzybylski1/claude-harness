"""Tests for repo_hygiene.py checks."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HYGIENE = ROOT / "scripts" / "tools" / "repo_hygiene.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HYGIENE), *args],
        capture_output=True, text=True,
    )


class TestPytestCollectCheck:
    """T101: repo_hygiene warns when pytest --collect-only finds import errors."""

    def test_clean_repo_shows_no_collect_warning(self):
        """Running against the real harness (all imports OK) shows no test-import-error WARN."""
        result = _run("--warn-only")
        assert result.returncode == 0
        assert "test-import-error" not in result.stdout and "test-import-error" not in result.stderr, \
            f"Unexpected collect warning on clean repo:\n{result.stdout}"

    def test_broken_import_surfaced_as_warn(self, tmp_path):
        """A test file with a broken import produces a WARN line naming the module."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        broken = tests_dir / "test_broken_import.py"
        broken.write_text("import nonexistent_module_xyz\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(HYGIENE), "--warn-only",
             "--tests-dir", str(tests_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, "hygiene must not fail even with broken imports"
        combined = result.stdout + result.stderr
        assert "nonexistent_module_xyz" in combined or "test_broken_import" in combined, \
            f"Expected broken module/file name in output:\n{combined}"

    def test_missing_pytest_does_not_crash(self, tmp_path):
        """If python -m pytest raises FileNotFoundError/ImportError, the check is skipped (exit 0)."""
        import importlib.util
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # Import check_test_imports directly and call it with a patched subprocess.run
        import unittest.mock as mock
        spec = importlib.util.spec_from_file_location("repo_hygiene", HYGIENE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("no pytest")):
            findings = mod.check_test_imports(tests_dir)
        assert findings == [], f"Expected no findings when pytest is missing, got: {findings}"
