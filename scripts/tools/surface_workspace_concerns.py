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
    # Stage the moves in git when possible so session-close picks them up
    # instead of leaving an uncommitted delete+add pair lying around.
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


if __name__ == "__main__":
    main()
