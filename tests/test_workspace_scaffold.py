"""Tests for T151: workspace scaffold produces tool-compatible sessions.md and INDEX.md."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_PY = ROOT / "scripts" / "tools" / "workspace.py"
EXTRACT_BRIEF = ROOT / "scripts" / "tools" / "extract_session_brief.py"
CURRENT_SESSION = ROOT / "scripts" / "tools" / "current_session.py"


def _create_workspace(tmp_path: Path) -> Path:
    """Run cmd_create in a temp dir and return the workspace docs dir."""
    ws_base = tmp_path / "workspaces"
    ws_base.mkdir()

    inputs = iter([
        "Test App",
        "personal",
        "app",
        "~/myapp",
        "",
        "",
    ])

    spec = importlib.util.spec_from_file_location("workspace", WORKSPACE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with mock.patch.object(mod, "_workspaces_base", return_value=ws_base), \
         mock.patch("builtins.input", lambda _: next(inputs)):
        ns = mock.Mock()
        ns.slug = "test-app"
        mod.cmd_create(ns)

    return ws_base / "test-app" / "internal"


class TestSessionsScaffold:
    """sessions.md from scaffold must work with extract_session_brief and current_session."""

    def test_extract_session_brief_succeeds(self, tmp_path):
        docs = _create_workspace(tmp_path)
        sessions = docs / "sessions.md"
        assert sessions.exists()

        result = subprocess.run(
            [sys.executable, str(EXTRACT_BRIEF), "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"extract_session_brief failed:\n{result.stderr}"
        assert "Current Phase & Status" in result.stdout
        assert "Active Work" in result.stdout
        assert "Session Log" in result.stdout

    def test_current_session_returns_s1(self, tmp_path):
        docs = _create_workspace(tmp_path)
        sessions = docs / "sessions.md"

        result = subprocess.run(
            [sys.executable, str(CURRENT_SESSION), "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"current_session failed:\n{result.stderr}"
        assert result.stdout.strip() == "S1"

    def test_sessions_has_required_sections(self, tmp_path):
        docs = _create_workspace(tmp_path)
        content = (docs / "sessions.md").read_text()
        assert "## Current Phase & Status" in content
        assert "## Active Work" in content
        assert "## Session Log" in content

    def test_sessions_has_s0_entry(self, tmp_path):
        docs = _create_workspace(tmp_path)
        content = (docs / "sessions.md").read_text()
        assert "S0 " in content
        assert "workspace created" in content


class TestIndexScaffold:
    """INDEX.md from scaffold must match generate_ticket_index.py format."""

    def test_index_has_severity_sections(self, tmp_path):
        docs = _create_workspace(tmp_path)
        content = (docs / "tickets" / "INDEX.md").read_text()
        for sev in ["Critical", "High", "Medium", "Low", "Unknown"]:
            assert f"## {sev} (0)" in content

    def test_index_has_aging_section(self, tmp_path):
        docs = _create_workspace(tmp_path)
        content = (docs / "tickets" / "INDEX.md").read_text()
        assert "## Aging Tickets" in content

    def test_index_has_regenerate_hint(self, tmp_path):
        docs = _create_workspace(tmp_path)
        content = (docs / "tickets" / "INDEX.md").read_text()
        assert "Re-generate:" in content

    def test_index_matches_generator_output(self, tmp_path):
        """Scaffold INDEX must match render_index([], 0, today) byte-for-byte."""
        docs = _create_workspace(tmp_path)
        scaffold_content = (docs / "tickets" / "INDEX.md").read_text()

        spec = importlib.util.spec_from_file_location(
            "gti", ROOT / "scripts" / "tools" / "generate_ticket_index.py"
        )
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        spec.loader.exec_module(mod)

        from datetime import date
        expected = mod.render_index([], 0, date.today().isoformat())
        assert scaffold_content == expected, (
            f"Scaffold INDEX differs from generator output.\n"
            f"Scaffold:\n{scaffold_content!r}\n\nGenerator:\n{expected!r}"
        )
