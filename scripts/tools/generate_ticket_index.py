#!/usr/bin/env python3
"""
Generate docs/tickets/INDEX.md from all open tickets.

Reads every .md file in docs/tickets/open/, parses frontmatter,
and writes a grouped index sorted by severity (critical → high → medium → low)
with age-in-sessions and an aging flag for tickets open > 10 sessions.

Usage (from project root):
    python scripts/tools/generate_ticket_index.py

Also called by the session-close skill at Step 0 and by the PostToolUse hook
(scripts/hooks/regenerate_ticket_index.py) after every ticket file write.
"""
import os
import re
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_config as _hc
from ticket_constants import AGING_EMPTY_MARKER

OPEN_DIR = _hc.tickets_dir()
OUTPUT_FILE = "docs/tickets/INDEX.md"
SESSIONS_MD = "docs/sessions.md"

SEVERITY_ORDER = ["critical", "high", "medium", "low", "unknown"]
AGING_THRESHOLD = 10  # sessions


def parse_frontmatter(content: str) -> dict[str, str]:
    """Parse YAML-style frontmatter between --- delimiters."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    result = {}
    for line in content[3:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            v = value.strip()
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = v[1:-1]
            result[key.strip()] = v
    return result


def derive_phase(ticket_id: str) -> str:
    """
    Derive phase from ticket ID number.
      T001–T015  → Phase 2  (paper trading era)
      T018–T026  → Phase 3  (backtesting + IBKR)
      everything else → Process
    """
    try:
        n = int(ticket_id[1:])
    except (ValueError, IndexError):
        return "process"
    if 1 <= n <= 15:
        return "2"
    if 18 <= n <= 26:
        return "3"
    return "process"


def session_number(opened_str: str) -> int | None:
    """Extract the numeric session number from 'S23 2026-03-31'."""
    match = re.match(r"S(\d+)", opened_str)
    return int(match.group(1)) if match else None


def get_current_session(project_root: str) -> int:
    """Read the most recent session number from the Session Log in sessions.md."""
    sessions_path = os.path.join(project_root, SESSIONS_MD)
    if not os.path.exists(sessions_path):
        print(f"ERROR: {sessions_path} not found", file=sys.stderr)
        sys.exit(1)
    with open(sessions_path) as f:
        content = f.read()
    matches = re.findall(r"^S(\d+) \d{4}-\d{2}-\d{2}:", content, re.MULTILINE)
    if not matches:
        print("ERROR: no session entries found in sessions.md", file=sys.stderr)
        sys.exit(1)
    return int(matches[-1]) + 1  # last entry is the closed session; active is next


def load_tickets(open_dir: str) -> list[dict]:
    """Load and parse all ticket files from open_dir."""
    tickets = []
    if not os.path.isdir(open_dir):
        return tickets
    for filename in sorted(os.listdir(open_dir)):
        if not filename.endswith(".md"):
            continue
        path = os.path.join(open_dir, filename)
        with open(path) as f:
            content = f.read()
        fm = parse_frontmatter(content)
        if not fm.get("id"):
            continue
        tid = fm.get("id", "")
        # Use explicit phase: field when present, fall back to ID-range derivation
        phase = fm.get("phase", "") or derive_phase(tid)
        tickets.append({
            "id": tid,
            "title": fm.get("title", "(no title)"),
            "severity": fm.get("severity", "unknown").lower(),
            "opened": fm.get("opened", ""),
            "phase": phase,
            "layer": fm.get("layer", "").strip(),
            "filename": filename,
        })
    return tickets


def render_index(tickets: list[dict], current_session: int, today: str) -> str:
    """Render the full INDEX.md content."""
    lines = [
        "# Ticket Index",
        "",
        f"Generated S{current_session} {today}. {len(tickets)} open tickets.",
        "Re-generate: `python scripts/tools/generate_ticket_index.py`",
        "",
    ]

    # Group by severity
    by_severity: dict[str, list[dict]] = {s: [] for s in SEVERITY_ORDER}
    for t in tickets:
        bucket = t["severity"] if t["severity"] in by_severity else "unknown"
        by_severity[bucket].append(t)

    for sev in SEVERITY_ORDER:
        group = by_severity[sev]
        header = f"## {sev.capitalize()} ({len(group)})"
        lines.append(header)
        lines.append("")
        if not group:
            lines.append(AGING_EMPTY_MARKER)
            lines.append("")
            continue

        # Sort oldest first within severity
        def sort_key(t: dict) -> int:
            n = session_number(t["opened"])
            return n if n is not None else 999

        group.sort(key=sort_key)

        lines.append("| ID | Title | Phase | Layer | Age |")
        lines.append("|----|-------|-------|-------|-----|")
        for t in group:
            opened_n = session_number(t["opened"])
            if opened_n is not None:
                age = current_session - opened_n
                age_str = "this session" if age == 0 else f"{age} session{'s' if age != 1 else ''}"
                if age >= AGING_THRESHOLD:
                    age_str = f"**{age_str}** ⚠"
            else:
                age_str = "unknown"
            phase = t["phase"]
            phase_label = f"Ph{phase}" if phase in ("2", "3", "4") else phase
            layer = t.get("layer") or "—"
            lines.append(f"| {t['id']} | {t['title']} | {phase_label} | {layer} | {age_str} |")
        lines.append("")

    # Aging summary — always emit header so absence of content is unambiguous (S9 #6).
    aging = [
        t for t in tickets
        if session_number(t["opened"]) is not None
        and (current_session - session_number(t["opened"])) >= AGING_THRESHOLD
    ]
    lines.append("## Aging Tickets (open ≥ 10 sessions)")
    lines.append("")
    if aging:
        aging.sort(key=lambda t: session_number(t["opened"]) or 999)
        for t in aging:
            age = current_session - session_number(t["opened"])
            lines.append(f"- **{t['id']}** — {t['title']} (open {age} sessions, since {t['opened']})")
    else:
        lines.append(AGING_EMPTY_MARKER)
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate docs/tickets/INDEX.md")
    parser.add_argument(
        "--session", type=int, default=None,
        help="Override the current session number (use when sessions.md hasn't been updated yet)",
    )
    parser.add_argument(
        "--tickets-dir", default=None,
        help="Override the open tickets directory (absolute path)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Override the INDEX.md output path (absolute path)",
    )
    parser.add_argument(
        "--sessions-file", default=None,
        help="Override the sessions.md path (absolute path)",
    )
    args = parser.parse_args()

    project_root = os.getcwd()
    open_dir = args.tickets_dir if args.tickets_dir else os.path.join(project_root, OPEN_DIR)
    _open_candidate = Path(open_dir) / "open"
    if _open_candidate.is_dir():
        open_dir = str(_open_candidate)
    output_path = args.output if args.output else os.path.join(project_root, OUTPUT_FILE)
    today = datetime.date.today().isoformat()

    if args.session is not None:
        current_session = args.session
    elif args.sessions_file:
        if not os.path.exists(args.sessions_file):
            print(f"ERROR: {args.sessions_file} not found", file=sys.stderr)
            sys.exit(1)
        with open(args.sessions_file) as f:
            content_s = f.read()
        matches = re.findall(r"^S(\d+) \d{4}-\d{2}-\d{2}:", content_s, re.MULTILINE)
        if not matches:
            current_session = 1
        else:
            current_session = int(matches[-1]) + 1
    else:
        current_session = get_current_session(project_root)

    tickets = load_tickets(open_dir)

    content = render_index(tickets, current_session, today)
    with open(output_path, "w") as f:
        f.write(content)

    print(f"Written {output_path} ({len(tickets)} tickets, session S{current_session})")


if __name__ == "__main__":
    main()
