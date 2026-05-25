"""tests/test_workspace_config.py

Tests for _yaml_load / load_workspace error handling and internal_dir resolution.
Covers Invariant 4: fail-closed on exceptions — malformed YAML must not be
silently swallowed.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

import workspace_config
from workspace_config import load_workspace, internal_dir, active_internal_dir


class TestLoadWorkspace:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        """A missing workspace.yaml returns {} without raising."""
        result = load_workspace(tmp_path)
        assert result == {}

    def test_valid_yaml_is_loaded(self, tmp_path):
        """A well-formed workspace.yaml is parsed and returned."""
        ws_yaml = tmp_path / "workspace.yaml"
        ws_yaml.write_text(
            "name: Test\ntype: personal\nstatus: active\nrepos: []\n",
            encoding="utf-8",
        )
        result = load_workspace(tmp_path)
        assert result["name"] == "Test"
        assert result["status"] == "active"

    def test_malformed_yaml_raises_yaml_error(self, tmp_path):
        """Malformed workspace.yaml must raise yaml.YAMLError, not return {}."""
        ws_yaml = tmp_path / "workspace.yaml"
        ws_yaml.write_text("key: [unclosed", encoding="utf-8")
        with pytest.raises(yaml.YAMLError):
            load_workspace(tmp_path)

    def test_malformed_yaml_does_not_return_empty_dict(self, tmp_path):
        """Confirm the silent-swallow path is gone — result must not be {}."""
        ws_yaml = tmp_path / "workspace.yaml"
        ws_yaml.write_text("key: [unclosed", encoding="utf-8")
        raised = False
        try:
            load_workspace(tmp_path)
        except yaml.YAMLError:
            raised = True
        assert raised, "load_workspace returned {} instead of raising yaml.YAMLError"


class TestInternalDir:
    def test_no_docs_path_returns_ws_dir_internal(self, tmp_path):
        """Without docs_path, internal_dir returns ws_dir/internal."""
        ws = {"name": "test", "repos": []}
        result = internal_dir(tmp_path, ws)
        assert result == tmp_path / "internal"

    def test_docs_path_set_returns_resolved_path(self, tmp_path):
        """With docs_path, internal_dir returns the resolved docs_path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        harness_dir = project_dir / ".harness"
        ws = {"name": "test", "repos": [], "docs_path": str(harness_dir)}
        result = internal_dir(tmp_path, ws)
        assert result == harness_dir.resolve()

    def test_docs_path_with_tilde_expands(self, tmp_path):
        """docs_path with ~ is expanded."""
        home = Path.home()
        ws = {"name": "test", "repos": [], "docs_path": "~/.harness"}
        result = internal_dir(tmp_path, ws)
        assert result == (home / ".harness").resolve()

    def test_empty_docs_path_falls_back(self, tmp_path):
        """Empty string docs_path falls back to ws_dir/internal."""
        ws = {"name": "test", "repos": [], "docs_path": ""}
        result = internal_dir(tmp_path, ws)
        assert result == tmp_path / "internal"

    def test_active_internal_dir_no_workspace(self):
        """active_internal_dir returns None when no workspace is active."""
        with patch.object(workspace_config, "active_workspace_dir", return_value=None):
            with patch.object(workspace_config, "active_workspace", return_value=None):
                result = active_internal_dir()
        assert result is None

    def test_active_internal_dir_default(self, tmp_path):
        """active_internal_dir returns ws_dir/internal for workspace without docs_path."""
        ws = {"name": "test", "repos": []}
        with patch.object(workspace_config, "active_workspace_dir", return_value=tmp_path):
            with patch.object(workspace_config, "active_workspace", return_value=ws):
                result = active_internal_dir()
        assert result == tmp_path / "internal"

    def test_active_internal_dir_with_docs_path(self, tmp_path):
        """active_internal_dir returns docs_path when configured."""
        harness_dir = tmp_path / "project" / ".harness"
        ws = {"name": "test", "repos": [], "docs_path": str(harness_dir)}
        with patch.object(workspace_config, "active_workspace_dir", return_value=tmp_path):
            with patch.object(workspace_config, "active_workspace", return_value=ws):
                result = active_internal_dir()
        assert result == harness_dir.resolve()
