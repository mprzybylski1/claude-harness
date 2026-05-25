#!/usr/bin/env python3
"""
scripts/tools/archive_session_log.py

Archive old Session Log entries from docs/sessions.md when the count exceeds a threshold.

Usage:
    python scripts/tools/archive_session_log.py [--threshold N] [--keep K]

Defaults:
    --threshold 75   Archive when the log exceeds this many entries
    --keep      30   Retain this many recent entries after archiving

Behaviour:
    - Reads docs/sessions.md and counts Session Log entries (lines starting with S<digits>)
    - If count <= threshold: prints "Session log has N entries (threshold M). No action needed."
      and exits 0
    - If count > threshold: moves the oldest (count - keep) entries to
      docs/archive/session_log_archive.md (appended, not overwritten), removes them from
      sessions.md, and prints "Archived N entries; K remain."
    - Idempotent: safe to call repeatedly; only acts when threshold is exceeded
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SESSIONS_FILE = REPO_ROOT / "docs" / "sessions.md"
ARCHIVE_FILE = REPO_ROOT / "docs" / "archive" / "session_log_archive.md"

SESSION_ENTRY_RE = re.compile(r"^S\d+\s")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--threshold", type=int, default=75, help="Archive when log exceeds this many entries (default 75)")
    p.add_argument("--keep", type=int, default=30, help="Entries to retain after archiving (default 30)")
    p.add_argument("--sessions", default=None, metavar="PATH",
                   help="Path to sessions.md (default: harness-root docs/sessions.md)")
    p.add_argument("--archive", default=None, metavar="PATH",
                   help="Path to archive file (default: harness-root docs/archive/session_log_archive.md)")
    return p.parse_args()


def split_session_log(content: str) -> tuple[str, list[str], str]:
    """
    Split sessions.md into (pre_log, entries, post_log).

    pre_log  — everything up to and including the '## Session Log' heading line
    entries  — list of session log lines (each starts with S<digits>)
    post_log — everything after the last entry (should be empty or just a trailing newline)
    """
    lines = content.splitlines(keepends=True)

    # Find the '## Session Log' heading
    log_start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "## Session Log":
            log_start_idx = i
            break

    if log_start_idx is None:
        raise ValueError("Could not find '## Session Log' section in sessions.md")

    pre_log_lines = lines[:log_start_idx + 1]

    # Collect entry lines and anything after
    entries = []
    post_log_lines = []
    in_entries = True
    for line in lines[log_start_idx + 1:]:
        stripped = line.strip()
        if not stripped:
            # Blank lines between entries are skipped; trailing blank after entries falls through
            if entries:
                # We're past the header blank — keep collecting
                pass
            continue
        if SESSION_ENTRY_RE.match(stripped):
            entries.append(stripped)
        else:
            # Non-entry, non-blank content after the log section
            post_log_lines.append(line)
            in_entries = False

    return "".join(pre_log_lines), entries, "".join(post_log_lines)


def main() -> int:
    args = parse_args()
    threshold = args.threshold
    keep = args.keep
    sessions_file = Path(args.sessions) if args.sessions else SESSIONS_FILE
    archive_file = Path(args.archive) if args.archive else ARCHIVE_FILE

    if keep >= threshold:
        print(f"ERROR: --keep ({keep}) must be less than --threshold ({threshold})", file=sys.stderr)
        return 1

    content = sessions_file.read_text(encoding="utf-8")
    pre_log, entries, post_log = split_session_log(content)

    count = len(entries)
    if count <= threshold:
        return 0

    n_to_archive = count - keep
    to_archive = entries[:n_to_archive]
    to_keep = entries[n_to_archive:]

    # Append to archive file
    archive_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_header = f"\n## Archived {timestamp} (entries {to_archive[0].split()[0]}–{to_archive[-1].split()[0]})\n\n"
    archive_block = archive_header + "\n".join(to_archive) + "\n"

    if archive_file.exists():
        with archive_file.open("a", encoding="utf-8") as f:
            f.write(archive_block)
    else:
        archive_file.write_text(
            "# Session Log Archive\n\nOldest entries moved here when the active log exceeds the threshold.\n"
            + archive_block,
            encoding="utf-8",
        )

    # Rewrite sessions.md with only the kept entries
    new_log_section = "\n".join(to_keep) + "\n"
    new_content = pre_log + "\n" + new_log_section
    if post_log:
        new_content += post_log
    sessions_file.write_text(new_content, encoding="utf-8")

    print(f"Archived {n_to_archive} entries; {keep} remain.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
