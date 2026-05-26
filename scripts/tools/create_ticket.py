#!/usr/bin/env python3
"""
Create a new harness ticket with correct frontmatter and scaffolding.

Usage:
    create_ticket.py "Title here" --severity high --phase 2
    create_ticket.py "Title here" --severity medium --ac "AC one" --ac "AC two"
    create_ticket.py "Title here" --workspace scrabble-score

The script auto-picks the next T-number by scanning all open/ and archive/
directories (harness root + workspaces), writes the file, and regenerates INDEX.md.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

_default_root = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("HARNESS_ROOT", str(_default_root)))

sys.path.insert(0, str(ROOT / "scripts" / "tools"))
from workspace_config import load_workspace


def _docs_paths(ws_dir: Path) -> list[Path]:
    try:
        cfg = load_workspace(ws_dir)
    except Exception:
        return []
    if not cfg or not cfg.get("docs_path"):
        return []
    p = Path(cfg["docs_path"]).expanduser()
    return [p] if p.is_dir() else []


def _next_id() -> str:
    """Return the next available T-number by scanning all ticket locations."""
    max_n = 0
    scan_dirs: list[Path] = [
        ROOT / "docs" / "tickets" / "open",
        ROOT / "docs" / "tickets" / "closed",
        ROOT / "docs" / "archive",
    ]
    ws_base = ROOT / "workspaces"
    if ws_base.is_dir():
        for ws_dir in ws_base.iterdir():
            if not ws_dir.is_dir():
                continue
            for internal in [ws_dir / "internal", *_docs_paths(ws_dir)]:
                scan_dirs += [internal / "tickets" / "open", internal / "archive"]

    for d in scan_dirs:
        if not d.is_dir():
            continue
        for p in d.glob("T[0-9]*.md"):
            m = re.match(r"T(\d+)", p.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return f"T{max_n + 1:03d}"


def _slugify(title: str) -> str:
    """Convert title to a filename-safe slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:60]


def _resolve_internal(workspace_slug: str) -> Path:
    """Return the internal docs root for the given workspace slug, or exit 1."""
    ws_dir = ROOT / "workspaces" / workspace_slug
    if not ws_dir.is_dir():
        print(f"ERROR: workspace '{workspace_slug}' not found at {ws_dir}", file=sys.stderr)
        sys.exit(1)
    # Prefer docs_path if configured
    extra = _docs_paths(ws_dir)
    if extra:
        return extra[0]
    internal = ws_dir / "internal"
    if not internal.is_dir():
        print(f"ERROR: workspace internal dir not found at {internal}", file=sys.stderr)
        sys.exit(1)
    return internal


def _current_session(internal: Path | None) -> str:
    cmd = [sys.executable, str(ROOT / "scripts" / "tools" / "current_session.py")]
    if internal is not None:
        cmd += ["--sessions", str(internal / "sessions.md")]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: current_session.py failed: {exc.stderr.strip()}", file=sys.stderr)
        sys.exit(2)


def _regenerate_index(internal: Path | None) -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "tools" / "generate_ticket_index.py")]
    if internal is not None:
        cmd += [
            "--sessions", str(internal / "sessions.md"),
            "--tickets-dir", str(internal / "tickets"),
            "--output", str(internal / "tickets" / "INDEX.md"),
        ]
    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        print(f"WARNING: generate_ticket_index.py failed: {exc}", file=sys.stderr)


_LAYER_VALUES = ("backend", "frontend", "fullstack", "infra", "process", "tooling")

_TEMPLATE = """\
---
id: {ticket_id}
title: {title}
severity: {severity}
status: open
phase: {phase}
layer: {layer}
{repo_line}opened: {session} {today}
closed:
---

## Problem

(Describe the problem here.)

## Acceptance Criteria

{acs}

## Resolution
(Fill in on close.)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new harness ticket.")
    parser.add_argument("title", help="Ticket title")
    parser.add_argument("--severity", choices=["critical", "high", "medium", "low"],
                        default="medium")
    parser.add_argument("--phase", default="2", help="Phase number (default: 2)")
    parser.add_argument("--ac", dest="acs", metavar="TEXT", action="append",
                        help="Acceptance criterion (repeatable)")
    parser.add_argument("--workspace", metavar="SLUG",
                        help="Workspace slug to create ticket in")
    parser.add_argument("--layer", choices=_LAYER_VALUES, default="tooling",
                        help="Layer value for ticket frontmatter (default: tooling)")
    parser.add_argument("--repo", metavar="SLUG",
                        help="Repo slug for workspace ticket frontmatter")
    args = parser.parse_args()

    internal = _resolve_internal(args.workspace) if args.workspace else None

    if internal is not None:
        open_dir = internal / "tickets" / "open"
    else:
        open_dir = ROOT / "docs" / "tickets" / "open"
    open_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(args.title)
    session = _current_session(internal)
    today = date.today().isoformat()

    if args.acs:
        ac_lines = "\n".join(f"- [ ] {ac}" for ac in args.acs)
    else:
        ac_lines = "- [ ] (fill in)"

    repo_line = f"repo: {args.repo}\n" if args.repo else "# repo: <name from workspace.yaml repos list>\n"

    _MAX_RETRIES = 10
    for attempt in range(_MAX_RETRIES):
        ticket_id = _next_id()
        dest = open_dir / f"{ticket_id}-{slug}.md"
        content = _TEMPLATE.format(
            ticket_id=ticket_id,
            title=args.title,
            severity=args.severity,
            phase=args.phase,
            layer=args.layer,
            repo_line=repo_line,
            session=session,
            today=today,
            acs=ac_lines,
        )
        try:
            with open(dest, "x", encoding="utf-8") as fh:
                fh.write(content)
            break
        except FileExistsError:
            if attempt == _MAX_RETRIES - 1:
                print(f"ERROR: could not allocate ticket ID after {_MAX_RETRIES} attempts", file=sys.stderr)
                sys.exit(1)

    _regenerate_index(internal)
    print(dest)


if __name__ == "__main__":
    main()
