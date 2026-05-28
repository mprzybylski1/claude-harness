"""Unit tests for scripts/tools/session_lookup.py (T128 implementation review)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_STUB_SESSION = "print('S5')\n"


def _setup(tmp_path: Path, slug: str = "myws") -> Path:
    """Minimal harness with stub current_session.py. Returns harness root."""
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text(_STUB_SESSION, encoding="utf-8")
    (tmp_path / "workspaces" / slug).mkdir(parents=True)
    return tmp_path


def _import_module(harness: Path):
    """Import session_lookup from the harness's scripts/tools/ using HARNESS_ROOT."""
    import importlib
    import os
    import types

    # Put the real scripts/tools on the path so we pick up session_lookup.py.
    src_dir = str(ROOT / "scripts" / "tools")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Patch env for HARNESS_ROOT so the module resolves paths into tmp_path.
    old = os.environ.get("HARNESS_ROOT")
    os.environ["HARNESS_ROOT"] = str(harness)
    try:
        import importlib
        if "session_lookup" in sys.modules:
            del sys.modules["session_lookup"]
        mod = importlib.import_module("session_lookup")
        # Reload so _DEFAULT_ROOT captures the overridden HARNESS_ROOT.
        mod = importlib.reload(mod)
        return mod
    finally:
        if old is None:
            os.environ.pop("HARNESS_ROOT", None)
        else:
            os.environ["HARNESS_ROOT"] = old


class TestResolveWorkspaceSessionsMd:

    def test_returns_none_when_sessions_md_absent(self, tmp_path):
        """When workspace has no internal/sessions.md, returns None."""
        harness = _setup(tmp_path)
        mod = _import_module(harness)
        result = mod.resolve_workspace_sessions_md("myws", root=harness)
        assert result is None

    def test_returns_path_when_sessions_md_exists(self, tmp_path):
        """Returns the Path when internal/sessions.md exists."""
        harness = _setup(tmp_path)
        internal = harness / "workspaces" / "myws" / "internal"
        internal.mkdir(parents=True)
        sessions = internal / "sessions.md"
        sessions.write_text("## Session Log\n\nS5 2026-05-28: init\n", encoding="utf-8")
        mod = _import_module(harness)
        result = mod.resolve_workspace_sessions_md("myws", root=harness)
        assert result == sessions

    def test_honours_docs_path_override(self, tmp_path):
        """docs_path in workspace.yaml overrides the internal/ default."""
        import yaml
        harness = _setup(tmp_path)
        custom_docs = tmp_path / "custom"
        custom_docs.mkdir()
        sessions = custom_docs / "sessions.md"
        sessions.write_text("## Session Log\n\nS7 2026-05-28: custom\n", encoding="utf-8")
        ws_dir = harness / "workspaces" / "myws"
        (ws_dir / "workspace.yaml").write_text(
            yaml.dump({"docs_path": str(custom_docs)}), encoding="utf-8"
        )
        mod = _import_module(harness)
        result = mod.resolve_workspace_sessions_md("myws", root=harness)
        assert result == sessions

    def test_yaml_exception_warns_and_falls_back_to_internal(self, tmp_path, capsys):
        """Malformed workspace.yaml warns to stderr and falls back to internal/."""
        harness = _setup(tmp_path)
        ws_dir = harness / "workspaces" / "myws"
        (ws_dir / "workspace.yaml").write_text("docs_path: [\n  bad yaml", encoding="utf-8")
        # No sessions.md in internal/ — should return None after fallback.
        mod = _import_module(harness)
        result = mod.resolve_workspace_sessions_md("myws", root=harness)
        assert result is None
        assert "WARNING" in capsys.readouterr().err


class TestCallCurrentSession:

    def test_returns_session_without_sessions_md(self, tmp_path):
        """call_current_session(None) invokes current_session.py without --sessions."""
        harness = _setup(tmp_path)
        mod = _import_module(harness)
        result = mod.call_current_session(None, root=harness)
        assert result == "S5"

    def test_passes_sessions_flag_when_path_given(self, tmp_path):
        """call_current_session(path) passes --sessions PATH to current_session.py."""
        harness = _setup(tmp_path)
        # Stub that echoes S9 when --sessions is present.
        (harness / "scripts" / "tools" / "current_session.py").write_text(
            "import sys\n"
            "print('S9') if '--sessions' in sys.argv else print('S1')\n",
            encoding="utf-8",
        )
        mod = _import_module(harness)
        sessions_md = harness / "workspaces" / "myws" / "internal" / "sessions.md"
        sessions_md.parent.mkdir(parents=True, exist_ok=True)
        sessions_md.write_text("## Session Log\n\nS9 2026-05-28: ws\n", encoding="utf-8")
        result = mod.call_current_session(sessions_md, root=harness)
        assert result == "S9"

    def test_raises_on_nonzero_exit(self, tmp_path):
        """CalledProcessError is raised when current_session.py exits non-zero."""
        harness = _setup(tmp_path)
        (harness / "scripts" / "tools" / "current_session.py").write_text(
            "import sys; sys.exit(2)\n", encoding="utf-8"
        )
        mod = _import_module(harness)
        try:
            mod.call_current_session(None, root=harness)
            assert False, "Expected CalledProcessError"
        except subprocess.CalledProcessError:
            pass
