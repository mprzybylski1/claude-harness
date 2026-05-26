"""
Tests for T020 + T022: workspace path flag support in session-start / session-close scripts.

Each test verifies that when a script is invoked with a workspace path flag it reads
from that path, not from the harness-root default.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "scripts" / "tools"

# ── Minimal file fixtures ─────────────────────────────────────────────────────

SESSIONS_MD = """\
# Sessions

## Current Phase & Status

Phase 99 (Testing).

## Active Work

**S000 — test session**

## Session Log

S0 2000-01-01: initial
S42 2026-01-15: test entry
"""

OPUS_NOTES_MD = """\
# Opus Notes

# Opus Review — S42 2026-01-15

## Invariant Violations

None.

## Architectural Concerns

None.

## Suggested Next Session Focus

1. Keep testing.
"""


# ── T020: current_session.py --sessions ───────────────────────────────────────

class TestCurrentSessionFlag:
    def test_reads_from_custom_sessions_path(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        sessions.write_text(SESSIONS_MD)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"), "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "S43"

    def test_custom_path_is_independent_of_harness_root(self, tmp_path):
        # Create a sessions.md with a different session number than harness root
        sessions = tmp_path / "ws_sessions.md"
        sessions.write_text(SESSIONS_MD.replace("S42", "S7"))
        result = subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"), "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "S8"

    def test_missing_custom_sessions_exits_nonzero(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"),
             "--sessions", str(tmp_path / "nonexistent.md")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ── T020: extract_session_brief.py --sessions ─────────────────────────────────

class TestExtractSessionBriefFlag:
    def test_reads_from_custom_sessions_path(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        sessions.write_text(SESSIONS_MD)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_session_brief.py"),
             "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Phase 99" in result.stdout

    def test_custom_path_excludes_harness_root_content(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        # Write content that differs from harness-root sessions.md
        sessions.write_text(SESSIONS_MD.replace("Phase 99", "Phase WORKSPACE-ONLY"))
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_session_brief.py"),
             "--sessions", str(sessions)],
            capture_output=True, text=True,
        )
        assert "WORKSPACE-ONLY" in result.stdout

    def test_missing_custom_sessions_exits_nonzero(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_session_brief.py"),
             "--sessions", str(tmp_path / "nonexistent.md")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ── T020: extract_opus_key_sections.py --opus ─────────────────────────────────

class TestExtractOpusKeySectionsFlag:
    def test_reads_from_custom_opus_path(self, tmp_path):
        opus = tmp_path / "opus_notes.md"
        opus.write_text(OPUS_NOTES_MD)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(opus)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "S42" in result.stdout

    def test_custom_path_excludes_harness_root_content(self, tmp_path):
        opus = tmp_path / "opus_notes.md"
        # Write content with a unique marker
        opus.write_text(OPUS_NOTES_MD.replace("S42 2026-01-15", "S999 2030-06-01"))
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(opus)],
            capture_output=True, text=True,
        )
        assert "S999" in result.stdout

    def test_missing_custom_opus_exits_nonzero(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(tmp_path / "nonexistent.md")],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ── T022: archive_session_log.py --sessions / --archive ──────────────────────

class TestArchiveSessionLogFlags:
    def _make_sessions(self, path: Path, n_entries: int = 80) -> None:
        entries = "\n".join(
            f"S{i} 2026-01-{(i % 28) + 1:02d}: session {i}"
            for i in range(1, n_entries + 1)
        )
        path.write_text(
            "# Sessions\n\n## Current Phase & Status\n\nPhase 1.\n\n"
            "## Active Work\n\nActive.\n\n## Session Log\n\n" + entries + "\n",
            encoding="utf-8",
        )

    def test_reads_from_custom_sessions_path(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        archive = tmp_path / "archive" / "session_log_archive.md"
        self._make_sessions(sessions, n_entries=80)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "archive_session_log.py"),
             "--sessions", str(sessions), "--archive", str(archive),
             "--threshold", "75", "--keep", "30"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert archive.exists(), "archive file should be created"
        content = sessions.read_text()
        # Only 30 entries should remain
        remaining = [ln for ln in content.splitlines() if ln.startswith("S")]
        assert len(remaining) == 30

    def test_does_not_touch_harness_root_sessions(self, tmp_path):
        sessions = tmp_path / "sessions.md"
        archive = tmp_path / "archive" / "log.md"
        self._make_sessions(sessions, n_entries=10)
        harness_sessions = ROOT / "docs" / "sessions.md"
        harness_mtime_before = harness_sessions.stat().st_mtime if harness_sessions.exists() else None
        subprocess.run(
            [sys.executable, str(TOOLS / "archive_session_log.py"),
             "--sessions", str(sessions), "--archive", str(archive)],
            capture_output=True, text=True,
        )
        if harness_mtime_before is not None:
            assert harness_sessions.stat().st_mtime == harness_mtime_before


# ── T022: rotate_opus_notes.py --opus / --archive ────────────────────────────

class TestRotateOpusNotesFlags:
    def _make_opus(self, path: Path, n_sections: int = 3) -> None:
        header = "# Opus Notes\n\n"
        sections = "\n\n".join(
            f"# Opus Review — S{i} 2026-01-{i:02d}\n\n"
            f"## Invariant Violations\n\nNone.\n\n"
            f"## Architectural Concerns\n\nNone.\n"
            for i in range(1, n_sections + 1)
        )
        path.write_text(header + sections + "\n")

    def test_rotates_using_custom_opus_and_archive(self, tmp_path):
        opus = tmp_path / "opus_notes.md"
        archive_dir = tmp_path / "archive"
        self._make_opus(opus, n_sections=3)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "rotate_opus_notes.py"),
             "--opus", str(opus), "--archive", str(archive_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        # After rotation, exactly 1 section should remain
        content = opus.read_text()
        sections = [ln for ln in content.splitlines() if ln.startswith("# Opus Review")]
        assert len(sections) == 1
        # Archive directory should have been created
        assert archive_dir.exists()

    def test_does_not_touch_harness_root_opus(self, tmp_path):
        opus = tmp_path / "opus_notes.md"
        archive_dir = tmp_path / "archive"
        self._make_opus(opus, n_sections=2)
        harness_opus = ROOT / "docs" / "opus_notes.md"
        harness_mtime_before = harness_opus.stat().st_mtime if harness_opus.exists() else None
        subprocess.run(
            [sys.executable, str(TOOLS / "rotate_opus_notes.py"),
             "--opus", str(opus), "--archive", str(archive_dir)],
            capture_output=True, text=True,
        )
        if harness_mtime_before is not None:
            assert harness_opus.stat().st_mtime == harness_mtime_before


# ── T027: classify_session.py --repo ─────────────────────────────────────────

def _make_classify_repo(base: Path, code_paths: list[str] | None = None) -> Path:
    """Create a minimal git repo with a session-close anchor commit."""
    repo = base / "ws_repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.com"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"],
                   capture_output=True, check=True)
    # Optional workspace harness.yaml with custom code_paths
    if code_paths is not None:
        import yaml
        (repo / "harness.yaml").write_text(
            yaml.dump({"code_paths": code_paths, "session_close_prefix": "docs: S"})
        )
        subprocess.run(["git", "-C", str(repo), "add", "harness.yaml"],
                       capture_output=True, check=True)
    # Anchor commit (acts as "last session close")
    (repo / "README.md").write_text("# WS Repo")
    subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "docs: S1 session close — init"],
                   capture_output=True, check=True)
    return repo


class TestClassifySessionRepoFlag:
    def test_docs_only_change_classified_docs(self, tmp_path):
        """A commit touching only docs/ in a workspace repo → 'docs'."""
        repo = _make_classify_repo(tmp_path, code_paths=["app/"])
        (repo / "NOTES.md").write_text("some notes")
        subprocess.run(["git", "-C", str(repo), "add", "NOTES.md"],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "docs: update notes"],
                       capture_output=True, check=True)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "classify_session.py"), "--repo", str(repo)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "docs"

    def test_code_change_classified_code(self, tmp_path):
        """A commit touching app/ (workspace code path) → 'code'."""
        repo = _make_classify_repo(tmp_path, code_paths=["app/"])
        app = repo / "app"
        app.mkdir()
        (app / "main.py").write_text("print('hello')")
        subprocess.run(["git", "-C", str(repo), "add", "app/"], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "feat: add main"],
                       capture_output=True, check=True)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "classify_session.py"), "--repo", str(repo)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "code"

    def test_no_anchor_falls_back_to_code(self, tmp_path):
        """When no session-close commit exists in the repo, prints 'code' conservatively."""
        repo = tmp_path / "fresh_repo"
        repo.mkdir()
        subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.com"],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"],
                       capture_output=True, check=True)
        (repo / "README.md").write_text("init")
        subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"],
                       capture_output=True, check=True)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "classify_session.py"), "--repo", str(repo)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "code"


# ── T029: harness.yaml code_paths includes scripts/ ──────────────────────────

class TestHarnessYamlCodePaths:
    def test_scripts_prefix_triggers_code_classification(self):
        """A scripts/ file must classify as 'code' with the updated harness.yaml."""
        import sys
        sys.path.insert(0, str(TOOLS))
        import harness_config as _hc
        harness = _hc.load()
        prefixes = _hc.code_paths(harness)
        assert any(p == "scripts/" or p.startswith("scripts") for p in prefixes), (
            f"'scripts/' not in code_paths: {prefixes}"
        )


# ── T031: extract_opus_key_sections.py — workspace level-2 header support ────

WORKSPACE_OPUS_NOTES_MD = """\
# Opus Notes — My Project

## Opus Review — S5 2026-03-01

### Invariant Violations

None.

### Architectural Concerns

One concern here.

### Suggested Next Session Focus

1. Fix the thing.
"""


class TestExtractOpusKeySectionsWorkspaceFormat:
    def test_parses_level2_review_header(self, tmp_path):
        """Workspace opus_notes.md uses ## Opus Review (level 2) — must parse correctly."""
        opus = tmp_path / "opus_notes.md"
        opus.write_text(WORKSPACE_OPUS_NOTES_MD)
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(opus)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "S5" in result.stdout
        assert "Invariant Violations" in result.stdout

    def test_error_message_shows_actual_path(self, tmp_path):
        """Error message must name the --opus path, not the hardcoded OPUS_NOTES constant."""
        fake = tmp_path / "no_reviews_here.md"
        fake.write_text("# Opus Notes — Project\n\nNo reviews yet.\n")
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(fake)],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert str(fake) in result.stderr, (
            f"Expected path {fake} in stderr, got: {result.stderr!r}"
        )

    def test_help_flag_exits_zero(self):
        """--help must exit 0 with usage text (Bug C: add_help=False was removing this)."""
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"), "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_parses_level1_review_header(self, tmp_path):
        """Harness-root opus_notes.md uses # Opus Review (level 1) — regression guard."""
        opus = tmp_path / "opus_notes.md"
        opus.write_text(OPUS_NOTES_MD)  # uses level-1 "# Opus Review"
        result = subprocess.run(
            [sys.executable, str(TOOLS / "extract_opus_key_sections.py"),
             "--opus", str(opus)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "S42" in result.stdout
        assert "Invariant Violations" in result.stdout


# ── Tests: regenerate_ticket_index._is_closed_ticket ─────────────────────────

class TestIsClosedTicket:
    """T042: path-component check added in T034 — must accept real closed/ paths and
    reject false positives that contain 'tickets/closed' as a substring only."""

    @pytest.fixture(autouse=True)
    def _import(self):
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import regenerate_ticket_index as rti
        self.fn = rti._is_closed_ticket

    @pytest.mark.parametrize("path,expected", [
        # Happy paths — various closed/ layouts
        ("docs/tickets/closed/T001.md", True),
        ("/abs/harness/docs/tickets/closed/T001.md", True),
        # Workspace layout
        ("workspaces/ws/internal/tickets/closed/T001.md", True),
        # False-positive rejection — 'tickets/closed' only as a substring
        ("/some/tickets-closed-archive/T001.md", False),
        ("docs/tickets/open/T001.md", False),
        ("tickets/T001.md", False),
    ])
    def test_is_closed_ticket(self, path, expected, tmp_path):
        # _is_closed_ticket calls Path.resolve() which hits the filesystem for relative
        # paths; use absolute paths or write a sentinel file so resolve works correctly.
        if not Path(path).is_absolute():
            abs_path = tmp_path / path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.touch()
            path = str(abs_path)
        assert self.fn(path) is expected


# ── Tests: close_ticket.py (T045) ────────────────────────────────────────────

class TestCloseTicket:
    """Round-trip tests for scripts/tools/close_ticket.py."""

    OPEN_TICKET = """\
---
id: T999
title: Synthetic test ticket
severity: low
status: open
phase: 2
layer: tooling
opened: S1 2026-01-01
closed:
---

## Problem

Synthetic.

## Acceptance Criteria

- [x] AC one done
- [x] AC two done

## Resolution
(Fill in on close.)
"""

    def _run(self, tmp_root: Path, *extra_args: str) -> subprocess.CompletedProcess:
        """Run close_ticket.py with HARNESS_ROOT redirected to tmp_root."""
        import os as _os
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tools" / "close_ticket.py"), *extra_args],
            capture_output=True, text=True,
            env={**_os.environ, "HARNESS_ROOT": str(tmp_root), "PYTHONPATH": str(ROOT)},
        )

    def _setup(self, tmp_path: Path) -> Path:
        """Build a minimal harness layout in tmp_path and return the open tickets dir."""
        # Harness structure
        docs = tmp_path / "docs"
        (docs / "tickets" / "open").mkdir(parents=True)
        (docs / "tickets" / "closed").mkdir(parents=True)
        (docs / "archive").mkdir(parents=True)
        (docs / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
        )
        # Stub generate_ticket_index.py so it exits cleanly
        tools = tmp_path / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "generate_ticket_index.py").write_text("import sys; sys.exit(0)\n")
        (tools / "current_session.py").write_text(
            "import sys\nprint('S9')\n"
        )
        # Plant the ticket
        ticket_path = docs / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket_path.write_text(self.OPEN_TICKET, encoding="utf-8")
        return ticket_path

    def test_happy_path_closes_ticket(self, tmp_path):
        """Round-trip: ticket moves to archive with updated frontmatter and resolution."""
        ticket = self._setup(tmp_path)
        result = self._run(tmp_path, "T999", "--resolution", "It worked.")
        assert result.returncode == 0, result.stderr

        archive = tmp_path / "docs" / "archive" / ticket.name
        assert archive.exists(), "ticket must be in archive/"
        assert not ticket.exists(), "ticket must be removed from open/"

        content = archive.read_text()
        assert "status: closed" in content
        assert "closed: S9" in content
        assert "It worked." in content

    def test_unchecked_ac_blocks_closure(self, tmp_path):
        """Ticket with an unchecked AC must be rejected without --force."""
        self._setup(tmp_path)
        # Replace with a version that has unchecked AC
        ticket = tmp_path / "docs" / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(self.OPEN_TICKET.replace("- [x] AC one done", "- [ ] AC one done"))

        result = self._run(tmp_path, "T999", "--resolution", "should fail")
        assert result.returncode != 0
        assert "unchecked" in result.stderr.lower()

    def test_force_bypasses_ac_check(self, tmp_path):
        """--force closes even with unchecked ACs."""
        self._setup(tmp_path)
        ticket = tmp_path / "docs" / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(self.OPEN_TICKET.replace("- [x] AC one done", "- [ ] AC one done"))

        result = self._run(tmp_path, "T999", "--resolution", "forced close", "--force")
        assert result.returncode == 0, result.stderr
        archive = tmp_path / "docs" / "archive" / ticket.name
        assert archive.exists()

    def test_missing_ticket_exits_nonzero(self, tmp_path):
        """Unknown ticket ID exits with a clear error."""
        self._setup(tmp_path)
        result = self._run(tmp_path, "T000", "--resolution", "no such ticket")
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_prints_commit_suggestion(self, tmp_path):
        """Output includes a suggested git commit message."""
        self._setup(tmp_path)
        result = self._run(tmp_path, "T999", "--resolution", "done")
        assert result.returncode == 0
        assert "git commit" in result.stdout
        assert "T999" in result.stdout


# ── Tests: surface_stale_tickets.py (T047) ───────────────────────────────────

class TestSurfaceStaleTickets:
    """T047: missing '## Aging Tickets' section must be treated as clean, not a parse error."""

    @pytest.fixture(autouse=True)
    def _import(self):
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import surface_stale_tickets as sst
        self.parse = sst.parse_aging_section

    def test_no_warning_when_aging_section_absent(self, tmp_path):
        """INDEX.md with no aging section → no parse_warning (T047 regression guard)."""
        index = tmp_path / "INDEX.md"
        index.write_text("## Medium (1)\n\n| T001 | title | Ph2 | tooling | this session |\n")
        result = self.parse(index)
        assert result.parse_warning is None
        assert result.section_found is True
        assert result.tickets == []

    def test_no_warning_on_real_index(self):
        """Current docs/tickets/INDEX.md must parse without any warning."""
        result = self.parse()
        assert result.parse_warning is None

    def test_parse_aging_section_when_present(self, tmp_path):
        """Tickets in the aging section are returned with correct age."""
        index = tmp_path / "INDEX.md"
        index.write_text(
            "## Aging Tickets (open ≥ 10 sessions)\n\n"
            "- **T001** — Old ticket (open 12 sessions, since S1 2026-01-01)\n"
            "- **T002** — Very old (open 55 sessions, since S1 2026-01-01)\n"
        )
        result = self.parse(index, threshold=50)
        assert result.parse_warning is None
        assert result.section_found is True
        assert len(result.tickets) == 1
        assert result.tickets[0][1] == 55  # age is index 1: (ticket_id, age, title)


# ── Tests: extract_carry_forwards.py (T048) ──────────────────────────────────

class TestExtractCarryForwards:
    """T048: carry-forwards must be detected from Opus's actual phrasing patterns."""

    @pytest.fixture(autouse=True)
    def _import(self):
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import extract_carry_forwards as ecf
        self.extract = ecf.extract

    def _opus(self, tmp_path: Path, body: str, session_n: int = 9) -> Path:
        p = tmp_path / "opus_notes.md"
        p.write_text(f"# Opus Review — S{session_n} 2026-05-26\n\n{body}\n")
        return p

    def test_explicit_count_pattern(self, tmp_path):
        """'carry-forward 3 sessions' matches and returns age 3."""
        f = self._opus(tmp_path, "Some item — carry-forward 3 sessions unaddressed.")
        items = self.extract(threshold=2, notes_file=f)
        assert len(items) == 1
        assert items[0][0] == 3

    def test_session_reference_pattern(self, tmp_path):
        """'carry-forward from S7' in an S9 review → age 2."""
        f = self._opus(tmp_path, "[carry-forward from S7 Concern #5] some fix needed.", session_n=9)
        items = self.extract(threshold=2, notes_file=f)
        assert len(items) == 1
        assert items[0][0] == 2

    def test_below_threshold_excluded(self, tmp_path):
        """Age-1 carry-forward is excluded when threshold=2."""
        f = self._opus(tmp_path, "[carry-forward from S8 Concern #1] minor.", session_n=9)
        items = self.extract(threshold=2, notes_file=f)
        assert items == []

    def test_no_carry_forwards_returns_empty(self, tmp_path):
        """Notes with no carry-forward patterns → empty list."""
        f = self._opus(tmp_path, "Everything is great. No issues.")
        items = self.extract(threshold=2, notes_file=f)
        assert items == []

    def test_default_threshold_is_two(self, tmp_path):
        """Default threshold is 2, so a 2-session carry-forward appears by default."""
        f = self._opus(tmp_path, "[carry-forward from S7 Concern #5] fix needed.", session_n=9)
        import extract_carry_forwards as ecf
        items = ecf.extract(notes_file=f)   # uses DEFAULT_THRESHOLD
        assert len(items) == 1


# ── Tests: expand_carry_forward.py (T046) ────────────────────────────────────

class TestExpandCarryForward:
    """T046: expand_carry_forward.py surfaces full Opus finding context by ID."""

    SCRIPT = ROOT / "scripts" / "tools" / "expand_carry_forward.py"

    # Minimal opus_notes content with two numbered findings across two sessions.
    NOTES_CURRENT = """\
# Opus Review — S9 2026-05-26

## Bugs & Implementation Issues

1. **S1 #3 — carry-forward from S7.** Still unaddressed. The boundary check
   in run_static_analysis.py is only at entry.

2. **S9 #1 — NEW.** Some brand-new finding with multiple lines of detail
   explaining the problem in depth.
"""

    NOTES_ARCHIVE = """\
# Opus Review Notes — Archive S0–S9

# Opus Review — S1 2026-05-25

## Bugs & Implementation Issues

1. **S1 #1 (T010) — FIXED.** Some already-fixed thing.

2. **S1 #2 — NOT ADDRESSED.** Another issue entirely.

3. **S1 #3 — NOT ADDRESSED.** `run_static_analysis.py` boundary check is still only
   asserted at script entry, not enforced inside imported check helpers.
   This is a latent Invariant 5 hole.

4. **S1 #4 — NOT ADDRESSED.** Some other issue.
"""

    def _run(self, tmp_root: Path, *args: str) -> subprocess.CompletedProcess:
        import os as _os
        return subprocess.run(
            [sys.executable, str(self.SCRIPT), *args],
            capture_output=True, text=True,
            env={**_os.environ, "HARNESS_ROOT": str(tmp_root), "PYTHONPATH": str(ROOT)},
        )

    def _make_root(self, tmp_path: Path) -> Path:
        (tmp_path / "docs" / "tickets" / "open").mkdir(parents=True)
        (tmp_path / "docs" / "archive").mkdir(parents=True)
        (tmp_path / "docs" / "opus_notes.md").write_text(self.NOTES_CURRENT)
        (tmp_path / "docs" / "archive" / "opus_notes_S0-S9.md").write_text(self.NOTES_ARCHIVE)
        return tmp_path

    def test_finds_finding_in_archive(self, tmp_path):
        root = self._make_root(tmp_path)
        result = self._run(root, "S1#3")
        assert result.returncode == 0
        assert "boundary check" in result.stdout
        assert "Invariant 5" in result.stdout

    def test_case_insensitive_and_spaced_formats(self, tmp_path):
        root = self._make_root(tmp_path)
        for fmt in ("s1#3", "S1 #3", "s1 #3"):
            result = self._run(root, fmt)
            assert result.returncode == 0, f"format {fmt!r} failed"
            assert "boundary check" in result.stdout

    def test_multi_file_shows_source_headers(self, tmp_path):
        """S1 #3 appears in both archive and current notes — both shown."""
        root = self._make_root(tmp_path)
        result = self._run(root, "S1#3")
        assert result.returncode == 0
        assert "[From:" in result.stdout

    def test_not_found_exits_nonzero(self, tmp_path):
        root = self._make_root(tmp_path)
        result = self._run(root, "S99#99")
        assert result.returncode == 1
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    def test_latest_flag_prints_one_occurrence(self, tmp_path):
        root = self._make_root(tmp_path)
        result = self._run(root, "S1#3", "--latest")
        assert result.returncode == 0
        # With --latest only one [From:] block should appear
        assert result.stdout.count("[From:") == 1

    def test_extracts_body_up_to_next_finding(self, tmp_path):
        """Extraction stops before the next numbered finding heading."""
        root = self._make_root(tmp_path)
        result = self._run(root, "S1#3")
        # S1 #4 content should NOT appear in any occurrence
        assert "Some other issue" not in result.stdout
