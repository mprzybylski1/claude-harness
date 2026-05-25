#!/usr/bin/env python3
"""
scripts/tools/analyze_tool_log.py
Reads .git/session_tool_log.jsonl and produces a workflow efficiency report.

Usage:
    python scripts/tools/analyze_tool_log.py [--log PATH] [--session SESSION]

Options:
    --log PATH        Path to the tool log (default: .git/session_tool_log.jsonl)
    --session SESSION Filter to a specific session (e.g. S6); default: all sessions

Output sections:
    1. Tool call frequency by type
    2. Top-10 most-read files
    3. Top-10 most-edited files
    4. Error / retry sequences (same tool within 30s)
    5. Session-start and session-close tool-call costs
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LOG = ROOT / ".git" / "session_tool_log.jsonl"
_RETRY_WINDOW_S = 30.0


def _load(log_path: Path, session_filter: str | None) -> tuple[list[dict], int]:
    """Return (records, skipped_count) where skipped_count counts malformed lines."""
    if not log_path.exists():
        return [], 0
    records = []
    skipped = 0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if session_filter and rec.get("session") != session_filter:
            continue
        records.append(rec)
    return records, skipped


def _frequency(records: list[dict]) -> str:
    counts: Counter[str] = Counter(r.get("tool", "") for r in records)
    if not counts:
        return "(no data)"
    lines = [f"  {tool:<20} {count}" for tool, count in counts.most_common()]
    return "\n".join(lines)


def _top_files(records: list[dict], tool_names: set[str], n: int = 10) -> str:
    counts: Counter[str] = Counter(
        r.get("path", "") for r in records
        if r.get("tool") in tool_names and r.get("path")
    )
    if not counts:
        return "  (none)"
    return "\n".join(f"  {count:4d}x  {path}" for path, count in counts.most_common(n))


def _retry_sequences(records: list[dict]) -> str:
    """Find same-tool calls within _RETRY_WINDOW_S — likely retries.

    Computed per-session to avoid false positives at session boundaries.
    """
    by_session: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_session[r.get("session") or ""].append(r)

    retries: list[str] = []
    for sess_records in by_session.values():
        for i in range(1, len(sess_records)):
            prev, cur = sess_records[i - 1], sess_records[i]
            prev_tool = prev.get("tool") or ""
            cur_tool = cur.get("tool") or ""
            if not prev_tool or not cur_tool:
                continue
            if (prev_tool == cur_tool
                    and cur.get("ts", 0) - prev.get("ts", 0) <= _RETRY_WINDOW_S):
                delta = cur.get("ts", 0) - prev.get("ts", 0)
                path = (cur.get("path") or "")[:60]
                retries.append(f"  {cur_tool} × 2 within {delta:.1f}s  path={path!r}")
    return "\n".join(retries) if retries else "  (none)"


def _session_costs(records: list[dict]) -> str:
    by_session: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        s = r.get("session") or "unknown"
        by_session[s].append(r)
    if not by_session:
        return "  (no data)"
    lines = []
    for sess in sorted(by_session):
        recs = by_session[sess]
        lines.append(f"  {sess}: {len(recs)} tool calls")
    return "\n".join(lines)


def report(log_path: Path, session_filter: str | None) -> str:
    records, skipped = _load(log_path, session_filter)
    if not records and not skipped:
        return (
            f"No telemetry data found in {log_path}.\n"
            "Enable via harness.yaml: workflow_telemetry: true"
        )

    read_tools = {"Read", "WebFetch", "WebSearch"}
    edit_tools = {"Edit", "Write", "NotebookEdit"}

    header = (
        f"# Workflow Telemetry Report\n"
        f"Log: {log_path}  |  Records: {len(records)}"
        + (f"  |  Session: {session_filter}" if session_filter else "")
        + (f"  |  Skipped (malformed): {skipped}" if skipped else "")
    )

    sections = [
        header,
        "## Tool call frequency\n" + _frequency(records),
        "## Top-10 most-read files\n" + _top_files(records, read_tools),
        "## Top-10 most-edited files\n" + _top_files(records, edit_tools),
        "## Error / retry sequences (same tool ≤30s)\n" + _retry_sequences(records),
        "## Tool-call cost per session\n" + _session_costs(records),
    ]
    return "\n\n".join(sections)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--log", default=None, metavar="PATH",
                   help=f"Path to tool log (default: {_DEFAULT_LOG})")
    p.add_argument("--session", default=None, metavar="SESSION",
                   help="Filter to a specific session ID (e.g. S6)")
    args = p.parse_args()

    log_path = Path(args.log) if args.log else _DEFAULT_LOG
    print(report(log_path, args.session))


if __name__ == "__main__":
    main()
