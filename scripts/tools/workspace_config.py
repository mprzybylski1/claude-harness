"""workspace_config.py — Load workspace context and enforce isolation boundaries.

Workspaces live under HARNESS_ROOT/workspaces/<slug>/ and are declared in workspace.yaml.
Scripts that read repo content must call assert_workspace_boundary() before accessing
any file outside the harness root — this is the isolation guarantee.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _yaml_load(path: Path) -> dict:
    import yaml
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (FileNotFoundError, OSError):
        return {}
    except yaml.YAMLError:
        raise


# ── Directory helpers ─────────────────────────────────────────────────────────

def workspaces_base() -> Path:
    """Return the absolute path to the workspaces/ directory."""
    import harness_config as _hc
    return (_ROOT / _hc.workspaces_dir()).resolve()


def workspace_dir(slug: str) -> Path:
    return workspaces_base() / slug


# ── Internal docs directory ───────────────────────────────────────────────────

def internal_dir(ws_dir: Path, ws: dict) -> Path:
    """Return the docs root for a workspace.

    Returns the resolved docs_path from workspace.yaml if configured, otherwise
    falls back to ws_dir/internal (the harness-local default).
    """
    docs_path = ws.get("docs_path")
    if docs_path:
        return Path(docs_path).expanduser().resolve()
    return ws_dir / "internal"


def active_internal_dir() -> Path | None:
    """Return the internal docs dir for the active workspace, or None.

    Exits 2 when docs_path is configured but the directory does not exist —
    a missing docs_path silently produces empty results everywhere that reads
    from it, so we fail loudly here instead.
    """
    ws_dir = active_workspace_dir()
    ws = active_workspace()
    if ws_dir is not None and ws is not None:
        result = internal_dir(ws_dir, ws)
        if ws.get("docs_path") and not result.is_dir():
            print(
                f"Error: workspace docs_path directory does not exist: {result}\n"
                f"Restore the directory or update docs_path in "
                f"{ws_dir}/workspace.yaml to fix this.",
                file=sys.stderr,
            )
            sys.exit(2)
        return result
    return None


# ── Loading ───────────────────────────────────────────────────────────────────

def load_workspace(ws_dir: Path) -> dict:
    """Load workspace.yaml from a workspace directory. Returns {} if missing."""
    return _yaml_load(ws_dir / "workspace.yaml")


def active_workspace_dir() -> Path | None:
    """Return the workspace directory if CWD is at or inside a workspace.

    Detection: checks whether CWD is a subdirectory of workspaces_base().
    Returns the top-level workspace dir (e.g. workspaces/client-acme/).
    """
    ws_base = workspaces_base()
    cwd = Path.cwd().resolve()
    try:
        rel = cwd.relative_to(ws_base)
        parts = rel.parts
        if parts:
            return ws_base / parts[0]
    except ValueError:
        pass
    return None


def active_workspace() -> dict | None:
    """Return the active workspace config dict, or None if not in a workspace."""
    ws_dir = active_workspace_dir()
    if ws_dir is None:
        return None
    cfg = load_workspace(ws_dir)
    return cfg if cfg else None


def list_active_workspaces() -> list[tuple[str, dict]]:
    """Return [(slug, config), ...] for all non-archived workspaces."""
    ws_base = workspaces_base()
    if not ws_base.exists():
        return []
    results = []
    for ws_dir in sorted(ws_base.iterdir()):
        if not ws_dir.is_dir() or ws_dir.name == "archive":
            continue
        cfg = load_workspace(ws_dir)
        if not cfg:
            continue
        if cfg.get("status") == "archived":
            continue
        results.append((ws_dir.name, cfg))
    return results


# ── Repo accessors ────────────────────────────────────────────────────────────

def client_remote(workspace: dict) -> str | None:
    """Return the client git remote URL, or None if not configured."""
    return workspace.get("client_remote") or None


def all_repos(workspace: dict) -> list[dict]:
    """Return the repos list from a workspace config."""
    return workspace.get("repos", [])


def primary_repo(workspace: dict) -> Path | None:
    """Return the absolute path of the primary repo, or None."""
    for repo in all_repos(workspace):
        if repo.get("role") == "primary":
            return Path(repo["path"]).expanduser().resolve()
    repos = all_repos(workspace)
    if repos:
        return Path(repos[0]["path"]).expanduser().resolve()
    return None


def secondary_repos(workspace: dict) -> list[Path]:
    """Return absolute paths of all secondary repos."""
    return [
        Path(r["path"]).expanduser().resolve()
        for r in all_repos(workspace)
        if r.get("role") != "primary"
    ]


# ── Isolation enforcement (T005) ──────────────────────────────────────────────

def _repo_roots(workspace: dict) -> list[Path]:
    return [Path(r["path"]).expanduser().resolve() for r in all_repos(workspace)]


def is_within_workspace(path: Path, workspace: dict) -> bool:
    """Return True if path is inside any declared repo in the workspace."""
    resolved = Path(path).expanduser().resolve()
    for root in _repo_roots(workspace):
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def assert_workspace_boundary(path: Path, workspace: dict) -> None:
    """Hard-exit with a clear message if path escapes the workspace boundary.

    Call this before reading any repo file from a script that is workspace-scoped.
    Prevents cross-workspace data leakage — scripts must only read repos they declare.
    """
    if not is_within_workspace(path, workspace):
        roots = [str(r) for r in _repo_roots(workspace)]
        ws_name = workspace.get("name", "?")
        print(
            f"\n[WORKSPACE ISOLATION VIOLATION]\n"
            f"  Attempted to access: {path}\n"
            f"  Workspace '{ws_name}' declares repos:\n"
            + "".join(f"    - {r}\n" for r in roots)
            + "  Access denied — path is outside all declared repos.\n",
            file=sys.stderr,
        )
        sys.exit(2)
