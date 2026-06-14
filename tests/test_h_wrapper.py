"""
Tests for T146: the scripts/h wrapper dispatches harness tools from any cwd.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "scripts" / "h"


def _run(cwd, args, env=None):
    return subprocess.run(
        ["bash", str(H), *args], cwd=str(cwd), capture_output=True, text=True,
        env=env if env is not None else os.environ.copy(),
    )


def test_dispatches_from_unrelated_cwd(tmp_path):
    """h close_ticket --help works from a cwd that is not the harness root."""
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)  # force the script-location fallback
    result = _run(tmp_path, ["close_ticket", "--help"], env=env)
    assert result.returncode == 0, result.stderr
    assert "close_ticket.py" in result.stdout


def test_strips_py_suffix(tmp_path):
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    result = _run(tmp_path, ["close_ticket.py", "--help"], env=env)
    assert result.returncode == 0, result.stderr


def test_unknown_tool_errors(tmp_path):
    result = _run(tmp_path, ["definitely_not_a_tool"])
    assert result.returncode == 2
    assert "no such tool" in result.stderr.lower()


def test_no_args_usage(tmp_path):
    result = _run(tmp_path, [])
    assert result.returncode == 2
    assert "usage" in result.stderr.lower()
