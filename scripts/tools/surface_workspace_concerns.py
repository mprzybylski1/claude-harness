#!/usr/bin/env python3
"""
Surface workspace raised concerns for session-start briefing.

Usage:
    surface_workspace_concerns.py [--workspace SLUG]

Reads workspaces/<slug>/raised/*.md (excludes archive/), prints active
(raised/promoted) and newly-terminal (resolved/rejected) items, then moves
terminal items to raised/archive/ so they appear exactly once per session.
Produces no output when the workspace has no raised concerns.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_default_root = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("HARNESS_ROOT", str(_default_root)))

sys.path.insert(0, str(ROOT / "scripts" / "tools"))

_ACTIVE = {"raised", "promoted"}
_TERMINAL = {"resolved", "rejected"}


def _workspace_sessions_md(slug: str) -> Path | None:
    """Resolve <INTERNAL>/sessions.md for a workspace, or None if not found.
    Honors docs_path override in workspace.yaml; falls back to
    workspaces/<slug>/internal/."""
    ws_dir = ROOT / "workspaces" / slug
    yaml_path = ws_dir / "workspace.yaml"
    docs_path = None
    if yaml_path.is_file():
        try:
            import yaml
            cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            docs_path = cfg.get("docs_path")
        except (ImportError, OSError, Exception):
            pass
    internal = Path(docs_path).expanduser().resolve() if docs_path else ws_dir / "internal"
    sessions_md = internal / "sessions.md"
    return sessions_md if sessions_md.is_file() else None


def _current_session(sessions_md: Path | None) -> str | None:
    """Return S<N> for the active session, or None if lookup fails."""
    cmd = [sys.executable, str(ROOT / "scripts" / "tools" / "current_session.py")]
    if sessions_md is not None:
        cmd.extend(["--sessions", str(sessions_md)])
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def _active_workspace_slug() -> str | None:
    """Return workspace slug if CWD is inside workspaces/<slug>/, else None."""
    ws_base = (ROOT / "workspaces").resolve()
    cwd = Path.cwd().resolve()
    try:
        rel = cwd.relative_to(ws_base)
        if rel.parts:
            return rel.parts[0]
    except ValueError:
        pass
    return None


def _parse_frontmatter(path: Path) -> dict:
    """Return frontmatter fields as dict, or {} on any error."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    import yaml
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _format_active(item: dict) -> str:
    sr_id = item.get("id", "SR-???")
    severity = item.get("severity", "?")
    title = item.get("title", "(no title)")
    status = item.get("status", "?")
    ticket = item.get("harness_ticket") or ""
    if status == "promoted" and ticket:
        tag = f"promoted → {ticket}"
    else:
        tag = status
    return f"    {sr_id} ({severity}, {tag}) — {title}"


def _format_terminal(item: dict) -> str:
    sr_id = item.get("id", "SR-???")
    severity = item.get("severity", "?")
    title = item.get("title", "(no title)")
    status = item.get("status", "?")
    resolved_in = item.get("resolved_in") or ""
    suffix = f" in {resolved_in}" if resolved_in else ""
    return f"    {sr_id} ({severity}, {status}{suffix}) — {title}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Surface workspace raised concerns for session-start."
    )
    parser.add_argument(
        "--workspace", metavar="SLUG",
        help="Workspace slug (auto-detected from CWD if omitted)",
    )
    args = parser.parse_args()

    if args.workspace:
        slug = args.workspace
        ws_dir = ROOT / "workspaces" / slug
        if not ws_dir.is_dir():
            print(f"ERROR: workspace '{slug}' not found at {ws_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        slug = _active_workspace_slug()
        if slug is None:
            print(
                "ERROR: no workspace context detected.\n"
                "Run from inside a workspace directory or pass --workspace SLUG.",
                file=sys.stderr,
            )
            sys.exit(1)

    raised_dir = ROOT / "workspaces" / slug / "raised"
    if not raised_dir.is_dir():
        return  # no raised/ dir yet — clean exit, no output

    archive_dir = raised_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    active: list[dict] = []
    terminal: list[tuple[dict, Path]] = []

    for md in sorted(raised_dir.glob("*.md")):
        data = _parse_frontmatter(md)
        if not data:
            continue
        status = data.get("status", "")
        if status in _ACTIVE:
            active.append(data)
        elif status in _TERMINAL:
            terminal.append((data, md))

    if not active and not terminal:
        return

    lines: list[str] = ["Your raised concerns:", ""]

    if active:
        lines.append("  Active:")
        for item in active:
            lines.append(_format_active(item))
        lines.append("")

    resolved = [(d, p) for d, p in terminal if d.get("status") == "resolved"]
    rejected = [(d, p) for d, p in terminal if d.get("status") == "rejected"]

    if resolved:
        lines.append("  Resolved since last session:")
        for item, _ in resolved:
            lines.append(_format_terminal(item))
        lines.append("")

    if rejected:
        lines.append("  Rejected since last session:")
        for item, _ in rejected:
            lines.append(_format_terminal(item))
        lines.append("")

    print("\n".join(lines).rstrip())

    # Archive terminal items after surfacing so they appear exactly once.
    # Stage the moves in git, then auto-commit them in an isolated chore commit
    # (T126 / SR-006). Pathspec limits the commit to the archive moves so any
    # other staged work in the operator's tree is untouched. If anything in the
    # commit pipeline fails (no git identity, signing issue, etc.) we fall back
    # to leaving the moves staged and warning the operator — the same end-state
    # the pre-T126 script produced.
    staged_paths: list[str] = []
    for _, path in terminal:
        dest = archive_dir / path.name
        shutil.move(str(path), str(dest))
        git_result = subprocess.run(
            ["git", "add", "--", str(path), str(dest)],
            cwd=str(ROOT),
            capture_output=True,
            check=False,
        )
        if git_result.returncode != 0:
            detail = git_result.stderr.strip() or git_result.stdout.strip()
            print(
                f"WARNING: failed to stage archive move for {path.name} — "
                f"run 'git add {dest}' manually before session-close. "
                f"git: {detail}",
                file=sys.stderr,
            )
        else:
            staged_paths.extend([str(path), str(dest)])

    if staged_paths:
        session = _current_session(_workspace_sessions_md(slug))
        msg = (
            f"chore: auto-archive resolved SRs {session}" if session
            else "chore: auto-archive resolved SRs"
        )
        commit_result = subprocess.run(
            ["git", "-C", str(ROOT), "commit", "-q", "-m", msg, "--", *staged_paths],
            capture_output=True, text=True, check=False,
        )
        if commit_result.returncode != 0:
            detail = commit_result.stderr.strip() or commit_result.stdout.strip()
            print(
                f"WARNING: auto-commit of archive moves failed — changes remain staged. "
                f"Commit manually:\n"
                f"  git -C {ROOT} commit -m \"{msg}\" -- workspaces/{slug}/raised/\n"
                f"  git: {detail}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
