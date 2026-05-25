#!/usr/bin/env python3
"""Generate workspaces/<slug>/client/progress.md from internal session data.

Usage:
    python scripts/tools/generate_client_progress.py \
        --workspace workspaces/<slug>/ \
        --session S003
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


def parse_frontmatter(content: str) -> dict[str, str]:
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


def first_sentence(text: str) -> str:
    """Return the first sentence of text, trimmed."""
    text = text.strip()
    match = re.search(r"[.!?]", text)
    if match:
        return text[: match.end()].strip()
    return text


def extract_active_work(sessions_content: str, session_label: str) -> str:
    """Extract the body of the Active Work section for session_label.

    Looks for the header line starting with **S[N] — or **S[N] — inside
    the ## Active Work section. Returns the body text (everything after the
    header line until the next --- or end of the section).
    """
    active_match = re.search(r"^## Active Work\s*$", sessions_content, re.MULTILINE)
    if not active_match:
        return ""

    section_start = active_match.end()
    next_section = re.search(r"^---", sessions_content[section_start:], re.MULTILINE)
    section_end = section_start + next_section.start() if next_section else len(sessions_content)
    section = sessions_content[section_start:section_end]

    header_pattern = re.compile(
        r"^\*\*" + re.escape(session_label) + r"\s*[—–-]", re.MULTILINE
    )
    header_match = header_pattern.search(section)
    if not header_match:
        return ""

    body_start = header_match.end()
    # Include rest of the header line
    rest_of_line = re.search(r"\*\*\s*\n", section[header_match.start():])
    if rest_of_line:
        body_start = header_match.start() + rest_of_line.end()

    return section[body_start:].strip()


def extract_session_summary_line(sessions_content: str, session_label: str) -> str:
    """Extract the one-line summary from the Active Work header for session_label."""
    active_match = re.search(r"^## Active Work\s*$", sessions_content, re.MULTILINE)
    if not active_match:
        return ""

    section_start = active_match.end()
    next_section = re.search(r"^---", sessions_content[section_start:], re.MULTILINE)
    section_end = section_start + next_section.start() if next_section else len(sessions_content)
    section = sessions_content[section_start:section_end]

    header_pattern = re.compile(
        r"^\*\*" + re.escape(session_label) + r"\s*[—–-]\s*(.+?)\*\*", re.MULTILINE
    )
    match = header_pattern.search(section)
    if match:
        return match.group(1).strip()
    return ""


def extract_next_focus(body: str) -> str:
    """Extract the 'next session focus' from the Active Work body.

    Looks for a 'Remaining open items' line or the last bullet point.
    """
    remaining_match = re.search(r"Remaining open items[:\s]*(.+)", body)
    if remaining_match:
        return remaining_match.group(1).strip()

    bullets = re.findall(r"^[-*]\s+(.+)", body, re.MULTILINE)
    if bullets:
        return bullets[-1].strip()

    return "See open tickets."


def load_closed_tickets_for_session(closed_dir: Path, session_label: str) -> list[dict]:
    """Find tickets closed in session_label by reading their frontmatter."""
    tickets = []
    if not closed_dir.exists():
        return tickets

    for ticket_file in sorted(closed_dir.glob("T*.md")):
        content = ticket_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        closed_val = fm.get("closed", "")
        if not closed_val:
            continue
        if not closed_val.startswith(session_label):
            continue

        tid = fm.get("id", "")
        title = fm.get("title", "(no title)")

        resolution_text = ""
        res_match = re.search(r"^## Resolution\s*\n(.+?)(?=^##|\Z)", content, re.MULTILINE | re.DOTALL)
        if res_match:
            resolution_body = res_match.group(1).strip()
            prefix_stripped = re.sub(r"^S\d+\s+\d{4}-\d{2}-\d{2}:\s*", "", resolution_body)
            resolution_text = first_sentence(prefix_stripped)

        tickets.append({"id": tid, "title": title, "resolution": resolution_text})

    return tickets


def extract_session_date(sessions_content: str, session_n: int) -> str:
    """Extract the date for a session from the Session Log section."""
    match = re.search(
        r"^S" + str(session_n) + r"\s+(\d{4}-\d{2}-\d{2}):", sessions_content, re.MULTILINE
    )
    if match:
        return match.group(1)
    return date.today().isoformat()


def load_existing_previous(client_progress: Path) -> str:
    """Return the existing content of client/progress.md below the first '---' separator, if any."""
    if not client_progress.exists():
        return ""
    content = client_progress.read_text(encoding="utf-8")
    sep = content.find("\n---\n")
    if sep == -1:
        return ""
    return content[sep + 5:].strip()


def build_progress_md(
    workspace_name: str,
    session_label: str,
    session_date: str,
    summary_line: str,
    closed_tickets: list[dict],
    next_focus: str,
    previous_content: str,
) -> str:
    lines = [
        f"# Progress — {workspace_name}",
        "",
        f"_Last updated: {session_label} {session_date}_",
        "",
        "---",
        "",
        f"## Session {session_label} — {session_date}",
        "",
    ]

    if summary_line:
        lines += [summary_line, ""]

    if closed_tickets:
        lines += ["### Completed this session", ""]
        for t in closed_tickets:
            if t["resolution"]:
                lines.append(f"- **{t['id']}: {t['title']}** — {t['resolution']}")
            else:
                lines.append(f"- **{t['id']}: {t['title']}**")
        lines.append("")

    lines += ["### Next session focus", "", next_focus, ""]

    if previous_content:
        lines += ["---", "", "## Previous sessions", "", previous_content, ""]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate client/progress.md from internal session data."
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Path to the workspace directory (e.g. workspaces/acme/)",
    )
    parser.add_argument(
        "--session",
        required=True,
        help="Session label, e.g. S003 or 3",
    )
    args = parser.parse_args()

    ws_dir = Path(args.workspace).resolve()
    if not ws_dir.exists():
        print(f"Error: workspace directory not found: {ws_dir}", file=sys.stderr)
        sys.exit(1)

    session_arg = args.session.lstrip("Ss")
    try:
        session_n = int(session_arg)
    except ValueError:
        print(f"Error: invalid session '{args.session}'", file=sys.stderr)
        sys.exit(1)
    session_label = f"S{session_n:03d}"

    try:
        import yaml
        ws_yaml = ws_dir / "workspace.yaml"
        workspace_name = yaml.safe_load(ws_yaml.read_text(encoding="utf-8")).get("name", ws_dir.name) if ws_yaml.exists() else ws_dir.name
    except Exception:
        workspace_name = ws_dir.name

    sessions_path = ws_dir / "internal" / "sessions.md"
    sessions_content = ""
    if sessions_path.exists():
        sessions_content = sessions_path.read_text(encoding="utf-8")

    session_date = extract_session_date(sessions_content, session_n) if sessions_content else date.today().isoformat()
    summary_line = extract_session_summary_line(sessions_content, session_label) if sessions_content else ""
    body = extract_active_work(sessions_content, session_label) if sessions_content else ""
    next_focus = extract_next_focus(body) if body else "See open tickets."

    closed_dir = ws_dir / "internal" / "tickets" / "closed"
    closed_tickets = load_closed_tickets_for_session(closed_dir, session_label)

    client_dir = ws_dir / "client"
    client_dir.mkdir(parents=True, exist_ok=True)
    client_progress = client_dir / "progress.md"

    previous_content = load_existing_previous(client_progress)

    content = build_progress_md(
        workspace_name=workspace_name,
        session_label=session_label,
        session_date=session_date,
        summary_line=summary_line,
        closed_tickets=closed_tickets,
        next_focus=next_focus,
        previous_content=previous_content,
    )

    client_progress.write_text(content, encoding="utf-8")
    print(f"Written {client_progress} ({len(closed_tickets)} tickets closed)")


if __name__ == "__main__":
    main()
