#!/usr/bin/env python3
"""portfolio.py — Cross-workspace metadata summary.

Usage:
    python scripts/tools/portfolio.py
    python scripts/tools/portfolio.py --markdown   # same output
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness_config as _hc


def _workspaces_base() -> Path:
    return (ROOT / _hc.workspaces_dir()).resolve()


def _yaml_get(path: Path, key: str) -> str:
    """Extract a single scalar value from a YAML frontmatter block without full parse."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    # Limit search to YAML frontmatter (between --- delimiters) to avoid matching body text
    if text.startswith("---"):
        end = text.find("---", 3)
        text = text[3:end] if end != -1 else text[3:]
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


_KNOWN_SEVERITIES = frozenset({"critical", "high", "medium", "low"})


def _ticket_counts(open_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not open_dir.exists():
        return counts
    for f in open_dir.glob("T*.md"):
        sev = _yaml_get(f, "severity").lower()
        if sev:
            key = sev if sev in _KNOWN_SEVERITIES else "other"
            counts[key] = counts.get(key, 0) + 1
    return counts


def _last_session(sessions_path: Path) -> str:
    if not sessions_path.exists():
        return "—"
    matches = re.findall(r"S\d+ (\d{4}-\d{2}-\d{2}):", sessions_path.read_text(encoding="utf-8"))
    return matches[-1] if matches else "—"


def _format_ticket_cell(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    if total == 0:
        return "0"
    parts = []
    for sev, abbr in [("critical", "crit"), ("high", "high"), ("medium", "med"), ("low", "low"), ("other", "other")]:
        n = counts.get(sev, 0)
        if n:
            parts.append(f"{n} {abbr}")
    detail = ", ".join(parts)
    return f"{total} ({detail})"


def main() -> None:
    ws_base = _workspaces_base()
    if not ws_base.exists():
        print("No active workspaces.")
        sys.exit(0)

    rows = []
    for ws_dir in sorted(ws_base.iterdir()):
        if not ws_dir.is_dir() or ws_dir.name == "archive":
            continue
        ws_yaml = ws_dir / "workspace.yaml"
        if not ws_yaml.exists():
            continue
        try:
            import yaml
            cfg = yaml.safe_load(ws_yaml.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"WARNING: Could not parse {ws_yaml}: {e}", file=sys.stderr)
            continue
        if not cfg or cfg.get("status") == "archived":
            continue

        slug = ws_dir.name
        name = cfg.get("name", slug)
        ws_type = cfg.get("type", "?")
        repo_count = len(cfg.get("repos", []))
        ticket_counts = _ticket_counts(ws_dir / "internal" / "tickets" / "open")
        last = _last_session(ws_dir / "internal" / "sessions.md")

        rows.append(dict(
            slug=slug,
            name=name,
            ws_type=ws_type,
            repo_count=repo_count,
            ticket_counts=ticket_counts,
            last=last,
        ))

    if not rows:
        print("No active workspaces.")
        sys.exit(0)

    rows.sort(key=lambda r: r["last"] if r["last"] != "—" else "0000-00-00", reverse=True)

    today = date.today().isoformat()
    print(f"# Portfolio — {today}")
    print()
    print("| Workspace | Type | Repos | Open tickets | Last session |")
    print("|-----------|------|-------|--------------|--------------|")
    for r in rows:
        link = f"[{r['name']}](workspaces/{r['slug']}/)"
        ticket_cell = _format_ticket_cell(r["ticket_counts"])
        print(f"| {link} | {r['ws_type']} | {r['repo_count']} | {ticket_cell} | {r['last']} |")

    print()
    total_tickets = sum(sum(r["ticket_counts"].values()) for r in rows)
    print(f"**Total:** {len(rows)} active workspace{'s' if len(rows) != 1 else ''} · {total_tickets} open ticket{'s' if total_tickets != 1 else ''}")


if __name__ == "__main__":
    main()
