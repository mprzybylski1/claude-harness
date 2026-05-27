#!/usr/bin/env python3
"""
Reject a workspace→harness concern: stamp the SR file as rejected.

Usage:
    reject_raised_concern.py <slug>/SR-NNN --reason "..."

Updates the SR file: status → rejected, resolved_in → S<N>, and writes
the rejection reason into ## Harness disposition. Refuses if the SR is
already in a terminal status (resolved or rejected).
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
_SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT / "scripts" / "tools"))

_TERMINAL = {"resolved", "rejected"}


def _parse_frontmatter(path: Path) -> tuple[dict, str]:
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
    raised_dir = ROOT / "workspaces" / slug / "raised"
    if not raised_dir.is_dir():
        print(f"ERROR: raised directory not found at {raised_dir}", file=sys.stderr)
        sys.exit(1)
    matches = list(raised_dir.glob(f"{sr_id}-*.md"))
    if not matches:
        print(f"ERROR: {sr_id} not found in {raised_dir}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        print(f"ERROR: multiple files match {sr_id} in {raised_dir}", file=sys.stderr)
        sys.exit(1)
    return matches[0]


def _current_session() -> str:
    cmd = [sys.executable, str(ROOT / "scripts" / "tools" / "current_session.py")]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: current_session.py failed: {exc.stderr.strip()}", file=sys.stderr)
        sys.exit(2)


def _update_sr(sr_path: Path, session: str, reason: str) -> None:
    text = sr_path.read_text(encoding="utf-8")

    # status → rejected
    text = re.sub(
        r"(^status:\s*)\S+\s*$",
        r"\1rejected",
        text,
        flags=re.MULTILINE,
        count=1,
    )

    # resolved_in: — update if present, insert after harness_ticket: if absent
    if re.search(r"^resolved_in:", text, flags=re.MULTILINE):
        text = re.sub(
            r"(^resolved_in:).*$",
            rf"\1 {session}",
            text,
            flags=re.MULTILINE,
            count=1,
        )
    else:
        text = re.sub(
            r"(^harness_ticket:.*$)",
            rf"\1\nresolved_in: {session}",
            text,
            flags=re.MULTILINE,
            count=1,
        )

    # Write reason into ## Harness disposition
    rejection_line = f"Rejected {session} {date.today().isoformat()}. Reason: {reason}"
    placeholder = re.compile(
        r"(## Harness disposition\s*\n)\(Filled by harness[^)]*\)\s*",
        re.DOTALL,
    )
    if placeholder.search(text):
        text = placeholder.sub(lambda m: m.group(1) + rejection_line + "\n", text)
    else:
        disp = re.search(r"(## Harness disposition\s*\n)", text)
        if disp:
            insert_at = disp.end()
            next_sec = re.search(r"\n## ", text[insert_at:])
            if next_sec:
                pos = insert_at + next_sec.start()
                text = text[:pos] + f"\n{rejection_line}\n" + text[pos:]
            else:
                text = text.rstrip("\n") + f"\n\n{rejection_line}\n"
        else:
            text = text.rstrip("\n") + f"\n\n## Harness disposition\n\n{rejection_line}\n"

    sr_path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reject a workspace→harness concern (SR-NNN)."
    )
    parser.add_argument("sr_ref", metavar="<slug>/SR-NNN",
                        help="e.g. scrabble-score/SR-001")
    parser.add_argument("--reason", required=True,
                        help="Why the concern is rejected")
    args = parser.parse_args()

    if "/" not in args.sr_ref:
        print(
            "ERROR: expected <slug>/SR-NNN format\n"
            "Example: reject_raised_concern.py scrabble-score/SR-001 --reason '...'",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_slug, raw_id = args.sr_ref.split("/", 1)
    sr_id = raw_id.upper()
    if not re.fullmatch(r"SR-\d+", sr_id):
        print(f"ERROR: invalid SR ID '{raw_id}' — expected SR-NNN format", file=sys.stderr)
        sys.exit(1)

    sr_path = _find_sr_file(raw_slug, sr_id)
    data, _ = _parse_frontmatter(sr_path)

    status = data.get("status", "")
    if status in _TERMINAL:
        print(
            f"ERROR: SR is already in terminal status '{status}' — cannot reject.\n"
            f"  SR file: {sr_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    session = _current_session()
    _update_sr(sr_path, session, args.reason)

    print(f"Rejected {raw_slug}/{sr_id} in {session}")
    print(f"  SR: {sr_path}")
    print(f"\nStage the file before committing:")
    print(f"  git add {sr_path}")


if __name__ == "__main__":
    main()
