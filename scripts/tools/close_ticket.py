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
from workspace_config import load_workspace

# ── Helpers ───────────────────────────────────────────────────────────────────

def _docs_paths(ws_dir: Path) -> list[Path]:
    """Return extra docs roots configured via docs_path in workspace.yaml."""
    try:
        cfg = load_workspace(ws_dir)
    except Exception:
        if (ws_dir / "workspace.yaml").exists():
            print(
                f"WARNING: failed to parse {ws_dir / 'workspace.yaml'} "
                "— workspace tickets will not be searched",
                file=sys.stderr,
            )
        return []
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
    """Return list of unchecked AC lines within the Acceptance Criteria section."""
    ac_header = re.search(r"^## Acceptance Criteria\s*$", content, flags=re.MULTILINE)
    if not ac_header:
        return [ln.strip() for ln in content.splitlines() if re.match(r"\s*-\s+\[ \]", ln)]
    next_section = re.search(r"^## ", content[ac_header.end():], flags=re.MULTILINE)
    ac_end = ac_header.end() + next_section.start() if next_section else len(content)
    ac_block = content[ac_header.end():ac_end]
    return [ln.strip() for ln in ac_block.splitlines() if re.match(r"\s*-\s+\[ \]", ln)]


def _tick_acs(content: str) -> str:
    """Rewrite unchecked '- [ ]' boxes to '- [x]' within the Acceptance Criteria section only."""
    ac_header = re.search(r"^## Acceptance Criteria\s*$", content, flags=re.MULTILINE)
    if not ac_header:
        return content
    next_section = re.search(r"^## ", content[ac_header.end():], flags=re.MULTILINE)
    ac_end = ac_header.end() + next_section.start() if next_section else len(content)
    ac_block = content[ac_header.end():ac_end]
    ticked = re.sub(r"^(\s*-)\s+\[ \]", r"\1 [x]", ac_block, flags=re.MULTILINE)
    return content[:ac_header.end()] + ticked + content[ac_end:]


def _update_frontmatter(content: str, session: str) -> str:
    today = date.today().isoformat()
    content = re.sub(r"^(status:\s*)open\s*$", r"\1closed", content, flags=re.MULTILINE)
    content = re.sub(r"^(closed:).*$", rf"\1 {session} {today}", content, flags=re.MULTILINE)
    return content


def _replace_resolution(content: str, resolution: str) -> str:
    """Replace the '(Fill in on close.)' placeholder with resolution text.

    Tries a strict match first (handles optional client-visible block).
    Falls back to a permissive search within the ## Resolution section, with a warning.
    """
    strict = re.compile(
        r"(## Resolution\s*\n)"
        r"(?:> \*\*Client-visible:\*\*.*?\n(?:> .*\n)*\n)?"
        r"\(Fill in on close[^)]*\)\s*",
        re.DOTALL,
    )
    if strict.search(content):
        repl = resolution.rstrip() + "\n"
        return strict.sub(lambda m: m.group(1) + repl, content)

    # Permissive fallback: find the placeholder anywhere in the ## Resolution section.
    res_header = re.search(r"## Resolution\s*\n", content)
    if res_header:
        after = content[res_header.end():]
        next_section = re.search(r"\n##\s", after)
        section = after[: next_section.start()] if next_section else after
        fill_m = re.search(r"\(Fill in on close[^)]*\)[^\n]*\n?", section)
        if fill_m:
            print(
                "WARNING: resolution placeholder matched via permissive fallback "
                "— ticket format may be non-standard",
                file=sys.stderr,
            )
            return (
                content[: res_header.end()]
                + section[: fill_m.start()]
                + resolution.rstrip()
                + "\n"
                + section[fill_m.end() :]
                + (after[next_section.start() :] if next_section else "")
            )

    print(
        "ERROR: ## Resolution placeholder '(Fill in on close.)' not found "
        "— ticket format unexpected",
        file=sys.stderr,
    )
    sys.exit(2)


def _atomic_move(ticket_path: Path, dest: Path, content: str) -> None:
    """Write content to dest atomically via os.replace, then remove ticket_path.

    Writes to a tempfile in the same directory as dest first so that os.replace
    (atomic rename) guarantees dest is never a partial write. ticket_path.unlink()
    is outside the critical window — if it fails, dest is already clean.
    """
    tmp = dest.parent / (dest.name + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    try:
        ticket_path.unlink()
    except OSError as exc:
        print(
            f"WARNING: archive written to {dest} but could not remove {ticket_path}: {exc}\n"
            f"  Manual cleanup: rm {ticket_path}",
            file=sys.stderr,
        )
        sys.exit(2)


def _regenerate_index(internal: Path | None) -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "tools" / "generate_ticket_index.py")]
    if internal is not None:
        cmd += [
            "--sessions", str(internal / "sessions.md"),
            "--tickets-dir", str(internal / "tickets"),
            "--output", str(internal / "tickets" / "INDEX.md"),
        ]
    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as exc:
        print(f"WARNING: generate_ticket_index.py failed: {exc}", file=sys.stderr)


def _git_root_for(path: Path) -> tuple[str | None, str]:
    """Return (git_root, stderr). git_root is None when path is not in a git repo.

    Uses path directly if it is a directory, path.parent if it is a file.
    """
    git_cwd = str(path if path.is_dir() else path.parent)
    try:
        result = subprocess.run(
            ["git", "-C", git_cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip(), ""
        return None, result.stderr.strip()
    except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)


def _check_gitignored(paths: list[Path]) -> list[Path]:
    """Return subset of paths that are ignored by git.

    Runs 'git -C <git_root> check-ignore' per git root so files in different repos
    are checked against the correct .gitignore.

    git check-ignore exit codes: 0 = some paths ignored, 1 = none ignored, 128 = git error.
    Fails closed (exits 2) on subprocess errors or git errors so the check cannot be silently bypassed.
    """
    if not paths:
        return []

    from collections import defaultdict
    by_root: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        git_root, git_err = _git_root_for(p)
        if git_root is None:
            # Path is not inside any git repo — cannot check; proceed (staging will catch it)
            continue
        by_root[git_root].append(p)

    ignored: list[Path] = []
    for git_root, root_paths in by_root.items():
        try:
            result = subprocess.run(
                ["git", "-C", git_root, "check-ignore", "--", *[str(p) for p in root_paths]],
                capture_output=True, text=True,
            )
        except (FileNotFoundError, OSError, subprocess.SubprocessError) as exc:
            print(f"ERROR: could not run 'git check-ignore' to validate --files: {exc}", file=sys.stderr)
            sys.exit(2)

        if result.returncode == 0:
            ignored_names = set(result.stdout.splitlines())
            ignored.extend(p for p in root_paths if str(p) in ignored_names)
        elif result.returncode == 1:
            pass  # none ignored in this root — clean
        else:
            # returncode >= 128: git error
            print(
                f"ERROR: 'git check-ignore' failed (exit {result.returncode}) — cannot verify --files paths:\n"
                f"  {result.stderr.strip()}",
                file=sys.stderr,
            )
            sys.exit(2)

    return ignored


def _stage_extra_files(extra_files: list[Path]) -> None:
    """Stage extra_files grouped by their git root. Exit 2 on failure."""
    if not extra_files:
        return
    from collections import defaultdict
    by_root: dict[str, list[str]] = defaultdict(list)
    for ef in extra_files:
        ef_root, ef_err = _git_root_for(ef)
        if ef_root is None:
            err_detail = f"\n  git: {ef_err}" if ef_err else ""
            print(
                f"WARNING: --files path '{ef}' is not in a git repo — stage manually:{err_detail}\n"
                f"  git add -- {ef}",
                file=sys.stderr,
            )
            sys.exit(2)
        by_root[ef_root].append(str(ef))
    try:
        for root, file_paths in by_root.items():
            subprocess.check_call(["git", "-C", root, "add", "--", *file_paths])
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        print(
            "WARNING: failed to stage --files paths — stage manually.\n"
            "  Some paths from earlier repos may already be staged; run 'git reset HEAD' to unstage.",
            file=sys.stderr,
        )
        sys.exit(2)


def _git_stage(
    ticket_path: Path,
    dest: Path,
    internal: Path | None,
) -> None:
    """Stage ticket deletion, archive destination, and INDEX.md via git."""
    if internal is not None:
        index_path = internal / "tickets" / "INDEX.md"
    else:
        index_path = ROOT / "docs" / "tickets" / "INDEX.md"
    paths = [str(ticket_path), str(dest), str(index_path)]
    git_root, git_err = _git_root_for(dest)
    if git_root is None:
        err_detail = f"\n  git: {git_err}" if git_err else ""
        print(
            f"WARNING: ticket moved to archive but git staging failed — stage manually.{err_detail}\n"
            f"  git rm --cached -- {paths[0]}\n"
            f"  git add -- {' '.join(paths[1:])}",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        subprocess.check_call(
            ["git", "-C", git_root, "rm", "--cached", "--ignore-unmatch", "--", str(ticket_path)],
            stdout=subprocess.DEVNULL,
        )
        to_add = [str(p) for p in [dest, index_path] if p.exists()]
        if to_add:
            subprocess.check_call(["git", "-C", git_root, "add", "--", *to_add])
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        print(
            "WARNING: ticket moved to archive but git staging failed — stage manually.\n"
            f"  git -C {git_root} rm --cached -- {paths[0]}\n"
            f"  git -C {git_root} add -- {' '.join(paths[1:])}",
            file=sys.stderr,
        )
        sys.exit(2)


def _warn_unstaged_code(git_root: str | None) -> None:
    """Warn if there are any unstaged or untracked code files in the repo (unrelated files included)."""
    if git_root is None:
        return
    try:
        # Modified tracked files (working tree vs index — unstaged changes only)
        diff_result = subprocess.run(
            ["git", "-C", git_root, "diff", "--name-only"],
            capture_output=True, text=True,
        )
        # New untracked files that haven't been staged
        untracked_result = subprocess.run(
            ["git", "-C", git_root, "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True,
        )
        if diff_result.returncode != 0 and untracked_result.returncode != 0:
            return
        dirty = diff_result.stdout.splitlines() if diff_result.returncode == 0 else []
        untracked = untracked_result.stdout.splitlines() if untracked_result.returncode == 0 else []
        code_files = [p for p in dirty + untracked if not p.endswith(".md")]
        if code_files:
            print(
                "WARNING: no code files staged — pass --files explicitly or commit code separately.",
                file=sys.stderr,
            )
            for p in code_files:
                print(f"  {p}", file=sys.stderr)
    except (subprocess.SubprocessError, OSError):
        pass


# ── Close-the-loop: source SR resolution ─────────────────────────────────────

def _parse_source(content: str) -> tuple[str, str] | None:
    """Return (slug, sr_id) from source: frontmatter field, or None if absent/invalid."""
    m = re.search(r"^source:\s*(\S+)/(SR-\d+)\s*$", content, re.MULTILINE)
    if not m:
        return None
    slug = m.group(1)
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        print(
            f"WARNING: source: field has invalid slug '{slug}' — skipping SR resolution",
            file=sys.stderr,
        )
        return None
    return slug, m.group(2).upper()


def _resolve_source_sr(sr_path: Path, session: str) -> None:
    """Update SR file: status raised/promoted → resolved, resolved_in → S<N>."""
    text = sr_path.read_text(encoding="utf-8")
    if not re.search(r"^status:\s*(raised|promoted)\s*$", text, flags=re.MULTILINE):
        print(
            f"WARNING: SR {sr_path.name} has non-pending status — not overwriting.",
            file=sys.stderr,
        )
        return
    text = re.sub(
        r"(^status:\s*)(raised|promoted)\s*$",
        r"\1resolved",
        text, flags=re.MULTILINE, count=1,
    )
    resolved_in_set = False
    if re.search(r"^resolved_in:", text, flags=re.MULTILINE):
        new_text = re.sub(
            r"(^resolved_in:).*$",
            rf"\1 {session}",
            text, flags=re.MULTILINE, count=1,
        )
        resolved_in_set = new_text != text
        text = new_text
    else:
        new_text = re.sub(
            r"(^harness_ticket:.*$)",
            rf"\1\nresolved_in: {session}",
            text, flags=re.MULTILINE, count=1,
        )
        resolved_in_set = new_text != text
        text = new_text
    if not resolved_in_set:
        print(
            f"WARNING: could not set resolved_in in SR {sr_path.name} — "
            f"missing both resolved_in: and harness_ticket: fields. "
            f"Update resolved_in manually.",
            file=sys.stderr,
        )
    sr_path.write_text(text, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Close a harness ticket in one command.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("ticket_id", metavar="T###", help="Ticket ID to close, e.g. T045")
    res_group = parser.add_mutually_exclusive_group(required=False)
    res_group.add_argument("--resolution", "-r", metavar="TEXT",
                           help="Resolution text (inline)")
    res_group.add_argument("--resolution-file", metavar="PATH",
                           help="Path to a file containing the resolution text")
    gate_group = parser.add_mutually_exclusive_group()
    gate_group.add_argument("--force", action="store_true",
                            help="Close even if some ACs are still unchecked")
    gate_group.add_argument("--tick-acs", action="store_true",
                            help="Mark all unchecked ACs as done and close")
    parser.add_argument("--workspace", metavar="SLUG",
                        help="Workspace slug to search (required when ID is ambiguous)")
    parser.add_argument("--files", nargs="+", metavar="PATH",
                        help="Code/test files to stage together with the archive move")
    parser.add_argument("--path-only", action="store_true",
                        help="Print the ticket file path and exit; no other action taken")
    args = parser.parse_args()

    ticket_id = args.ticket_id.upper()

    if args.path_only:
        if args.resolution or args.resolution_file:
            parser.error("--path-only cannot be combined with --resolution or --resolution-file")
        ticket_path, _ = _find_ticket(ticket_id, args.workspace)
        print(ticket_path)
        sys.exit(0)

    if not args.resolution and not args.resolution_file:
        parser.error("one of the arguments --resolution/-r --resolution-file is required")

    ticket_path, internal = _find_ticket(ticket_id, args.workspace)
    content = ticket_path.read_text(encoding="utf-8")

    # Locate source SR now so we can warn early if it's missing
    sr_source_path: Path | None = None
    source_info = _parse_source(content)
    if source_info:
        slug, sr_id = source_info
        raised_dir = ROOT / "workspaces" / slug / "raised"
        matches = list(raised_dir.glob(f"{sr_id}-*.md")) if raised_dir.is_dir() else []
        if len(matches) == 1:
            sr_source_path = matches[0]
        else:
            print(
                f"WARNING: ticket has source: {slug}/{sr_id} but SR file not found — "
                f"update {raised_dir / f'{sr_id}-*.md'} manually.",
                file=sys.stderr,
            )

    # Resolution text
    if args.resolution_file:
        res_path = Path(args.resolution_file)
        if not res_path.exists():
            print(f"ERROR: --resolution-file '{res_path}' not found", file=sys.stderr)
            sys.exit(1)
        resolution = res_path.read_text(encoding="utf-8").strip()
    else:
        resolution = args.resolution.strip()

    # Validate --files before any destructive operations
    extra_files: list[Path] = []
    if args.files:
        for raw in args.files:
            p = Path(raw)
            if not p.exists():
                print(f"ERROR: --files path '{raw}' does not exist", file=sys.stderr)
                sys.exit(1)
            if not p.is_file():
                print(f"ERROR: --files path '{raw}' is not a regular file", file=sys.stderr)
                sys.exit(1)
            extra_files.append(p)
        ignored = _check_gitignored(extra_files)
        if ignored:
            for p in ignored:
                print(f"ERROR: --files path '{p}' is gitignored — cannot stage", file=sys.stderr)
            sys.exit(1)

    # AC check (--tick-acs rewrites boxes before the gate; --force skips it)
    if args.tick_acs:
        content = _tick_acs(content)
    unchecked = _check_acs(content)
    if unchecked and not args.force:
        print(f"ERROR: {ticket_id} has unchecked ACs — resolve them or use --force:", file=sys.stderr)
        for ln in unchecked:
            print(f"  {ln}", file=sys.stderr)
        sys.exit(1)

    # Derive session and today's date
    session = _current_session(internal)

    # Append session info to resolution (only if not already stamped by a prior run).
    full_resolution = resolution
    if not re.search(r"\bClosed\s+S\d+\s+\d{4}-\d{2}-\d{2}", resolution):
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
    if dest.exists() and not args.force:
        print(f"ERROR: {dest} already exists in archive — ticket may already be closed", file=sys.stderr)
        sys.exit(2)

    # Stage extra_files BEFORE moving the ticket so a staging failure leaves the ticket in open/
    _stage_extra_files(extra_files)

    _atomic_move(ticket_path, dest, content)

    # Resolve source SR (write + stage together with ticket archive)
    if sr_source_path is not None:
        _resolve_source_sr(sr_source_path, session)
        _stage_extra_files([sr_source_path])

    # Regenerate index
    _regenerate_index(internal)

    # Stage ticket deletion, archive, and INDEX (extra_files already staged above)
    _git_stage(ticket_path, dest, internal)
    if not extra_files and sr_source_path is None:
        root, _ = _git_root_for(dest)
        _warn_unstaged_code(root)

    # Extract title for commit message
    title_m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else ticket_id

    try:
        dest_display = dest.relative_to(ROOT)
    except ValueError:
        dest_display = dest

    if internal is not None:
        index_path = internal / "tickets" / "INDEX.md"
    else:
        index_path = ROOT / "docs" / "tickets" / "INDEX.md"
    staged_paths = [dest, index_path] + (extra_files or [])
    if sr_source_path is not None:
        staged_paths.append(sr_source_path)

    print(f"Closed {ticket_id} → {dest_display}")
    for p in staged_paths:
        try:
            print(f"  staged: {p.relative_to(ROOT)}")
        except ValueError:
            print(f"  staged: {p}")
    print()
    print("Suggested commit:")
    print(f'  git commit -m "fix({ticket_id}): {title}"')


if __name__ == "__main__":
    main()
