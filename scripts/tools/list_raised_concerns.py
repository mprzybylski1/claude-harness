#!/usr/bin/env python3
"""
Aggregate pending workspace→harness concerns across all workspaces.

Usage:
    list_raised_concerns.py

Scans workspaces/*/raised/*.md (excludes raised/archive/), prints only
raised and promoted items grouped by workspace and sorted by severity.
Exits cleanly with no output when no pending concerns exist.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_default_root = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get("HARNESS_ROOT", str(_default_root)))

_ACTIVE_STATUSES = {"raised", "promoted"}
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _parse_frontmatter(path: Path) -> dict:
    """Return YAML frontmatter fields as a dict, or {} on any parse error."""
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


def _severity_key(item: dict) -> int:
    return _SEVERITY_ORDER.get(item.get("severity", "low"), 3)


def main() -> None:
    ws_base = ROOT / "workspaces"
    if not ws_base.is_dir():
        return

    # Collect: {slug: [item_dict, ...]}
    by_workspace: dict[str, list[dict]] = {}

    for ws_dir in sorted(ws_base.iterdir()):
        if not ws_dir.is_dir():
            continue
        raised_dir = ws_dir / "raised"
        if not raised_dir.is_dir():
            continue
        slug = ws_dir.name
        items: list[dict] = []
        for md in raised_dir.glob("*.md"):
            if md.parent.name == "archive":
                continue
            data = _parse_frontmatter(md)
            if not data:
                continue
            if data.get("status") not in _ACTIVE_STATUSES:
                continue
            items.append(data)
        if items:
            items.sort(key=_severity_key)
            by_workspace[slug] = items

    if not by_workspace:
        return

    lines: list[str] = ["Pending raised concerns:", ""]
    for slug, items in by_workspace.items():
        lines.append(f"  {slug}:")
        for item in items:
            sr_id = item.get("id", "SR-???")
            severity = item.get("severity", "?")
            title = item.get("title", "(no title)")
            status = item.get("status", "?")
            harness_ticket = item.get("harness_ticket") or ""
            suffix = f" → {harness_ticket}" if harness_ticket else ""
            lines.append(f"    {sr_id} ({severity}) — {title} [{status}{suffix}]")
        lines.append("")

    lines.append("Triage:")
    lines.append("  promote: python scripts/tools/promote_raised_concern.py <slug>/SR-NNN")
    lines.append("  reject:  python scripts/tools/reject_raised_concern.py <slug>/SR-NNN --reason \"...\"")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
