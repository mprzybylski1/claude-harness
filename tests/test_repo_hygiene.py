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
        """Running against the real harness (all imports OK) shows no collect error."""
        result = _run("--warn-only")
        assert result.returncode == 0
        assert "collect" not in result.stdout.lower() or "ERROR" not in result.stdout, \
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
        """If pytest binary is unavailable, the check is silently skipped (exit 0)."""
        import os
        (tmp_path / "tests").mkdir()
        # Replace PATH with a dir that has only python, not pytest
        env = {k: v for k, v in os.environ.items()}
        env["PATH"] = str(Path(sys.executable).parent)
        result = subprocess.run(
            [sys.executable, str(HYGIENE), "--warn-only",
             "--tests-dir", str(tmp_path / "tests")],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0, \
            f"hygiene must exit 0 even when pytest is missing:\n{result.stderr}"
