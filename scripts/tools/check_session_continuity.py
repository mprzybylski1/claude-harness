#!/usr/bin/env python3
"""
check_session_continuity.py — advisory session-start guard for numbering collisions (T165).

The session number S<N> is derived from the last Session Log entry in sessions.md
(`current_session.py` returns last_logged + 1). If a PRIOR session created tickets
stamped `opened: S<N>` but never wrote its log line (abandoned, or closed without
`/session-close`), the next session re-derives the SAME S<N> — a silent collision
that conflates two distinct work-sessions in the audit trail (the exact failure that
produced the ghost S30: T157–T160).

This check is meant to run at session start (before this session creates any S<N>
work). At that point the number has already advanced past the last LOGGED session,
so any existing ticket stamped `opened: S<N>` must come from a prior, unlogged
session — i.e. the collision. It scans open + archived tickets for `opened: S<N>`
and warns on any hit. It is advisory: it prints a warning for `/session-start` to
surface and always exits 0 (empty output when clean). It does NOT change the
numbering algorithm — the operator reconciles (placeholder log entry, or
accept-and-note in this session's close).

(No date filter: a date-based "is this today's work" guard breaks for sessions that
span midnight — the own-tickets would be dated yesterday and mis-flagged. Since the
intended caller runs before any S<N> ticket exists, an exact session-number match is
both sufficient and correct.)

Usage (defaults to harness paths; pass overrides for a workspace):
    python scripts/tools/check_session_continuity.py
    python scripts/tools/check_session_continuity.py \
        --sessions <INTERNAL>/sessions.md \
        --tickets-dir <INTERNAL>/tickets/open \
        --archive-dir <INTERNAL>/archive
"""
from __future__ import annotations

import argparse
import contextlib
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
import current_session  # single source of truth for the number derivation

_OPENED_RE = re.compile(r"^opened:\s*S(\d+)\s+(\d{4}-\d{2}-\d{2})", re.MULTILINE)
_ID_RE = re.compile(r"^id:\s*(T\d+)", re.MULTILINE)


def _derive_session(sessions_path: Path) -> int | None:
    """Return the session number this session will use, or None if undeterminable.

    Reuses current_session.get_current_session (suppressing its error/exit on an
    empty or missing log) so the advisory check stays silent rather than failing."""
    if not sessions_path.exists():
        return None
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            return current_session.get_current_session(sessions_path)
    except SystemExit:
        return None


def _scan(dirs: list[Path], n: int) -> list[tuple[str, str]]:
    """Return (ticket_id, date) for every ticket stamped `opened: S<n>`."""
    hits: list[tuple[str, str]] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("T*.md")):
            text = p.read_text(encoding="utf-8", errors="replace")
            m = _OPENED_RE.search(text)
            if not m:
                continue
            session, dt = int(m.group(1)), m.group(2)
            if session == n:
                idm = _ID_RE.search(text)
                tid = idm.group(1) if idm else p.name.split("-")[0]
                hits.append((tid, dt))
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sessions", default=str(ROOT / "docs" / "sessions.md"))
    ap.add_argument("--tickets-dir", default=str(ROOT / "docs" / "tickets" / "open"))
    ap.add_argument("--archive-dir", default=str(ROOT / "docs" / "archive"))
    args = ap.parse_args(argv)

    n = _derive_session(Path(args.sessions))
    if n is None:
        return 0

    hits = _scan([Path(args.tickets_dir), Path(args.archive_dir)], n)
    if not hits:
        return 0

    print(f"WARNING: session-number collision — S{n} is the number this session will use,")
    print(f"but it is already stamped on {len(hits)} ticket(s) opened by an earlier session:")
    for tid, dt in hits:
        print(f"  {tid}  (opened: S{n} {dt})")
    print(f"A prior session used S{n} without writing its Session Log line. Reconcile:")
    print(f"  - add a placeholder Session Log entry for the abandoned session, or")
    print(f"  - accept the conflation and note it explicitly in this session's close.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
