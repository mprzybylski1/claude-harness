#!/usr/bin/env python3
"""
telemetry_coverage.py — measure telemetry capture vs. ground truth (T156).

Compares the number of tool calls the PostToolUse hook recorded for a session
(.git/session_tool_log.jsonl, joined by claude_session_uuid) against the number
of `tool_use` blocks in that session's native Claude Code transcript (the source
of truth). Surfaces under-counting as a coverage ratio.

The join key is claude_session_uuid == the transcript filename stem (see
log_tool_usage.py). With the T156 fix that key is reliably populated, so this
check is meaningful per session.

Usage:
    # most recent transcript for this project:
    python scripts/tools/telemetry_coverage.py
    # a specific session/transcript:
    python scripts/tools/telemetry_coverage.py --transcript ~/.claude/projects/<proj>/<uuid>.jsonl
    python scripts/tools/telemetry_coverage.py --uuid <uuid>

Exit code is 0 (advisory) unless --min-coverage is given and not met (then 1).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LOG = ROOT / ".git" / "session_tool_log.jsonl"


def count_native_tool_uses(transcript: Path) -> int:
    """Count tool_use blocks in a native Claude Code transcript (.jsonl)."""
    n = 0
    for line in transcript.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        for block in msg.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                n += 1
    return n


def count_telemetry_records(log_path: Path, uuid: str) -> int:
    """Count telemetry records whose claude_session_uuid matches uuid."""
    if not log_path.exists():
        return 0
    n = 0
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("claude_session_uuid") == uuid:
            n += 1
    return n


def _resolve_transcript(args) -> Path | None:
    if args.transcript:
        p = Path(args.transcript).expanduser()
        return p if p.exists() else None
    proj_dir = Path(args.projects_dir).expanduser() if args.projects_dir else None
    if proj_dir is None or not proj_dir.is_dir():
        return None
    if args.uuid:
        cand = proj_dir / f"{args.uuid}.jsonl"
        return cand if cand.exists() else None
    transcripts = sorted(proj_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return transcripts[-1] if transcripts else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--transcript", help="Path to a native transcript .jsonl")
    ap.add_argument("--uuid", help="Session UUID (transcript filename stem)")
    ap.add_argument("--projects-dir",
                    help="Claude projects dir to search (default: derived from this repo path)")
    ap.add_argument("--log", default=str(_DEFAULT_LOG), help="Telemetry log path")
    ap.add_argument("--min-coverage", type=float, default=None,
                    help="Exit 1 if coverage ratio falls below this (0–1)")
    args = ap.parse_args(argv)

    if args.projects_dir is None and not args.transcript:
        # Default project dir: ~/.claude/projects/<escaped repo path>
        escaped = str(ROOT).replace("/", "-")
        args.projects_dir = str(Path.home() / ".claude" / "projects" / escaped)

    transcript = _resolve_transcript(args)
    if transcript is None:
        print("telemetry_coverage: no transcript found to compare against.", file=sys.stderr)
        return 0

    uuid = args.uuid or transcript.stem
    native = count_native_tool_uses(transcript)
    captured = count_telemetry_records(Path(args.log), uuid)
    ratio = (captured / native) if native else 1.0

    print(f"transcript: {transcript.name}")
    print(f"native tool_use calls : {native}")
    print(f"telemetry records     : {captured}")
    print(f"coverage              : {ratio:.0%}")
    if captured > native:
        print("note: telemetry > native — likely session-number/uuid conflation "
              "(see T165) or multiple transcripts share this uuid.")

    if args.min_coverage is not None and ratio < args.min_coverage:
        print(f"FAIL: coverage {ratio:.0%} below threshold {args.min_coverage:.0%}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
