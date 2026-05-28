#!/usr/bin/env python3
"""
Create a workspace→harness concern file (SR-NNN) in the boundary slot.

Usage:
    raise_for_harness.py "Title" [--severity high] [--workspace SLUG]

Workspace context is auto-detected from CWD (if inside workspaces/<slug>/)
or specified explicitly via --workspace. Refuses without a workspace context.
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


def _next_sr_number(raised_dir: Path) -> int:
    """Return next SR sequence number by scanning raised/ + raised/archive/."""
    max_n = 0
    for scan_dir in [raised_dir, raised_dir / "archive"]:
        if not scan_dir.is_dir():
            continue
        for p in scan_dir.glob("SR-[0-9]*.md"):
            m = re.match(r"SR-(\d+)", p.name)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:50]


def _current_session(sessions_md: Path | None, slug: str) -> str:
    """Resolve the workspace session ID. Fail-closed when sessions_md is None.

    Why fail closed: this value lands in an SR file's `raised:` frontmatter,
    a tracked record that downstream tools (list_raised_concerns.py,
    promote_raised_concern.py) parse. Falling back to harness-global
    current_session.py would stamp a harness session number into workspace
    state — a workspace↔harness audit-trail contamination (Invariant 1).
    surface_workspace_concerns.py warn-and-omits because its session ID only
    appears in a commit message; here the cost of a wrong value is higher.
    """
    if sessions_md is None:
        default_path = ROOT / "workspaces" / slug / "internal" / "sessions.md"
        print(
            f"ERROR: workspace '{slug}' has no sessions.md (looked for "
            f"{default_path} or docs_path override in workspace.yaml) — "
            f"refusing to fall back to harness session ID (would contaminate "
            f"workspace audit trail).\n"
            f"Run /session-start inside the workspace at least once to "
            f"initialise its session log before raising concerns.",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        return session_lookup.call_current_session(sessions_md, root=ROOT)
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: current_session.py failed: {exc.stderr.strip()}", file=sys.stderr)
        sys.exit(2)


def _yaml_scalar(value: str) -> str:
    """Return value as a YAML scalar. Double-quote when a plain scalar would
    be misparsed (e.g. titles containing ': ', which YAML reads as a nested
    mapping key — observed S22 with SR-004..SR-007 silently dropped by
    list_raised_concerns.py)."""
    needs_quote = (
        not value
        or value != value.strip()
        or ": " in value
        or value.endswith(":")
        or " #" in value
        or value[0] in "-?:,[]{}#&*!|>'\"%@`"
    )
    if not needs_quote:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


_TEMPLATE = """\
---
id: {sr_id}
from: {slug}
raised: {session} {today}
title: {title}
severity: {severity}
status: raised
harness_ticket:
resolved_in:
---

## Context

(Why this matters, what workspace surfaced it, blocking yes/no.)

## Proposed change

(What the workspace thinks should happen. Harness may disagree.)

## Harness disposition

(Filled by harness on promotion or rejection.)
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a workspace→harness concern file (SR-NNN)."
    )
    parser.add_argument("title", help="Short concern title")
    parser.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low"],
        default="medium",
    )
    parser.add_argument(
        "--workspace",
        metavar="SLUG",
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
                "Run from inside a workspace directory or pass --workspace SLUG.\n"
                "This script is for workspace sessions only — harness tickets\n"
                "belong in docs/tickets/ via create_ticket.py.",
                file=sys.stderr,
            )
            sys.exit(1)

    raised_dir = ROOT / "workspaces" / slug / "raised"
    raised_dir.mkdir(parents=True, exist_ok=True)
    (raised_dir / "archive").mkdir(exist_ok=True)

    session = _current_session(session_lookup.resolve_workspace_sessions_md(slug, ROOT), slug)
    today = date.today().isoformat()
    slug_part = _slugify(args.title)

    _MAX_RETRIES = 10
    for attempt in range(_MAX_RETRIES):
        n = _next_sr_number(raised_dir)
        sr_id = f"SR-{n:03d}"
        dest = raised_dir / f"{sr_id}-{slug_part}.md"
        content = _TEMPLATE.format(
            sr_id=sr_id,
            slug=slug,
            session=session,
            today=today,
            title=_yaml_scalar(args.title),
            severity=args.severity,
        )
        try:
            with open(dest, "x", encoding="utf-8") as fh:
                fh.write(content)
            break
        except FileExistsError:
            if attempt == _MAX_RETRIES - 1:
                print(
                    f"ERROR: could not allocate SR number after {_MAX_RETRIES} attempts",
                    file=sys.stderr,
                )
                sys.exit(1)

    print(dest)


if __name__ == "__main__":
    main()
