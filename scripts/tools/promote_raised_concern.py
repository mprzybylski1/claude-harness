#!/usr/bin/env python3
"""
Promote a workspace→harness concern: create a harness ticket, stamp the SR file.

Usage:
    promote_raised_concern.py <slug>/SR-NNN

Reads the SR file, creates a harness ticket via create_ticket.py, stamps the
ticket with source: <slug>/SR-NNN, and updates the SR to status: promoted with
harness_ticket: T###. Refuses if the SR is not in 'raised' status.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_LAYER_VALUES = ("backend", "frontend", "fullstack", "infra", "process", "tooling")

_default_root = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("HARNESS_ROOT", str(_default_root)))
_SCRIPTS_DIR = Path(__file__).resolve().parent  # sibling scripts always here

sys.path.insert(0, str(ROOT / "scripts" / "tools"))


def _parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Return (fields_dict, raw_text). Exits 2 on parse error."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        print(f"ERROR: {path} has no YAML frontmatter block", file=sys.stderr)
        sys.exit(2)
    import yaml
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        print(f"ERROR: failed to parse frontmatter in {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    return (data if isinstance(data, dict) else {}), text


def _find_sr_file(slug: str, sr_id: str) -> Path:
    """Find SR file in workspaces/<slug>/raised/. Exits 1 if not found."""
    raised_dir = ROOT / "workspaces" / slug / "raised"
    if not raised_dir.is_dir():
        print(f"ERROR: raised directory not found at {raised_dir}", file=sys.stderr)
        sys.exit(1)
    matches = list(raised_dir.glob(f"{sr_id}-*.md"))
    if not matches:
        print(f"ERROR: {sr_id} not found in {raised_dir}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        print(f"ERROR: multiple files match {sr_id} in {raised_dir}: {matches}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def _extract_body(text: str, sr_id: str, slug: str) -> str:
    """Return Context + Proposed change sections as ticket Problem body.

    Any H2 header not in the copy_on allowlist terminates the current copy
    section — so unknown sections like ## Principle, ## Boundary slot etc.
    are not bled into the ticket body. ### subheadings within a copy section
    are preserved (they're content, not boundaries).
    """
    lines = [f"Promoted from {slug}/{sr_id}.", ""]
    in_section = False
    copy_on = {"## context", "## proposed change"}
    for line in text.split("\n"):
        stripped = line.strip()
        lower = stripped.lower()
        is_h2 = stripped.startswith("## ") and not stripped.startswith("### ")
        if lower in copy_on:
            in_section = True
        elif is_h2:
            in_section = False
        if in_section:
            lines.append(line)
    return "\n".join(lines).strip()


_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
_NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+(.+?)\s*$")


def _extract_proposed_change_acs(text: str) -> list[str]:
    """Return one AC text per bullet/numbered list item found inside the SR's
    ## Proposed change section. Empty when the section is prose-only or absent;
    create_ticket.py then keeps its default '- [ ] (fill in)' placeholder so
    the operator hand-fills before closing (T127)."""
    items: list[str] = []
    in_section = False
    for line in text.split("\n"):
        stripped = line.strip()
        is_h2 = stripped.startswith("## ") and not stripped.startswith("### ")
        if stripped.lower() == "## proposed change":
            in_section = True
            continue
        if in_section and is_h2:
            break
        if not in_section:
            continue
        m = _BULLET_RE.match(line) or _NUMBERED_RE.match(line)
        if m:
            items.append(m.group(1).strip())
    return items


def _stamp_source(ticket_path: Path, sr_ref: str) -> None:
    """Insert source: <sr_ref> into ticket frontmatter after closed: field."""
    text = ticket_path.read_text(encoding="utf-8")
    updated = re.sub(
        r"(^closed:.*$)",
        rf"\1\nsource: {sr_ref}",
        text,
        flags=re.MULTILINE,
        count=1,
    )
    if updated == text:
        print(
            f"ERROR: could not insert source: field into {ticket_path} — "
            f"missing closed: line in frontmatter. Add 'closed:' to the ticket before promoting.",
            file=sys.stderr,
        )
        sys.exit(2)
    ticket_path.write_text(updated, encoding="utf-8")


def _inject_body(ticket_path: Path, body: str) -> None:
    """Replace Problem placeholder with extracted SR body."""
    text = ticket_path.read_text(encoding="utf-8")
    updated = re.sub(
        r"(## Problem\s*\n)\(Describe the problem here\.\)\s*",
        lambda m: m.group(1) + body + "\n",
        text,
        flags=re.DOTALL,
        count=1,
    )
    ticket_path.write_text(updated, encoding="utf-8")


def _update_sr(sr_path: Path, ticket_id: str) -> None:
    """Update SR file: status raised → promoted, harness_ticket: → T###."""
    text = sr_path.read_text(encoding="utf-8")
    text = re.sub(
        r"(^status:\s*)raised\s*$",
        r"\1promoted",
        text,
        flags=re.MULTILINE,
        count=1,
    )
    new_text = re.sub(
        r"(^harness_ticket:).*$",
        rf"\1 {ticket_id}",
        text,
        flags=re.MULTILINE,
        count=1,
    )
    if new_text == text:
        print(
            f"WARNING: could not set harness_ticket: in SR {sr_path.name} — "
            f"missing harness_ticket: field. Add it manually: harness_ticket: {ticket_id}",
            file=sys.stderr,
        )
    sr_path.write_text(new_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote a workspace→harness concern into a harness ticket.",
        usage="promote_raised_concern.py <slug>/SR-NNN [--layer LAYER]",
    )
    parser.add_argument(
        "sr_ref",
        metavar="<slug>/SR-NNN",
        help="SR reference, e.g. scrabble-score/SR-001",
    )
    parser.add_argument(
        "--layer",
        choices=_LAYER_VALUES,
        default="tooling",
        help="Layer for the created ticket (default: tooling)",
    )
    args = parser.parse_args()

    if "/" not in args.sr_ref:
        print(
            "Usage: promote_raised_concern.py <slug>/SR-NNN\n"
            "Example: promote_raised_concern.py scrabble-score/SR-001",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_slug, raw_id = args.sr_ref.split("/", 1)
    sr_id = raw_id.upper()
    if not re.fullmatch(r"SR-\d+", sr_id):
        print(f"ERROR: invalid SR ID '{raw_id}' — expected SR-NNN format", file=sys.stderr)
        sys.exit(1)
    sr_ref = f"{raw_slug}/{sr_id}"

    sr_path = _find_sr_file(raw_slug, sr_id)
    data, text = _parse_frontmatter(sr_path)

    status = data.get("status", "")
    if status != "raised":
        print(
            f"ERROR: SR is in '{status}' status — can only promote 'raised' SRs.\n"
            f"  SR file: {sr_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    title = data.get("title", sr_id)
    severity = data.get("severity", "medium")
    body = _extract_body(text, sr_id, raw_slug)
    acs = _extract_proposed_change_acs(text)

    # Create harness ticket via create_ticket.py
    cmd = [
        sys.executable,
        str(_SCRIPTS_DIR / "create_ticket.py"),
        title,
        "--severity", severity,
        "--layer", args.layer,
    ]
    for ac in acs:
        cmd.extend(["--ac", ac])
    result = subprocess.run(
        cmd,
        capture_output=True, text=True,
        env={**os.environ, "HARNESS_ROOT": str(ROOT)},
    )
    if result.returncode != 0:
        print(f"ERROR: create_ticket.py failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(2)

    ticket_path = Path(result.stdout.strip())
    m = re.match(r"T\d+", ticket_path.name)
    if not m:
        print(f"ERROR: could not parse ticket ID from path {ticket_path}", file=sys.stderr)
        sys.exit(2)
    ticket_id = m.group(0)

    _stamp_source(ticket_path, sr_ref)
    _inject_body(ticket_path, body)
    _update_sr(sr_path, ticket_id)

    print(f"Promoted {sr_ref} → {ticket_id}")
    print(f"  Ticket: {ticket_path}")
    print(f"  SR:     {sr_path}")
    print(f"\nStage both files before committing:")
    print(f"  git add {ticket_path} {sr_path}")


if __name__ == "__main__":
    main()
