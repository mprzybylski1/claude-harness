"""Shared session-lookup primitives (T128). Callers wrap with their own None/error policy."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def _root(root: Path | None) -> Path:
    return root if root is not None else Path(os.environ.get("HARNESS_ROOT", str(_DEFAULT_ROOT)))


def resolve_workspace_sessions_md(slug: str, root: Path | None = None) -> Path | None:
    """Return <workspace>/internal/sessions.md (or docs_path override), or None
    when the file does not exist."""
    ws_dir = _root(root) / "workspaces" / slug
    yaml_path = ws_dir / "workspace.yaml"
    docs_path = None
    if yaml_path.is_file():
        try:
            import yaml
            cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            docs_path = cfg.get("docs_path")
        except ImportError as exc:
            print(f"WARNING: PyYAML not available — cannot read docs_path from {yaml_path}: {exc}",
                  file=sys.stderr)
        except OSError as exc:
            print(f"WARNING: could not read {yaml_path}: {exc} — using default internal/",
                  file=sys.stderr)
        except Exception as exc:  # yaml.YAMLError and unexpected parse errors
            print(f"WARNING: could not parse {yaml_path}: {exc} — using default internal/",
                  file=sys.stderr)
    internal = Path(docs_path).expanduser().resolve() if docs_path else ws_dir / "internal"
    sessions_md = internal / "sessions.md"
    return sessions_md if sessions_md.is_file() else None


def call_current_session(sessions_md: Path | None, root: Path | None = None) -> str:
    """Invoke current_session.py, optionally with --sessions PATH. Returns S<N>.
    Raises subprocess.CalledProcessError so callers attach their own exit policy."""
    cmd = [sys.executable, str(_root(root) / "scripts" / "tools" / "current_session.py")]
    if sessions_md is not None:
        cmd.extend(["--sessions", str(sessions_md)])
    return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()
