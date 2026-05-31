#!/usr/bin/env python3
"""
Create a new harness ticket with correct frontmatter and scaffolding.

Usage:
    create_ticket.py "Title here" --severity high --phase 2
    create_ticket.py "Title here" --severity medium --ac "AC one" --ac "AC two"
    create_ticket.py "Title here" --problem "What went wrong." --ac "Fixed it"
    create_ticket.py "Title here" --workspace scrabble-score

Layer selection (T140):
    --workspace SLUG  → that workspace's layer (explicit)
    --harness         → harness layer (explicit; for programmatic callers)
    (neither)         → consult .claude/.active_workspace: harness session uses the
                        harness layer; a workspace or undeclared session fails closed
                        (never silently creates a harness ticket from a workspace session)

The script auto-picks the next T-number scoped to the target layer (the chosen
workspace's own sequence, or the harness sequence otherwise), writes the file,
and regenerates INDEX.md.
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
import session_lookup
from workspace_config import (
    STATE_HARNESS,
    STATE_UNDECLARED,
    STATE_WORKSPACE,
    load_workspace,
    read_session_state,
)


def _docs_paths(ws_dir: Path) -> list[Path]:
    try:
        cfg = load_workspace(ws_dir)
    except Exception:
        return []
    if not cfg or not cfg.get("docs_path"):
        return []
    p = Path(cfg["docs_path"]).expanduser()
    return [p] if p.is_dir() else []


def _next_id(internal: Path | None) -> str:
    """Return the next T-number scoped to the target layer ONLY.

    The counter is per-layer: a workspace ticket continues that workspace's own
    sequence, and a harness ticket continues the harness sequence — neither sees
    the other (T135 / SR-008). Mixing them produced harness-global numbers for
    workspace tickets (e.g. a workspace at T018 getting T135), breaking the
    "T-number = this layer's Nth ticket" model. This mirrors how
    current_session.py --sessions PATH scopes the session counter per layer.

    internal=None  → harness layer (docs/tickets/{open,closed} + docs/archive)
    internal=<dir> → that workspace's layer (tickets/{open,closed} + archive)
    """
    if internal is not None:
        scan_dirs = [
            internal / "tickets" / "open",
            internal / "tickets" / "closed",
            internal / "archive",
        ]
    else:
        scan_dirs = [
            ROOT / "docs" / "tickets" / "open",
            ROOT / "docs" / "tickets" / "closed",
            ROOT / "docs" / "archive",
        ]

    max_n = 0
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


def _resolve_bare_layer() -> None:
    """Decide the target layer for a bare invocation (no --workspace).

    Consults the session-declared layer in .claude/.active_workspace and fails
    closed unless this is a harness session — a bare invocation must never silently
    create a HARNESS ticket from a workspace or undeclared session (T140; mirrors
    generate_ticket_index.py's T136 behavior and check_cross_layer_writes). Returns
    None (the harness layer) only for a declared harness session; otherwise exits 2.

    create_ticket writes via plain `open()`, so the PreToolUse cross-layer hook —
    which fires on Edit/Write only — cannot catch a misrouted ticket here; the tool
    itself has to be session-aware.
    """
    state, slug = read_session_state(ROOT)
    if state == STATE_WORKSPACE:
        print(
            f"ERROR (T140): active session is workspace '{slug}', but no --workspace "
            f"was given — refusing to create a harness ticket from a workspace session.\n"
            f"  Create the ticket in your workspace with:\n"
            f"    python scripts/tools/create_ticket.py \"<title>\" --workspace {slug}",
            file=sys.stderr,
        )
        sys.exit(2)
    if state == STATE_UNDECLARED:
        print(
            "ERROR (T140): session type undeclared (.claude/.active_workspace is "
            "missing or empty) — refusing to create a ticket by default.\n"
            "  Run /session-start to declare the session, or pass --workspace SLUG.",
            file=sys.stderr,
        )
        sys.exit(2)
    # state == STATE_HARNESS → harness layer (current behavior).
    return None


def _current_session(internal: Path | None) -> str:
    sessions_md = (internal / "sessions.md") if internal is not None else None
    try:
        return session_lookup.call_current_session(sessions_md, root=ROOT)
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


_PROBLEM_PLACEHOLDER = "(Describe the problem here.)"


def _apply_problem(content: str, problem_text: str) -> str:
    """Replace the '(Describe the problem here.)' placeholder in ## Problem."""
    if _PROBLEM_PLACEHOLDER not in content:
        print(
            f"ERROR: --problem passed but the template placeholder "
            f"'{_PROBLEM_PLACEHOLDER}' was not found in the ticket body — "
            "problem text was not applied",
            file=sys.stderr,
        )
        sys.exit(1)
    return content.replace(_PROBLEM_PLACEHOLDER, problem_text)


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
    layer_group = parser.add_mutually_exclusive_group()
    layer_group.add_argument("--workspace", metavar="SLUG",
                             help="Workspace slug to create ticket in")
    layer_group.add_argument("--harness", action="store_true",
                             help="Force the harness layer, bypassing the session-state "
                                  "check (for programmatic harness operations like "
                                  "promote_raised_concern.py — T140)")
    parser.add_argument("--problem", metavar="TEXT",
                        help="Problem description — replaces the placeholder in ## Problem")
    parser.add_argument("--layer", choices=_LAYER_VALUES, default="tooling",
                        help="Layer value for ticket frontmatter (default: tooling)")
    parser.add_argument("--repo", metavar="SLUG",
                        help="Repo slug for workspace ticket frontmatter")
    args = parser.parse_args()

    if args.workspace:
        internal = _resolve_internal(args.workspace)  # explicit workspace intent
    elif args.harness:
        internal = None  # explicit harness intent — bypass the session check
    else:
        internal = _resolve_bare_layer()  # bare → consult the session-declared layer

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
        ticket_id = _next_id(internal)
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
        if args.problem:
            content = _apply_problem(content, args.problem)
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
