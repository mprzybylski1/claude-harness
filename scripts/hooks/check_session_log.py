#!/usr/bin/env python3
"""
Stop hook: verify session hygiene before the session ends.

Four independent checks run on every session stop:

Check 1 — Ticket attribution (always runs):
  For every ticket file newly moved into docs/tickets/closed/ since main,
  verify its `closed:` YAML frontmatter field starts with the session ID
  found in the Active Work header of docs/sessions.md.
  Exits 1 if any mismatch is found.

Check 2 — Session log (runs only when core Python files were changed):
  Verify that docs/sessions.md Session Log has an entry for today.
  Exits 1 if sessions.md was not updated.

Check 3 — No unstaged code changes (always runs):
  Verify that no tracked code files have unstaged modifications.
  Exits 1 if any TRACKED_PREFIXES file has worktree changes not yet staged,
  reminding the agent to commit per-ticket before session-close.

Check 4 — Uncommitted research result artefacts (always runs):
  Scan research/results/ for untracked *.json / *.md files tagged with the
  current session ID (e.g. *S127*.json). If any exist, the evidence chain
  for gate decisions is not in version control.
  Exits 1 with instructions to commit before session-close. (T166)

Exits 0 to allow session to end.
Exits 1 with an error message to block session end and prompt the agent to fix.
"""
import datetime
import re
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))
from workspace_config import active_workspace_dir, active_workspace, all_repos as _all_repos

TRACKED_PREFIXES = (
    "core/",
    "execution/",
    "strategies/",
    "tests/",
    "data/",
    "infra/",
    "research/",
    "main.py",
)

SESSIONS_MD = "docs/sessions.md"
CLOSED_TICKETS_DIR = "docs/tickets/closed"


def _resolve_paths(project_root: str) -> tuple[str, str]:
    """Return (sessions_md_path, closed_tickets_dir) based on workspace context."""
    ws_dir = active_workspace_dir()
    if ws_dir:
        sessions = str(ws_dir / "internal" / "sessions.md")
        closed = str(ws_dir / "internal" / "tickets" / "closed")
    else:
        sessions = os.path.join(project_root, SESSIONS_MD)
        closed = os.path.join(project_root, CLOSED_TICKETS_DIR)
    return sessions, closed


def run(cmd: list[str], cwd: str) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.stdout.strip()


def parse_porcelain(output: str) -> list[str]:
    """Extract file paths from git status --porcelain output."""
    files = []
    for line in output.splitlines():
        if len(line) >= 3:
            path = line[3:].split(" -> ")[-1].strip()
            files.append(path)
    return files


# ---------------------------------------------------------------------------
# Check 1: Ticket attribution
# ---------------------------------------------------------------------------

def extract_session_id_from_active_work(sessions_content: str) -> str | None:
    """
    Parse the session ID from the Active Work header.

    Looks for a line like:  **S36 — ...**  or  **S36 2026-04-11 — ...**
    Returns 'S36' (or None if not found).
    """
    match = re.search(r'\*\*(S\d+)[\s\-—]', sessions_content)
    if match:
        return match.group(1)
    return None


def _parse_newly_closed_paths(git_diff_output: str, closed_dir: str) -> list[str]:
    """
    Parse `git diff --name-status` output and return paths of files that were
    Added (A) or Renamed-into (R) inside closed_dir.

    Handles both:
      A\tdocs/tickets/closed/T036-foo.md
      R100\tdocs/tickets/open/T036-foo.md\tdocs/tickets/closed/T036-foo.md
    """
    paths = []
    for line in git_diff_output.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("A") and len(parts) >= 2:
            path = parts[1]
            if path.startswith(closed_dir):
                paths.append(path)
        elif status.startswith("R") and len(parts) >= 3:
            path = parts[2]
            if path.startswith(closed_dir):
                paths.append(path)
    return paths


def get_newly_closed_ticket_paths(project_root: str, sessions_path: str, closed_dir: str) -> list[str]:
    """
    Return paths of ticket files newly moved into closed/ that belong to the
    current session:

    1. Tickets moved IN the most recent commit that touched sessions.md
       (i.e. the session-close commit).  This catches wrong attribution written
       by session-close itself.
    2. Tickets in uncommitted staged changes (pre-commit, for interactive use).

    Intentionally excludes tickets moved in earlier commits on this branch —
    those were validated at their own session-close time and would cause false
    positives if diffed against main (since the whole closed/ dir is new on
    this branch vs main).
    """
    # Part 1: tickets moved inside the session-close commit
    sessions_commit = run(
        ["git", "log", "--follow", "-1", "--format=%H", "--", sessions_path],
        cwd=project_root,
    )
    committed: list[str] = []
    if sessions_commit:
        diff_output = run(
            ["git", "diff-tree", "--no-commit-id", "-r", "--name-status",
             sessions_commit, "--", closed_dir + "/"],
            cwd=project_root,
        )
        committed = _parse_newly_closed_paths(diff_output, closed_dir)

    # Part 2: tickets staged but not yet committed
    staged_output = run(
        ["git", "diff", "--cached", "--name-status", "--",
         closed_dir + "/"],
        cwd=project_root,
    )
    staged = _parse_newly_closed_paths(staged_output, closed_dir)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for p in committed + staged:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


def _read_closed_field(file_path: str) -> str | None:
    """Read the `closed:` YAML frontmatter field from a ticket file."""
    try:
        with open(file_path) as f:
            content = f.read()
    except OSError:
        return None
    match = re.search(r'^closed:\s*(\S.*?)?\s*$', content, re.MULTILINE)
    if match:
        return match.group(1) or ""
    return None


def check_ticket_attribution(
    project_root: str,
    session_id: str,
    newly_closed_paths: list[str],
) -> list[str]:
    """
    For each newly closed ticket, verify its `closed:` field starts with session_id.
    Returns a list of error strings (empty = all good).
    """
    errors = []
    for rel_path in newly_closed_paths:
        full_path = os.path.join(project_root, rel_path)
        closed_value = _read_closed_field(full_path)
        if closed_value is None:
            errors.append(
                f"  {rel_path}: could not read closed: field"
            )
        elif not closed_value:
            errors.append(
                f"  {rel_path}: closed: is empty (expected to start with {session_id!r})"
            )
        elif not closed_value.startswith(session_id):
            errors.append(
                f"  {rel_path}: closed: {closed_value!r} (expected to start with {session_id!r})"
            )
    return errors


def run_attribution_check(project_root: str) -> list[str]:
    """
    Full attribution check pipeline.
    Returns list of error strings; empty list = pass.
    """
    sessions_path, closed_dir = _resolve_paths(project_root)
    if not os.path.exists(sessions_path):
        return []

    with open(sessions_path) as f:
        sessions_content = f.read()

    session_id = extract_session_id_from_active_work(sessions_content)
    if not session_id:
        # No Active Work header found — docs-only or question-only session; skip.
        return []

    newly_closed = get_newly_closed_ticket_paths(project_root, sessions_path, closed_dir)
    if not newly_closed:
        return []

    return check_ticket_attribution(project_root, session_id, newly_closed)


# ---------------------------------------------------------------------------
# Check 2: Session log
# ---------------------------------------------------------------------------

def run_session_log_check(project_root: str, all_changed: set[str]) -> bool:
    """
    Returns True if the session log check passes (or is not applicable).
    Prints an error message and returns False if it fails.
    """
    has_core_changes = any(
        any(f.startswith(p) or f == p.rstrip("/") for p in TRACKED_PREFIXES)
        for f in all_changed
        if f.endswith(".py")
    )

    if not has_core_changes:
        return True

    sessions_path, _ = _resolve_paths(project_root)
    # Compute relative path; workspace internal/ files are gitignored so this
    # check typically falls through to the content-based fallback below.
    try:
        sessions_rel = str(Path(sessions_path).relative_to(project_root))
    except ValueError:
        sessions_rel = SESSIONS_MD

    # Check if sessions.md was modified (git-visible path)
    if sessions_rel in all_changed or sessions_path in all_changed:
        return True

    # Last resort: check if sessions.md content has today's date in Session Log
    if os.path.exists(sessions_path):
        with open(sessions_path) as f:
            content = f.read()
        today = datetime.date.today().isoformat()
        if "## Session Log" in content:
            log_section = content.split("## Session Log", 1)[1]
            if today in log_section:
                return True

    today = datetime.date.today().isoformat()
    print(
        f"\n[STOP HOOK] Core Python files were modified but {sessions_rel} "
        f"has no Session Log entry for today ({today}).\n"
        f"\nUpdate {sessions_rel} before ending the session:\n"
        f"  1. Update the 'Active Work' section with what changed.\n"
        f"  2. Append to 'Session Log': S[N] {today}: <one-line summary>\n",
        file=sys.stderr,
    )
    return False


# ---------------------------------------------------------------------------
# Check 3: No unstaged code changes
# ---------------------------------------------------------------------------

def check_unstaged_code_changes(project_root: str) -> list[str]:
    """
    Return paths of tracked code files that have unstaged worktree modifications.

    In workspace context: checks each declared workspace repo for unstaged .py files.
    At harness root: checks TRACKED_PREFIXES in the harness git.
    """
    ws = active_workspace()
    if ws:
        unstaged = []
        for repo in _all_repos(ws):
            repo_path = Path(repo["path"]).expanduser().resolve()
            if not repo_path.exists():
                continue
            porcelain_out = run(["git", "status", "--porcelain"], cwd=str(repo_path))
            for line in porcelain_out.splitlines():
                if len(line) < 4:
                    continue
                if line[1] not in ("M", "D"):
                    continue
                path = line[3:].split(" -> ")[-1].strip()
                if path.endswith(".py"):
                    repo_name = repo.get("name", repo_path.name)
                    unstaged.append(f"{repo_name}/{path}")
        return unstaged

    porcelain_out = run(["git", "status", "--porcelain"], cwd=project_root)
    unstaged = []
    for line in porcelain_out.splitlines():
        if len(line) < 4:
            continue
        worktree_status = line[1]
        if worktree_status not in ("M", "D"):
            continue
        path = line[3:].split(" -> ")[-1].strip()
        if any(path.startswith(p) or path == p.rstrip("/") for p in TRACKED_PREFIXES):
            unstaged.append(path)
    return unstaged


# ---------------------------------------------------------------------------
# Check 4: Uncommitted research result artefacts (T166)
# ---------------------------------------------------------------------------

RESEARCH_RESULTS_DIR = "research/results"


def check_uncommitted_research_artefacts(project_root: str, session_id: str) -> list[str]:
    """
    Find untracked research/results/ files tagged with the current session.
    Returns list of warning strings (empty = all good).
    Only flags files with the current session tag to avoid false positives from
    artefacts committed in previous sessions that are new on this branch.
    """
    if not session_id:
        return []
    if active_workspace_dir() is not None:
        return []  # research/results/ is harness-specific; skip in workspace context

    results_dir = os.path.join(project_root, RESEARCH_RESULTS_DIR)
    if not os.path.exists(results_dir):
        return []

    porcelain_out = run(
        ["git", "status", "--porcelain", "--", RESEARCH_RESULTS_DIR + "/"],
        cwd=project_root,
    )

    warnings = []
    for line in porcelain_out.splitlines():
        if len(line) < 4:
            continue
        xy_status = line[:2]
        path = line[3:].split(" -> ")[-1].strip()
        filename = os.path.basename(path)
        if session_id not in filename:
            continue
        if not (filename.endswith(".json") or filename.endswith(".md")):
            continue
        if "?" in xy_status:
            warnings.append(f"  {path} (untracked)")
        elif xy_status[1] in ("M", "D"):
            warnings.append(f"  {path} (modified, not staged)")
        elif xy_status[0] in ("M", "A", "D", "R") and xy_status[1] == " ":
            warnings.append(f"  {path} (staged but not committed)")
    return warnings


# ---------------------------------------------------------------------------
# Check 5: Overwritten research result artefacts (T178)
# ---------------------------------------------------------------------------


def check_overwritten_research_artefacts(project_root: str, session_id: str) -> list[str]:
    """
    Warn if any research/results/*.json was committed more than once in git
    history with the current session tag — indicating a silent overwrite that
    breaks the evidence chain (T178).

    A file with session_id in its name that appears in ≥2 commits was overwritten:
    an earlier run was committed, then a later run committed different content to
    the same filename. The earlier run's data is no longer at HEAD.

    This check is belt-and-suspenders — write_result() now raises FileExistsError
    before any overwrite can occur. This check catches legacy overwrites already in
    history, or any bypass that gets past the runtime guard.
    """
    if not session_id:
        return []
    if active_workspace_dir() is not None:
        return []  # research/results/ is harness-specific; skip in workspace context

    results_dir = os.path.join(project_root, RESEARCH_RESULTS_DIR)
    if not os.path.exists(results_dir):
        return []

    warnings = []
    try:
        for fname in sorted(os.listdir(results_dir)):
            if not fname.endswith(".json"):
                continue
            if session_id not in fname:
                continue
            log_out = run(
                ["git", "log", "--oneline", "--", f"{RESEARCH_RESULTS_DIR}/{fname}"],
                cwd=project_root,
            )
            commits = [line for line in log_out.splitlines() if line.strip()]
            if len(commits) > 1:
                warnings.append(
                    f"  {RESEARCH_RESULTS_DIR}/{fname} "
                    f"({len(commits)} commits — earlier content overwritten; "
                    f"use --run-tag on future runs to prevent this)"
                )
    except Exception as exc:
        print(f"  [check_overwritten_research_artefacts] git log failed: {exc}", file=sys.stderr)
    return warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    project_root = str(ROOT)

    # Check 1: Ticket attribution (independent of Python changes)
    attribution_errors = run_attribution_check(project_root)
    if attribution_errors:
        session_id = "(unknown)"
        sessions_path, _ = _resolve_paths(project_root)
        if os.path.exists(sessions_path):
            with open(sessions_path) as f:
                sid = extract_session_id_from_active_work(f.read())
                if sid:
                    session_id = sid
        print(
            f"\n[STOP HOOK] Ticket attribution mismatch — "
            f"closed: field does not match Active Work session {session_id!r}:\n",
            file=sys.stderr,
        )
        for err in attribution_errors:
            print(err, file=sys.stderr)
        print(
            f"\nFix the closed: fields to say '{session_id} YYYY-MM-DD' "
            f"before ending the session.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check 2: Session log (only when core Python was changed)
    committed_out = run(["git", "diff", "main...HEAD", "--name-only"], cwd=project_root)
    committed_files = [f for f in committed_out.splitlines() if f]

    porcelain_out = run(["git", "status", "--porcelain"], cwd=project_root)
    uncommitted_files = parse_porcelain(porcelain_out)

    all_changed = set(committed_files + uncommitted_files)

    if not run_session_log_check(project_root, all_changed):
        sys.exit(1)

    # Check 3: No unstaged code changes
    unstaged = check_unstaged_code_changes(project_root)
    if unstaged:
        print(
            "\n[STOP HOOK] Unstaged code changes detected — commit per-ticket before session-close:\n",
            file=sys.stderr,
        )
        for path in unstaged:
            print(f"  {path}", file=sys.stderr)
        print(
            "\nCommit these files now (one commit per ticket), then re-run session-close.\n"
            "See CLAUDE.md 'Commit Discipline' and session-close/SKILL.md for the pattern.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check 4: Uncommitted research result artefacts
    # Use current_session.py (not sessions.md Active Work header, which lags one session).
    current_session_script = os.path.join(project_root, "scripts", "tools", "current_session.py")
    session_id_for_artefacts = None
    if os.path.exists(current_session_script):
        raw = run(["python3", current_session_script], cwd=project_root)
        if raw.startswith("S"):
            session_id_for_artefacts = raw
        else:
            print(
                f"\n[STOP HOOK] current_session.py returned unexpected output: {raw!r}\n"
                "Cannot determine session ID for artefact check. "
                "Fix current_session.py or commit artefacts manually before session-close.\n",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(
            "\n[STOP HOOK] scripts/tools/current_session.py not found — "
            "cannot verify research/results/ artefacts are committed.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    artefact_warnings = check_uncommitted_research_artefacts(
        project_root, session_id_for_artefacts or ""
    )
    if artefact_warnings:
        print(
            f"\n[STOP HOOK] Uncommitted research result artefacts from "
            f"{session_id_for_artefacts} found in research/results/:\n",
            file=sys.stderr,
        )
        for warn in artefact_warnings:
            print(warn, file=sys.stderr)
        print(
            "\nThese files document gate decisions and must be in version control.\n"
            "Commit before session-close:\n"
            "  git add research/results/\n"
            "  git commit -m 'chore: commit backtest result artefacts'\n"
            "(T166: uncommitted artefacts break the evidence chain for Phase 4 gate decisions)\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check 5: Overwritten research result artefacts (T178)
    overwrite_warnings = check_overwritten_research_artefacts(
        project_root, session_id_for_artefacts or ""
    )
    if overwrite_warnings:
        print(
            f"\n[WARN] Overwritten research result artefacts detected in {session_id_for_artefacts}:\n",
            file=sys.stderr,
        )
        for warn in overwrite_warnings:
            print(warn, file=sys.stderr)
        print(
            "\nEarlier run data is not at HEAD — recoverable via git archaeology only.\n"
            "Backfill with distinct filenames using --run-tag and update ticket resolutions.\n"
            "(T178: overwritten artefacts break the Phase 4 evidence chain)\n",
            file=sys.stderr,
        )
        # Warning only — does not block session-close; the prevention is the write_result guard.

    sys.exit(0)


if __name__ == "__main__":
    main()
