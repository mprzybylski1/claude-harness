#!/usr/bin/env python3
"""
Close a ticket in one command.

Does the full closure dance:
  1. Locate the ticket in tickets/open/ (harness or workspace).
  2. Check that all ACs are ticked (override with --force).
  3. Update frontmatter: status → closed, closed → S<N> YYYY-MM-DD.
  4. Replace ## Resolution placeholder with the provided text.
  5. Move file to archive/.
  6. Regenerate tickets/INDEX.md.
  7. Print a suggested git commit message.

Usage:
    python scripts/tools/close_ticket.py T045 --resolution "What was done."
    python scripts/tools/close_ticket.py T045 --resolution-file /tmp/res.txt
    python scripts/tools/close_ticket.py T045 --resolution "..." --force
    python scripts/tools/close_ticket.py T045 --resolution "..." --workspace scrabble-score
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
from workspace_config import load_workspace, internal_dir as _ws_internal_dir

# ── Helpers ───────────────────────────────────────────────────────────────────

def _docs_paths(ws_dir: Path) -> list[Path]:
    """Return extra docs roots configured via docs_path in workspace.yaml."""
    cfg = load_workspace(ws_dir)
    if not cfg or not cfg.get("docs_path"):
        return []
    p = Path(cfg["docs_path"]).expanduser()
    if p.is_dir():
        return [p]
    return []


def _find_ticket(ticket_id: str, workspace_slug: str | None = None) -> tuple[Path, Path | None]:
    """Return (ticket_path, workspace_internal_dir | None).

    Searches harness-root tickets/open/ and all workspace internal paths, then
    errors if more than one match is found. Supply --workspace to disambiguate.
    """
    ticket_id = ticket_id.upper()
    if not re.fullmatch(r"T\d+", ticket_id):
        print(f"ERROR: invalid ticket ID '{ticket_id}' — expected T### format", file=sys.stderr)
        sys.exit(1)

    matches: list[tuple[Path, Path | None]] = []

    if workspace_slug is None or workspace_slug == "":
        # Search harness-root tickets
        for p in sorted((ROOT / "docs" / "tickets" / "open").glob(f"{ticket_id}-*.md")):
            matches.append((p, None))

    ws_base = ROOT / "workspaces"
    if ws_base.is_dir():
        for ws_dir in sorted(ws_base.iterdir()):
            if not ws_dir.is_dir():
                continue
            if workspace_slug and ws_dir.name != workspace_slug:
                continue
            for internal in [ws_dir / "internal", *_docs_paths(ws_dir)]:
                open_dir = internal / "tickets" / "open"
                for p in sorted(open_dir.glob(f"{ticket_id}-*.md")):
                    matches.append((p, internal))

    if not matches:
        print(f"ERROR: ticket {ticket_id} not found in any tickets/open/ directory", file=sys.stderr)
        sys.exit(1)

    if len(matches) > 1:
        locations = "\n".join(f"  {p} (workspace: {i.parent.name if i else 'harness root'})"
                              for p, i in matches)
        print(
            f"ERROR: ticket {ticket_id} found in multiple locations — use --workspace to disambiguate:\n"
            + locations,
            file=sys.stderr,
        )
        sys.exit(1)

    return matches[0]


def _current_session(internal: Path | None) -> str:
    """Return S<N> for the active session."""
    cmd = [sys.executable, str(ROOT / "scripts" / "tools" / "current_session.py")]
    if internal is not None:
        cmd += ["--sessions", str(internal / "sessions.md")]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: current_session.py failed (exit {exc.returncode}): {exc.stderr.strip()}", file=sys.stderr)
        sys.exit(2)


def _check_acs(content: str) -> list[str]:
    """Return list of unchecked AC lines (- [ ] ...)."""
    return [ln.strip() for ln in content.splitlines() if re.match(r"\s*-\s+\[ \]", ln)]


def _update_frontmatter(content: str, session: str) -> str:
    today = date.today().isoformat()
    content = re.sub(r"^(status:\s*)open\s*$", r"\1closed", content, flags=re.MULTILINE)
    content = re.sub(r"^(closed:).*$", rf"\1 {session} {today}", content, flags=re.MULTILINE)
    return content


def _replace_resolution(content: str, resolution: str) -> str:
    """Replace the '(Fill in on close.)' placeholder with resolution text."""
    placeholder = re.compile(
        r"(## Resolution\s*\n)"
        r"(?:> \*\*Client-visible:\*\*.*?\n(?:> .*\n)*\n)?"
        r"\(Fill in on close[^)]*\)\s*",
        re.DOTALL,
    )
    if placeholder.search(content):
        return placeholder.sub(r"\g<1>" + resolution.rstrip() + "\n", content)
    print("ERROR: ## Resolution placeholder '(Fill in on close.)' not found — ticket format unexpected", file=sys.stderr)
    sys.exit(2)


def _regenerate_index(internal: Path | None) -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "tools" / "generate_ticket_index.py")]
    if internal is not None:
        cmd += ["--sessions", str(internal / "sessions.md")]
    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        print(f"WARNING: generate_ticket_index.py failed: {exc}", file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Close a harness ticket in one command.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("ticket_id", metavar="T###", help="Ticket ID to close, e.g. T045")
    res_group = parser.add_mutually_exclusive_group(required=True)
    res_group.add_argument("--resolution", "-r", metavar="TEXT",
                           help="Resolution text (inline)")
    res_group.add_argument("--resolution-file", metavar="PATH",
                           help="Path to a file containing the resolution text")
    parser.add_argument("--force", action="store_true",
                        help="Close even if some ACs are still unchecked")
    parser.add_argument("--workspace", metavar="SLUG",
                        help="Workspace slug to search (required when ID is ambiguous)")
    args = parser.parse_args()

    ticket_id = args.ticket_id.upper()
    ticket_path, internal = _find_ticket(ticket_id, args.workspace)
    content = ticket_path.read_text(encoding="utf-8")

    # Resolution text
    if args.resolution_file:
        res_path = Path(args.resolution_file)
        if not res_path.exists():
            print(f"ERROR: --resolution-file '{res_path}' not found", file=sys.stderr)
            sys.exit(1)
        resolution = res_path.read_text(encoding="utf-8").strip()
    else:
        resolution = args.resolution.strip()

    # AC check
    unchecked = _check_acs(content)
    if unchecked and not args.force:
        print(f"ERROR: {ticket_id} has unchecked ACs — resolve them or use --force:", file=sys.stderr)
        for ln in unchecked:
            print(f"  {ln}", file=sys.stderr)
        sys.exit(1)

    # Derive session and today's date
    session = _current_session(internal)

    # Append session info to resolution
    full_resolution = resolution
    if not re.search(r"\bS\d+\b.*\d{4}-\d{2}-\d{2}", resolution):
        full_resolution = resolution + f"\n\nClosed {session} {date.today().isoformat()}."

    # Apply changes
    content = _update_frontmatter(content, session)
    content = _replace_resolution(content, full_resolution)

    # Determine archive path
    if internal is not None:
        archive_dir = internal / "archive"
    else:
        archive_dir = ROOT / "docs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    dest = archive_dir / ticket_path.name
    if dest.exists():
        print(f"ERROR: {dest} already exists in archive — ticket may already be closed", file=sys.stderr)
        sys.exit(2)

    # Write to dest first so a write failure leaves open/ untouched (S9 #2).
    dest.write_text(content, encoding="utf-8")
    ticket_path.unlink()

    # Regenerate index
    _regenerate_index(internal)

    # Extract title for commit message
    title_m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else ticket_id

    print(f"Closed {ticket_id} → {dest.relative_to(ROOT)}")
    print()
    print("Suggested commit:")
    print(f'  git commit -m "fix({ticket_id}): {title}"')


if __name__ == "__main__":
    main()
