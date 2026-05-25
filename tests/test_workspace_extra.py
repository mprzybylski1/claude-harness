"""Additional workspace tests covering findings #15, #17, #18 from Opus review."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

from workspace_config import is_within_workspace, assert_workspace_boundary


# ── Finding #15: symlink traversal ────────────────────────────────────────────

class TestSymlinkTraversal:
    def test_symlink_pointing_outside_workspace_is_blocked(self, tmp_path):
        """A symlink whose resolved target escapes the workspace boundary must be blocked."""
        outside = tmp_path / "outside"
        outside.mkdir()

        repo = tmp_path / "repo"
        repo.mkdir()
        link = repo / "escape_link"
        link.symlink_to(outside)

        workspace = {"name": "test", "repos": [{"path": str(repo)}]}
        assert not is_within_workspace(link, workspace)

    def test_symlink_within_workspace_is_allowed(self, tmp_path):
        """A symlink whose resolved target stays inside the workspace is allowed."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subdir = repo / "sub"
        subdir.mkdir()
        link = repo / "link_to_sub"
        link.symlink_to(subdir)

        workspace = {"name": "test", "repos": [{"path": str(repo)}]}
        assert is_within_workspace(link, workspace)

    def test_assert_boundary_raises_on_symlink_escape(self, tmp_path):
        """assert_workspace_boundary must exit(2) when symlink target is outside."""
        outside = tmp_path / "outside"
        outside.mkdir()

        repo = tmp_path / "repo"
        repo.mkdir()
        link = repo / "escape"
        link.symlink_to(outside)

        workspace = {"name": "test", "repos": [{"path": str(repo)}]}
        with pytest.raises(SystemExit) as exc_info:
            assert_workspace_boundary(link, workspace)
        assert exc_info.value.code == 2


# ── Finding #17: .gitignore coverage ─────────────────────────────────────────

class TestGitignore:
    """Verify that workspaces/*/internal/ and workspaces/*/client/ are gitignored."""

    def _gitignore_lines(self) -> list[str]:
        gi = ROOT / ".gitignore"
        assert gi.exists(), ".gitignore not found at repo root"
        return [line.rstrip() for line in gi.read_text().splitlines()]

    def test_workspace_internal_is_gitignored(self):
        lines = self._gitignore_lines()
        assert any("workspaces/*/internal/" in line or "workspaces/**/internal" in line
                   for line in lines), \
            "workspaces/*/internal/ must be in .gitignore"

    def test_workspace_client_is_gitignored(self):
        lines = self._gitignore_lines()
        assert any("workspaces/*/client/" in line or "workspaces/**/client" in line
                   for line in lines), \
            "workspaces/*/client/ must be in .gitignore"

    def test_workspace_archive_is_gitignored(self):
        lines = self._gitignore_lines()
        assert any("workspaces/archive/" in line for line in lines), \
            "workspaces/archive/ must be in .gitignore"


# ── Finding #18: portfolio.py and run_static_analysis.py ─────────────────────

class TestPortfolioMetadataOnly:
    """portfolio.py must only read metadata, never ticket bodies or session content."""

    def _build_workspace(self, ws_base: Path, slug: str, ticket_body: str = "") -> Path:
        ws = ws_base / slug
        open_dir = ws / "internal" / "tickets" / "open"
        open_dir.mkdir(parents=True)
        sessions = ws / "internal" / "sessions.md"
        sessions.write_text("# Sessions\n\nS1 2026-01-01: first session\n", encoding="utf-8")
        ws_yaml = ws / "workspace.yaml"
        ws_yaml.write_text(
            "name: Test WS\ntype: personal\nstatus: active\nopened: 2026-01-01\nrepos: []\n",
            encoding="utf-8",
        )
        ticket = open_dir / "T001-sample.md"
        ticket.write_text(
            "---\nid: T001\ntitle: Sample\nseverity: high\n---\n\n"
            + (ticket_body or "Ticket body content."),
            encoding="utf-8",
        )
        return ws

    def test_portfolio_counts_tickets_by_severity(self, tmp_path, monkeypatch):
        import harness_config as _hc
        monkeypatch.chdir(ROOT)
        ws_base = tmp_path / "workspaces"
        ws_base.mkdir()
        monkeypatch.setattr(_hc, "workspaces_dir", lambda: str(ws_base.relative_to(ROOT)) if ws_base.is_relative_to(ROOT) else str(ws_base))

        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import importlib
        import portfolio
        importlib.reload(portfolio)

        monkeypatch.setattr(portfolio, "_workspaces_base", lambda: ws_base)

        self._build_workspace(ws_base, "acme")

        rows = []
        for ws_dir in sorted(ws_base.iterdir()):
            if not ws_dir.is_dir():
                continue
            counts = portfolio._ticket_counts(ws_dir / "internal" / "tickets" / "open")
            rows.append(counts)

        assert rows == [{"high": 1}]

    def test_portfolio_counts_unknown_severity_as_other(self, tmp_path):
        ws_base = tmp_path / "workspaces"
        open_dir = ws_base / "acme" / "internal" / "tickets" / "open"
        open_dir.mkdir(parents=True)
        ticket = open_dir / "T001-bad.md"
        ticket.write_text("---\nid: T001\nseverity: INVALID\n---\n\nBody.\n", encoding="utf-8")

        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import portfolio
        counts = portfolio._ticket_counts(open_dir)
        assert counts == {"other": 1}

    def test_portfolio_skips_no_severity(self, tmp_path):
        open_dir = tmp_path / "open"
        open_dir.mkdir()
        ticket = open_dir / "T001-nosev.md"
        ticket.write_text("---\nid: T001\ntitle: No sev\n---\n\nBody.\n", encoding="utf-8")

        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import portfolio
        counts = portfolio._ticket_counts(open_dir)
        assert counts == {}

    def test_yaml_get_reads_frontmatter_only(self, tmp_path):
        """_yaml_get must not match 'severity: high' in ticket body, only in frontmatter."""
        ticket = tmp_path / "T001.md"
        ticket.write_text(
            "---\nid: T001\nseverity: low\n---\n\n# Body\n\nseverity: critical\n",
            encoding="utf-8",
        )
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import portfolio
        sev = portfolio._yaml_get(ticket, "severity")
        assert sev == "low", f"Expected 'low' from frontmatter, got {sev!r}"


class TestRunStaticAnalysisWorkspaceMode:
    """run_static_analysis.py should call assert_workspace_boundary for each repo."""

    def test_harness_root_runs_without_workspace(self, monkeypatch):
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import run_static_analysis
        import workspace_config

        monkeypatch.setattr(workspace_config, "active_workspace", lambda: None)

        results = run_static_analysis._run_checks_for_repo(ROOT, "harness")
        assert isinstance(results, list)

    def test_workspace_mode_calls_boundary_check(self, tmp_path, monkeypatch, capsys):
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import run_static_analysis
        import workspace_config

        repo = tmp_path / "repo"
        repo.mkdir()
        workspace = {
            "name": "test",
            "repos": [{"name": "backend", "path": str(repo), "role": "primary"}],
        }

        boundary_calls = []

        def fake_boundary(path, ws):
            boundary_calls.append(path)

        monkeypatch.setattr(workspace_config, "active_workspace", lambda: workspace)
        monkeypatch.setattr(workspace_config, "assert_workspace_boundary", fake_boundary)
        monkeypatch.setattr(workspace_config, "primary_repo", lambda ws: repo)
        monkeypatch.setattr(workspace_config, "secondary_repos", lambda ws: [])

        run_static_analysis.main()
        assert any(str(repo) in str(c) for c in boundary_calls), \
            "assert_workspace_boundary was not called for the workspace repo"
