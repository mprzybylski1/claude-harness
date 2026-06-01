"""Tests for T150: machine-specific path detection in workspace.py and repo_hygiene.py."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_CONFIG = ROOT / "scripts" / "tools" / "workspace_config.py"
WORKSPACE_PY = ROOT / "scripts" / "tools" / "workspace.py"
HYGIENE = ROOT / "scripts" / "tools" / "repo_hygiene.py"


def _load_workspace_config():
    spec = importlib.util.spec_from_file_location("workspace_config", WORKSPACE_CONFIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestIsMachineSpecificPath:
    """Unit tests for the shared detector."""

    @pytest.fixture()
    def detector(self):
        return _load_workspace_config().is_machine_specific_path

    @pytest.mark.parametrize("raw", [
        "/Users/mprzybylski/Projects/app",
        "/Users/someone/code",
        "/home/ubuntu/app",
        "/home/ci/project",
        "/mnt/c/Users/dev/code",
        "/Volumes/External/repo",
        "C:\\Users\\dev\\code",
        "D:/Projects/app",
    ])
    def test_detects_machine_specific(self, detector, raw):
        assert detector(raw) is True, f"Expected True for {raw!r}"

    @pytest.mark.parametrize("raw", [
        "~/Projects/app",
        "~/Documents/code",
        "./relative/path",
        "relative/path",
        "",
    ])
    def test_allows_portable(self, detector, raw):
        assert detector(raw) is False, f"Expected False for {raw!r}"


class TestRepoHygieneWorkspacePaths:
    """Integration tests for the workspace path check in repo_hygiene.py."""

    def _load_hygiene(self):
        spec = importlib.util.spec_from_file_location("repo_hygiene", HYGIENE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_detects_machine_specific_repo_path(self, tmp_path, monkeypatch):
        ws_dir = tmp_path / "workspaces" / "bad-ws"
        ws_dir.mkdir(parents=True)
        (ws_dir / "workspace.yaml").write_text(
            "name: Bad\ntype: personal\nstatus: active\n"
            "repos:\n- name: app\n  path: /Users/someone/app\n  role: primary\n",
            encoding="utf-8",
        )

        mod = self._load_hygiene()
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import workspace_config as wc
        original_root = wc._ROOT
        monkeypatch.setattr(wc, "_ROOT", tmp_path)
        try:
            findings = mod.check_workspace_paths()
        finally:
            monkeypatch.setattr(wc, "_ROOT", original_root)
        assert len(findings) == 1
        assert findings[0].category == "machine-specific-path"
        assert "/Users/someone/app" in findings[0].detail

    def test_detects_machine_specific_docs_path(self, tmp_path, monkeypatch):
        ws_dir = tmp_path / "workspaces" / "bad-ws"
        ws_dir.mkdir(parents=True)
        (ws_dir / "workspace.yaml").write_text(
            "name: Bad\ntype: personal\nstatus: active\n"
            "repos:\n- name: app\n  path: ~/app\n  role: primary\n"
            "docs_path: /home/user/app/.harness\n",
            encoding="utf-8",
        )

        mod = self._load_hygiene()
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import workspace_config as wc
        original_root = wc._ROOT
        monkeypatch.setattr(wc, "_ROOT", tmp_path)
        try:
            findings = mod.check_workspace_paths()
        finally:
            monkeypatch.setattr(wc, "_ROOT", original_root)
        assert len(findings) == 1
        assert findings[0].category == "machine-specific-path"
        assert "/home/user/app/.harness" in findings[0].detail

    def test_clean_paths_produce_no_findings(self, tmp_path, monkeypatch):
        ws_dir = tmp_path / "workspaces" / "good-ws"
        ws_dir.mkdir(parents=True)
        (ws_dir / "workspace.yaml").write_text(
            "name: Good\ntype: personal\nstatus: active\n"
            "repos:\n- name: app\n  path: ~/Projects/app\n  role: primary\n",
            encoding="utf-8",
        )

        mod = self._load_hygiene()
        monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import workspace_config as wc
        original_root = wc._ROOT
        monkeypatch.setattr(wc, "_ROOT", tmp_path)
        try:
            findings = mod.check_workspace_paths()
        finally:
            monkeypatch.setattr(wc, "_ROOT", original_root)
        assert findings == []

    def test_real_harness_still_clean(self):
        result = subprocess.run(
            [sys.executable, str(HYGIENE), "--warn-only"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "machine-specific-path" not in result.stdout, \
            f"Live harness has machine-specific paths:\n{result.stdout}"


class TestPortablePath:
    """Unit tests for the home-collapse helper."""

    @pytest.fixture()
    def fn(self):
        return _load_workspace_config().portable_path

    def test_collapses_home_prefix(self, fn):
        home = str(Path.home())
        result = fn(Path(home) / "Projects" / "app")
        assert result == "~/Projects/app"

    def test_leaves_non_home_path_unchanged(self, fn):
        result = fn(Path("/opt/repos/app"))
        assert result == "/opt/repos/app"

    def test_home_itself(self, fn):
        result = fn(Path.home())
        assert result == "~"


class TestCmdCreateWarning:
    """Test that workspace.py create warns on machine-specific paths and stores portable form."""

    def test_warns_on_machine_specific_repo_path(self, tmp_path, capsys):
        ws_base = tmp_path / "workspaces"
        ws_base.mkdir()
        repo_dir = tmp_path / "myapp"
        repo_dir.mkdir()

        inputs = iter([
            "Test App",          # name
            "personal",          # type
            "app",               # repo name
            "/Users/someone/myapp",  # repo path (machine-specific)
            "",                  # finish repos
            "",                  # docs path (blank)
        ])

        spec = importlib.util.spec_from_file_location("workspace", WORKSPACE_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with mock.patch.object(mod, "_workspaces_base", return_value=ws_base), \
             mock.patch("builtins.input", lambda _: next(inputs)):
            ns = mock.Mock()
            ns.slug = "test-app"
            mod.cmd_create(ns)

        captured = capsys.readouterr()
        assert "machine-specific absolute path" in captured.out
        assert "~/..." in captured.out

    def test_no_warning_on_tilde_repo_path(self, tmp_path, capsys):
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
            ns.slug = "test-app2"
            mod.cmd_create(ns)

        captured = capsys.readouterr()
        assert "machine-specific absolute path" not in captured.out

    def test_stores_portable_repo_path(self, tmp_path):
        ws_base = tmp_path / "workspaces"
        ws_base.mkdir()
        home = str(Path.home())

        inputs = iter([
            "Test App",
            "personal",
            "app",
            f"{home}/myapp",
            "",
            "",
        ])

        spec = importlib.util.spec_from_file_location("workspace", WORKSPACE_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with mock.patch.object(mod, "_workspaces_base", return_value=ws_base), \
             mock.patch("builtins.input", lambda _: next(inputs)):
            ns = mock.Mock()
            ns.slug = "test-app3"
            mod.cmd_create(ns)

        ws_yaml = ws_base / "test-app3" / "workspace.yaml"
        cfg = yaml.safe_load(ws_yaml.read_text())
        stored = cfg["repos"][0]["path"]
        assert stored.startswith("~/"), f"Expected ~/... but got: {stored}"
        assert not stored.startswith(home), f"Path should not start with {home}"
