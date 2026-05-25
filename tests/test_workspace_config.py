"""tests/test_workspace_config.py

Tests for _yaml_load / load_workspace error handling in workspace_config.py.
Covers Invariant 4: fail-closed on exceptions — malformed YAML must not be
silently swallowed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

from workspace_config import load_workspace


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
