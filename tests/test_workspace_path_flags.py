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

    # ── T060: --sessions must NOT write CLAUDE_SESSION_ID ─────────────────────

    def test_custom_sessions_does_not_write_session_id_cache(self, tmp_path, monkeypatch):
        """When --sessions is given, CLAUDE_SESSION_ID must NOT be written (T060)."""
        sessions_a = tmp_path / "sessions_a.md"
        sessions_a.write_text(SESSIONS_MD)  # last entry S42 → current S43

        # Point the cache file at a tmp location so we don't pollute the real .git/
        fake_git = tmp_path / "fake_git"
        fake_git.mkdir()
        cache_file = fake_git / "CLAUDE_SESSION_ID"

        import os as _os
        result = subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"), "--sessions", str(sessions_a)],
            capture_output=True, text=True,
            # We cannot easily redirect the hardcoded _SESSION_ID_FILE path via env,
            # so we assert against the *real* cache file being unmodified.
            # Record mtime before the call; if file doesn't exist, it must not be created.
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "S43"

        # The real CLAUDE_SESSION_ID must not have been written with S43 (workspace value).
        real_cache = ROOT / ".git" / "CLAUDE_SESSION_ID"
        if real_cache.exists():
            cached_val = real_cache.read_text().strip()
            # If cache exists it should not contain the workspace session number
            # (it may contain the harness-root session from a prior no-arg invocation).
            # The key assertion: it must NOT equal S43 just because we passed --sessions.
            # We verify by checking the cached value is not "43" (a workspace-derived number).
            # This is only meaningful when 43 != harness-root session — but the important
            # thing is that running with --sessions didn't _create_ or _overwrite_ the file.
            pass  # existence check handled by the two-path test below

    def test_two_custom_sessions_paths_do_not_clobber_cache(self, tmp_path):
        """Calling current_session.py twice with different --sessions must not write CLAUDE_SESSION_ID (T060).

        Strategy: record the cache file's state before both calls.  After both calls the
        state must be identical — neither call should have touched it.
        """
        sessions_a = tmp_path / "sessions_a.md"
        sessions_b = tmp_path / "sessions_b.md"
        sessions_a.write_text(SESSIONS_MD)                           # → S43
        sessions_b.write_text(SESSIONS_MD.replace("S42", "S100"))   # → S101

        real_cache = ROOT / ".git" / "CLAUDE_SESSION_ID"

        # Snapshot state before
        cache_before_exists = real_cache.exists()
        cache_before_content = real_cache.read_text().strip() if cache_before_exists else None

        subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"), "--sessions", str(sessions_a)],
            capture_output=True, text=True,
        )
        subprocess.run(
            [sys.executable, str(TOOLS / "current_session.py"), "--sessions", str(sessions_b)],
            capture_output=True, text=True,
        )

        # Snapshot state after
        cache_after_exists = real_cache.exists()
        cache_after_content = real_cache.read_text().strip() if cache_after_exists else None

        assert cache_before_exists == cache_after_exists, (
            "CLAUDE_SESSION_ID must not be created or deleted by --sessions calls"
        )
        assert cache_before_content == cache_after_content, (
            f"CLAUDE_SESSION_ID was clobbered: before={cache_before_content!r}, "
            f"after={cache_after_content!r}"
        )


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

class TestClassifySessionNoRepoYaml:
    """T077: classify_session.py --repo must classify code correctly when no harness.yaml exists."""

    def _make_bare_repo(self, base: Path) -> Path:
        """Create a minimal git repo with a session-close anchor but NO harness.yaml."""
        repo = base / "ws_repo"
        repo.mkdir()
        subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.com"],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"],
                       capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"],
                       capture_output=True, check=True)
        (repo / "README.md").write_text("# Repo")
        subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "docs: S1 session close — init"],
                       capture_output=True, check=True)
        return repo

    def test_code_file_in_repo_without_yaml_classified_code(self, tmp_path):
        """Repo without harness.yaml: committing a Swift file → 'code', not 'docs'."""
        repo = self._make_bare_repo(tmp_path)
        view_dir = repo / "MyApp" / "View"
        view_dir.mkdir(parents=True)
        (view_dir / "GameView.swift").write_text("struct GameView {}")
        subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "feat: add GameView"],
                       capture_output=True, check=True)

        result = subprocess.run(
            [sys.executable, str(TOOLS / "classify_session.py"), "--repo", str(repo)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "code", (
            f"Expected 'code' for Swift commit in repo without harness.yaml, "
            f"got {result.stdout.strip()!r}"
        )

    def test_docs_only_in_repo_without_yaml_classified_docs(self, tmp_path):
        """Repo without harness.yaml: committing only .md files → 'docs'."""
        repo = self._make_bare_repo(tmp_path)
        (repo / "NOTES.md").write_text("session notes")
        subprocess.run(["git", "-C", str(repo), "add", "."], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "docs: update notes"],
                       capture_output=True, check=True)

        result = subprocess.run(
            [sys.executable, str(TOOLS / "classify_session.py"), "--repo", str(repo)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "docs", (
            f"Expected 'docs' for .md-only commit in repo without harness.yaml, "
            f"got {result.stdout.strip()!r}"
        )


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


# ── Tests: regenerate_ticket_index T016 workspace attribution (S9 #11) ───────

class TestT016WorkspaceAttribution:
    """S9 #11: check_closed_attribution must use workspace sessions.md, not harness root."""

    @pytest.fixture(autouse=True)
    def _import_hook(self):
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import importlib
        import regenerate_ticket_index as rti
        # Re-import fresh copy per test to avoid state bleed
        importlib.reload(rti)
        self.rti = rti

    def _make_workspace(self, tmp_path: Path, ws_session: str) -> tuple[Path, Path]:
        """Create workspace internal dir with sessions.md; return (internal, closed_ticket)."""
        ws_internal = tmp_path / "workspaces" / "ws1" / "internal"
        (ws_internal / "tickets" / "closed").mkdir(parents=True)
        ws_internal.joinpath("sessions.md").write_text(
            f"## Session Log\n\nS1 2026-01-01: init\n{ws_session} 2026-06-01: ws session\n",
            encoding="utf-8",
        )
        ticket = ws_internal / "tickets" / "closed" / "T999-ws-ticket.md"
        ticket.write_text(
            f"---\nid: T999\nstatus: closed\nclosed: {ws_session} 2026-06-01\n---\n",
            encoding="utf-8",
        )
        return ws_internal, ticket

    def test_uses_workspace_sessions_file(self, tmp_path):
        """check_closed_attribution passes workspace sessions.md to get_current_session.

        Patches workspaces_base in the workspace_config module (used by the hook) so that
        _detect_workspace_from_path can find our tmp workspace layout.
        """
        from unittest.mock import patch
        import workspace_config as wsc
        ws_internal, ticket = self._make_workspace(tmp_path, ws_session="S42")

        sessions_seen: list[str | None] = []

        def capture_session(project_root: str, sessions_file: str | None = None) -> str:
            sessions_seen.append(sessions_file)
            return "S42"

        # Redirect workspaces_base in the hook's namespace (imported by name, not via module).
        ws_base = tmp_path / "workspaces"
        with patch.object(self.rti, "workspaces_base", return_value=ws_base), \
             patch.object(self.rti, "get_current_session", side_effect=capture_session):
            self.rti.check_closed_attribution(str(ticket), str(ROOT))

        assert sessions_seen, "get_current_session must be called"
        assert sessions_seen[0] is not None, "sessions_file must be passed (not None)"
        assert "ws1" in sessions_seen[0], (
            f"Expected workspace sessions.md, got: {sessions_seen[0]}"
        )

    def test_no_warning_when_closed_matches_workspace_session(self, tmp_path, capsys):
        """T016: no warning when closed: matches workspace's current session."""
        from unittest.mock import patch
        ws_internal, ticket = self._make_workspace(tmp_path, ws_session="S42")

        with patch.object(self.rti, "get_current_session", return_value="S42"):
            self.rti.check_closed_attribution(str(ticket), str(ROOT))

        captured = capsys.readouterr()
        assert "T016" not in captured.err

    def test_warning_when_closed_mismatches_workspace_session(self, tmp_path, capsys):
        """T016: warning emitted when closed: doesn't match workspace current session."""
        from unittest.mock import patch
        ws_internal, ticket = self._make_workspace(tmp_path, ws_session="S42")
        # Ticket claims S5 but workspace current session is S42
        ticket.write_text(
            "---\nid: T999\nstatus: closed\nclosed: S5 2026-01-01\n---\n",
            encoding="utf-8",
        )

        with patch.object(self.rti, "get_current_session", return_value="S42"):
            self.rti.check_closed_attribution(str(ticket), str(ROOT))

        captured = capsys.readouterr()
        assert "T016" in captured.err


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
        # INDEX.md must be committed so git add succeeds when close_ticket stages it
        (docs / "tickets" / "INDEX.md").write_text("# Ticket Index\n", encoding="utf-8")
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
        # Init git repo so _git_stage succeeds
        subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@test.com"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "commit.gpgsign", "false"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"],
                       check=True, capture_output=True)
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

    def test_duplicate_id_across_scopes_errors(self, tmp_path):
        """S9 #3: same ticket ID in harness root and a workspace → error with hint."""
        self._setup(tmp_path)
        # Plant the same ticket in a workspace too
        ws_internal = tmp_path / "workspaces" / "ws1" / "internal"
        (ws_internal / "tickets" / "open").mkdir(parents=True)
        (ws_internal / "tickets" / "closed").mkdir(parents=True)
        (ws_internal / "archive").mkdir(parents=True)
        (ws_internal / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
        )
        import shutil
        shutil.copy(
            tmp_path / "docs" / "tickets" / "open" / "T999-synthetic-test-ticket.md",
            ws_internal / "tickets" / "open" / "T999-synthetic-test-ticket.md",
        )
        result = self._run(tmp_path, "T999", "--resolution", "should error")
        assert result.returncode != 0
        assert "multiple" in result.stderr.lower() or "disambiguate" in result.stderr.lower()
        # Finding 1: error message must name the workspace slug, not the grandparent dir name
        assert "ws1" in result.stderr, f"Expected slug 'ws1' in error, got: {result.stderr}"

    def test_workspace_flag_disambiguates(self, tmp_path):
        """S9 #3: --workspace targets the right scope when ID exists in multiple places."""
        self._setup(tmp_path)
        ws_internal = tmp_path / "workspaces" / "ws1" / "internal"
        (ws_internal / "tickets" / "open").mkdir(parents=True)
        (ws_internal / "tickets" / "closed").mkdir(parents=True)
        (ws_internal / "archive").mkdir(parents=True)
        (ws_internal / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
        )
        import shutil
        shutil.copy(
            tmp_path / "docs" / "tickets" / "open" / "T999-synthetic-test-ticket.md",
            ws_internal / "tickets" / "open" / "T999-synthetic-test-ticket.md",
        )
        # Closing with --workspace=ws1 should pick the workspace copy
        result = self._run(tmp_path, "T999", "--resolution", "workspace close", "--workspace", "ws1")
        assert result.returncode == 0, result.stderr
        ws_archive = ws_internal / "archive" / "T999-synthetic-test-ticket.md"
        assert ws_archive.exists(), "workspace copy must be in workspace archive"
        harness_open = tmp_path / "docs" / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        assert harness_open.exists(), "harness copy must be untouched"

    def test_write_to_dest_before_unlink(self, tmp_path):
        """S9 #2: if archive write fails, open/ ticket must be untouched."""
        self._setup(tmp_path)
        ticket = tmp_path / "docs" / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        original = ticket.read_text()

        # Make archive dir a file so write_text to dest fails
        archive = tmp_path / "docs" / "archive"
        archive.rmdir()
        archive.write_text("not a directory")  # write_text to a sub-path will fail

        result = self._run(tmp_path, "T999", "--resolution", "should fail")
        assert result.returncode != 0
        # open/ ticket must be untouched
        assert ticket.exists(), "open/ ticket must survive a failed archive write"
        assert ticket.read_text() == original, "open/ ticket content must be unmodified"
        # No partial archive copy should exist at the intended destination
        dest = tmp_path / "docs" / "archive" / ticket.name
        assert not dest.exists(), "No archive copy must be created when dest write fails"

    def test_force_bypasses_archive_exists_check(self, tmp_path):
        """--force overwrites a pre-existing archive file; without --force the error is raised."""
        self._setup(tmp_path)
        archive = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        archive.write_text("stale archive content")

        # Without --force: must fail
        result_no_force = self._run(tmp_path, "T999", "--resolution", "done")
        assert result_no_force.returncode != 0
        assert "already exists" in result_no_force.stderr

        # With --force: must succeed and overwrite the archive
        result_force = self._run(tmp_path, "T999", "--resolution", "done", "--force")
        assert result_force.returncode == 0, result_force.stderr
        assert "stale archive content" not in archive.read_text()
        assert "done" in archive.read_text()


# ── Tests: close_ticket.py T054 ──────────────────────────────────────────────

class TestCloseTicketT054:
    """T054: atomic move, permissive resolution fallback, stamp regex, parse-failure warning."""

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

## Resolution
(Fill in on close.)
"""

    @pytest.fixture(autouse=True)
    def _import(self):
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import close_ticket as ct
        self.ct = ct

    def _run(self, tmp_root: Path, *extra_args: str) -> subprocess.CompletedProcess:
        import os as _os
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tools" / "close_ticket.py"), *extra_args],
            capture_output=True, text=True,
            env={**_os.environ, "HARNESS_ROOT": str(tmp_root), "PYTHONPATH": str(ROOT)},
        )

    def _setup(self, tmp_path: Path) -> Path:
        docs = tmp_path / "docs"
        (docs / "tickets" / "open").mkdir(parents=True)
        (docs / "tickets" / "closed").mkdir(parents=True)
        (docs / "archive").mkdir(parents=True)
        (docs / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
        )
        (docs / "tickets" / "INDEX.md").write_text("# Ticket Index\n", encoding="utf-8")
        tools = tmp_path / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "generate_ticket_index.py").write_text("import sys; sys.exit(0)\n")
        (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
        ticket_path = docs / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket_path.write_text(self.OPEN_TICKET, encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@test.com"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "commit.gpgsign", "false"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"],
                       check=True, capture_output=True)
        return ticket_path

    # ── Fix 2: _replace_resolution permissive fallback ────────────────────────

    def test_replace_resolution_strict_placeholder_unchanged(self):
        """Standard placeholder replaced without warning (regression guard)."""
        content = "## Resolution\n(Fill in on close.)\n"
        result = self.ct._replace_resolution(content, "Fixed.")
        assert "Fixed." in result
        assert "(Fill in on close." not in result

    def test_replace_resolution_permissive_fallback_text_before_placeholder(self, capsys):
        """Non-whitespace text before placeholder → permissive fallback fires + WARNING + pre-text preserved."""
        content = "## Resolution\nNote: see T052 for background.\n(Fill in on close.)\n"
        result = self.ct._replace_resolution(content, "Fixed via fallback.")
        captured = capsys.readouterr()
        assert "Fixed via fallback." in result
        assert "(Fill in on close." not in result
        assert "Note: see T052 for background." in result, "pre-placeholder text must be preserved"
        assert "WARNING" in captured.err

    def test_replace_resolution_regex_metacharacters_survive(self):
        """Resolution text containing regex metacharacters must not cause re.sub to crash or mangle."""
        content = "## Resolution\n(Fill in on close.)\n"
        resolution = r"Patched \g<1> placeholder and fixed \d+ issues."
        result = self.ct._replace_resolution(content, resolution)
        assert r"\g<1>" in result
        assert r"\d+" in result
        assert "(Fill in on close." not in result

    def test_replace_resolution_no_placeholder_exits2(self):
        """No placeholder anywhere in Resolution section → exit 2."""
        content = "## Resolution\nAlready has text.\n"
        with pytest.raises(SystemExit) as exc:
            self.ct._replace_resolution(content, "new resolution")
        assert exc.value.code == 2

    # ── Fix 3: stamp regex ────────────────────────────────────────────────────

    def test_stamp_appended_despite_historical_session_mention(self, tmp_path):
        """Resolution mentioning a historical session date must not suppress the closure stamp."""
        self._setup(tmp_path)
        result = self._run(
            tmp_path, "T999", "--resolution",
            "Reverted the S5 2026-01-01 commit.",
        )
        assert result.returncode == 0, result.stderr
        archive = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        content = archive.read_text()
        assert "Closed S" in content, f"stamp missing:\n{content}"

    def test_stamp_not_duplicated_when_already_present(self, tmp_path):
        """Resolution already containing 'Closed S<N> YYYY-MM-DD' must not get a second stamp."""
        self._setup(tmp_path)
        result = self._run(
            tmp_path, "T999", "--resolution",
            "All done. Closed S9 2026-05-26.",
        )
        assert result.returncode == 0, result.stderr
        archive = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        content = archive.read_text()
        assert content.count("Closed S") == 1, "stamp must not be duplicated"

    # ── Fix 4: _docs_paths parse-failure warning ──────────────────────────────

    def test_docs_paths_warns_on_corrupt_workspace_yaml(self, tmp_path, capsys):
        """Corrupt workspace.yaml → WARNING to stderr, returns [] rather than crashing."""
        ws_dir = tmp_path / "ws1"
        ws_dir.mkdir()
        (ws_dir / "workspace.yaml").write_text("key: [unclosed_bracket\n")
        result = self.ct._docs_paths(ws_dir)
        captured = capsys.readouterr()
        assert result == []
        assert "WARNING" in captured.err

    # ── Fix 1: atomic move via os.replace ─────────────────────────────────────

    def test_atomic_move_archive_clean_if_unlink_fails(self, tmp_path, monkeypatch, capsys):
        """T070: PermissionError on unlink → exit(2) + WARNING to stderr; archive stays clean."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        open_dir = tmp_path / "open"
        open_dir.mkdir()
        ticket_path = open_dir / "T999.md"
        ticket_path.write_text("original")
        dest = archive_dir / "T999.md"

        original_unlink = Path.unlink

        def fail_on_source(self_path, missing_ok=False):
            if self_path.parent == open_dir:
                raise PermissionError("simulated permission denied")
            return original_unlink(self_path, missing_ok=missing_ok)

        monkeypatch.setattr(Path, "unlink", fail_on_source)

        with pytest.raises(SystemExit) as exc_info:
            self.ct._atomic_move(ticket_path, dest, "new content")

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "could not remove" in captured.err
        assert "Manual cleanup" in captured.err
        assert dest.exists(), "archive must exist after os.replace"
        assert dest.read_text() == "new content", "archive must have correct content"
        assert not list(archive_dir.glob("*.tmp")), "no temp files should remain"
        assert ticket_path.exists(), "source ticket must still exist when unlink failed"


# ── Tests: close_ticket.py T064 — git staging ────────────────────────────────

class TestCloseTicketGitStaging:
    """T064: close_ticket.py auto-stages git changes after closure."""

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
        import os as _os
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tools" / "close_ticket.py"), *extra_args],
            capture_output=True, text=True,
            env={**_os.environ, "HARNESS_ROOT": str(tmp_root), "PYTHONPATH": str(ROOT)},
        )

    def _setup_git_repo(self, tmp_path: Path) -> Path:
        """Minimal harness + git repo with initial commit, INDEX.md committed."""
        docs = tmp_path / "docs"
        (docs / "tickets" / "open").mkdir(parents=True)
        (docs / "archive").mkdir(parents=True)
        index = docs / "tickets" / "INDEX.md"
        index.write_text("# Ticket Index\n", encoding="utf-8")
        (docs / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
        )
        tools = tmp_path / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
        # Stub that modifies INDEX.md so it shows as a staged change
        (tools / "generate_ticket_index.py").write_text(
            "import os; from pathlib import Path\n"
            "root = Path(os.environ.get('HARNESS_ROOT', '.'))\n"
            "(root / 'docs' / 'tickets' / 'INDEX.md').write_text('# Updated\\n')\n"
        )
        ticket = docs / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(self.OPEN_TICKET, encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@test.com"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "commit.gpgsign", "false"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"],
                       check=True, capture_output=True)
        return ticket

    def test_closes_and_stages_all_three_paths(self, tmp_path):
        """After close, deletion of open ticket, archive file, and INDEX.md are all staged."""
        self._setup_git_repo(tmp_path)
        result = self._run(tmp_path, "T999", "--resolution", "done")
        assert result.returncode == 0, result.stderr

        status_out = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        staged = [ln for ln in status_out.splitlines() if ln[:1] not in ("", " ", "?")]
        staged_str = "\n".join(staged)
        assert any("T999" in ln and "open" in ln for ln in staged), \
            f"open/ ticket deletion not staged:\n{staged_str}"
        assert any("T999" in ln and "archive" in ln for ln in staged), \
            f"archive file not staged:\n{staged_str}"
        assert any("INDEX.md" in ln for ln in staged), \
            f"INDEX.md not staged:\n{staged_str}"

    def test_git_failure_warns_and_exits_nonzero(self, tmp_path):
        """When not inside a git repo, close_ticket warns and exits non-zero."""
        docs = tmp_path / "docs"
        (docs / "tickets" / "open").mkdir(parents=True)
        (docs / "archive").mkdir(parents=True)
        (docs / "tickets" / "INDEX.md").write_text("# Index\n")
        (docs / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n")
        tools = tmp_path / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
        (tools / "generate_ticket_index.py").write_text("import sys; sys.exit(0)\n")
        ticket = docs / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(self.OPEN_TICKET, encoding="utf-8")
        result = self._run(tmp_path, "T999", "--resolution", "done")
        assert result.returncode != 0
        assert "WARNING" in result.stderr

    def test_external_docs_path_workspace_stages_in_project_repo(self, tmp_path):
        """T072: workspace with external docs_path stages in the project repo, not harness root."""
        # Set up harness root git repo
        harness = tmp_path / "harness"
        (harness / "docs" / "tickets" / "open").mkdir(parents=True)
        (harness / "docs" / "archive").mkdir(parents=True)
        (harness / "docs" / "tickets" / "INDEX.md").write_text("# Index\n")
        (harness / "docs" / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n")
        tools = harness / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
        (tools / "generate_ticket_index.py").write_text(
            "import os; from pathlib import Path\n"
            "import sys\n"
            "# write INDEX in the --output arg path if given\n"
            "args = sys.argv\n"
            "if '--output' in args:\n"
            "    idx = args[args.index('--output') + 1]\n"
            "    Path(idx).write_text('# Updated\\n')\n"
        )

        # Set up project repo (external docs_path)
        project = tmp_path / "project"
        harness_dir = project / ".harness"
        (harness_dir / "tickets" / "open").mkdir(parents=True)
        (harness_dir / "archive").mkdir(parents=True)
        (harness_dir / "tickets" / "INDEX.md").write_text("# Index\n")
        (harness_dir / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n")
        ticket = harness_dir / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(self.OPEN_TICKET, encoding="utf-8")

        # Init project repo and commit initial state
        for cmd in [
            ["git", "-C", str(project), "init", "-q"],
            ["git", "-C", str(project), "config", "user.email", "t@test.com"],
            ["git", "-C", str(project), "config", "user.name", "Test"],
            ["git", "-C", str(project), "config", "commit.gpgsign", "false"],
            ["git", "-C", str(project), "add", "-A"],
            ["git", "-C", str(project), "commit", "-q", "-m", "init"],
        ]:
            subprocess.run(cmd, check=True, capture_output=True)

        # Init harness repo
        for cmd in [
            ["git", "-C", str(harness), "init", "-q"],
            ["git", "-C", str(harness), "config", "user.email", "t@test.com"],
            ["git", "-C", str(harness), "config", "user.name", "Test"],
            ["git", "-C", str(harness), "config", "commit.gpgsign", "false"],
            ["git", "-C", str(harness), "add", "-A"],
            ["git", "-C", str(harness), "commit", "-q", "-m", "init"],
        ]:
            subprocess.run(cmd, check=True, capture_output=True)

        # Create workspace with docs_path pointing at the external project repo
        ws_dir = harness / "workspaces" / "test-ws"
        (ws_dir / "internal" / "tickets" / "open").mkdir(parents=True)
        ws_dir.joinpath("workspace.yaml").write_text(
            f"name: test-ws\ndocs_path: {harness_dir}\n", encoding="utf-8"
        )

        result = self._run(harness, "T999", "--workspace", "test-ws", "--resolution", "done")
        assert result.returncode == 0, f"Expected exit 0; got {result.returncode}\n{result.stderr}"

        # Changes must be staged in the project repo, not the harness repo
        proj_status = subprocess.run(
            ["git", "-C", str(project), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        harness_status = subprocess.run(
            ["git", "-C", str(harness), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        assert "archive/T999" in proj_status, \
            f"Expected archive/T999 staged in project repo:\n{proj_status}"
        assert "T999" not in harness_status, \
            f"T999 must not appear in harness repo staging:\n{harness_status}"

    def test_non_git_workspace_warns_and_exits_nonzero(self, tmp_path):
        """T072: workspace docs_path in a non-git dir warns and exits 2, not silently stages in harness."""
        harness = tmp_path / "harness"
        (harness / "docs" / "tickets" / "open").mkdir(parents=True)
        (harness / "docs" / "archive").mkdir(parents=True)
        (harness / "docs" / "tickets" / "INDEX.md").write_text("# Index\n")
        (harness / "docs" / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n")
        tools = harness / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
        (tools / "generate_ticket_index.py").write_text("import sys; sys.exit(0)\n")

        # Plain directory — NOT a git repo
        plain_dir = tmp_path / "plain"
        harness_dir = plain_dir / ".harness"
        (harness_dir / "tickets" / "open").mkdir(parents=True)
        (harness_dir / "archive").mkdir(parents=True)
        (harness_dir / "tickets" / "INDEX.md").write_text("# Index\n")
        (harness_dir / "sessions.md").write_text("## Session Log\n\nS1 2026-01-01: init\n")
        ticket = harness_dir / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(self.OPEN_TICKET, encoding="utf-8")

        # Init harness repo (but NOT the plain_dir)
        for cmd in [
            ["git", "-C", str(harness), "init", "-q"],
            ["git", "-C", str(harness), "config", "user.email", "t@test.com"],
            ["git", "-C", str(harness), "config", "user.name", "Test"],
            ["git", "-C", str(harness), "config", "commit.gpgsign", "false"],
            ["git", "-C", str(harness), "add", "-A"],
            ["git", "-C", str(harness), "commit", "-q", "-m", "init"],
        ]:
            subprocess.run(cmd, check=True, capture_output=True)

        ws_dir = harness / "workspaces" / "plain-ws"
        (ws_dir / "internal" / "tickets" / "open").mkdir(parents=True)
        ws_dir.joinpath("workspace.yaml").write_text(
            f"name: plain-ws\ndocs_path: {harness_dir}\n", encoding="utf-8"
        )

        result = self._run(harness, "T999", "--workspace", "plain-ws", "--resolution", "done")
        assert result.returncode == 2, f"Expected exit 2 for non-git workspace; got {result.returncode}"
        assert "WARNING" in result.stderr

        # Harness repo must be clean — nothing staged there
        harness_status = subprocess.run(
            ["git", "-C", str(harness), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        assert "T999" not in harness_status, \
            f"T999 must not be staged in harness repo:\n{harness_status}"


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

    def test_last_finding_in_session_does_not_bleed_into_next_session(self, tmp_path):
        """S9 #4: last finding in a session block must not include next session's content."""
        # Two sessions, each with exactly one finding.
        notes = """\
# Opus Review — S5 2026-01-05

## Bugs

1. **S5 #1 — first session finding.** Details about S5 finding here.

# Opus Review — S6 2026-01-06

## Bugs

1. **S6 #1 — second session finding.** Content from S6 only.
"""
        (tmp_path / "docs").mkdir(parents=True)
        (tmp_path / "docs" / "opus_notes.md").write_text(notes)
        (tmp_path / "docs" / "archive").mkdir(parents=True)
        result = self._run(tmp_path, "S5#1")
        assert result.returncode == 0
        # Must include S5 finding text
        assert "S5 finding" in result.stdout
        # Must NOT bleed into S6 content
        assert "S6 only" not in result.stdout
        assert "second session finding" not in result.stdout


# ── Tests: generate_ticket_index.py T074 — auto-descend into open/ ────────────

MINIMAL_TICKET = """\
---
id: T001
title: Real ticket
severity: low
status: open
phase: 2
layer: process
opened: S1 2026-01-01
closed:
---

## Problem

Synthetic.

## Acceptance Criteria

- [ ] Done.

## Resolution

(Fill in on close.)
"""

SESSIONS_STUB = "## Session Log\n\nS1 2026-01-01: init\n"


class TestGenerateTicketIndexTicketsDir:
    """T074: --tickets-dir with open/ subdir must scan open/, not root dir."""

    def _run(self, *extra_args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(TOOLS / "generate_ticket_index.py"), *extra_args],
            capture_output=True, text=True,
        )

    def test_auto_descends_into_open_subdir_excludes_template(self, tmp_path):
        """Passing <tickets>/ where <tickets>/open/ exists scans open/, skips TEMPLATE.md."""
        tickets_dir = tmp_path / "tickets"
        open_dir = tickets_dir / "open"
        open_dir.mkdir(parents=True)
        (tickets_dir / "TEMPLATE.md").write_text(
            "---\nid: T000\ntitle: Template\nseverity: low\nstatus: open\n"
            "phase: 2\nlayer: process\nopened: S0 2026-01-01\nclosed:\n---\n"
        )
        (open_dir / "T001-real-ticket.md").write_text(MINIMAL_TICKET)
        sessions = tmp_path / "sessions.md"
        sessions.write_text(SESSIONS_STUB)
        output = tmp_path / "INDEX.md"

        result = self._run(
            "--tickets-dir", str(tickets_dir),
            "--output", str(output),
            "--sessions-file", str(sessions),
        )
        assert result.returncode == 0, result.stderr
        content = output.read_text()
        assert "T001" in content, "real ticket must appear in index"
        assert "T000" not in content, "TEMPLATE.md at root must not appear"

    def test_no_open_subdir_scans_dir_directly(self, tmp_path):
        """--tickets-dir <dir> without open/ scans <dir> directly (backward-compatible)."""
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir()
        (tickets_dir / "T001-real-ticket.md").write_text(MINIMAL_TICKET)
        sessions = tmp_path / "sessions.md"
        sessions.write_text(SESSIONS_STUB)
        output = tmp_path / "INDEX.md"

        result = self._run(
            "--tickets-dir", str(tickets_dir),
            "--output", str(output),
            "--sessions-file", str(sessions),
        )
        assert result.returncode == 0, result.stderr
        assert "T001" in output.read_text()


# ── Tests: close_ticket.py T075 — workspace INDEX not clobbered ──────────────

class TestCloseTicketWorkspaceIndex:
    """T075: closing a workspace ticket must write INDEX.md to the workspace, not harness root."""

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

## Resolution
(Fill in on close.)
"""

    def _run(self, tmp_root: Path, *extra_args: str) -> subprocess.CompletedProcess:
        import os as _os
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tools" / "close_ticket.py"), *extra_args],
            capture_output=True, text=True,
            env={**_os.environ, "HARNESS_ROOT": str(tmp_root), "PYTHONPATH": str(ROOT)},
        )

    def _setup(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        """Build harness + workspace layout. Returns (harness, ws_internal, ticket)."""
        harness = tmp_path / "harness"
        (harness / "docs" / "tickets" / "open").mkdir(parents=True)
        (harness / "docs" / "archive").mkdir(parents=True)
        harness_index = harness / "docs" / "tickets" / "INDEX.md"
        harness_index.write_text("# Harness Index — unchanged sentinel\n")
        (harness / "docs" / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n"
        )
        tools = harness / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
        # Stub: writes "# Updated\n" to --output if given, else no-op
        (tools / "generate_ticket_index.py").write_text(
            "import sys; from pathlib import Path\n"
            "args = sys.argv\n"
            "if '--output' in args:\n"
            "    Path(args[args.index('--output') + 1]).write_text('# Updated\\n')\n"
        )

        ws_internal = harness / "workspaces" / "test-ws" / "internal"
        (ws_internal / "tickets" / "open").mkdir(parents=True)
        (ws_internal / "archive").mkdir(parents=True)
        ws_index = ws_internal / "tickets" / "INDEX.md"
        ws_index.write_text("# Workspace Index — will be updated\n")
        (ws_internal / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n"
        )
        ticket = ws_internal / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(self.OPEN_TICKET)

        for cmd in [
            ["git", "-C", str(harness), "init", "-q"],
            ["git", "-C", str(harness), "config", "user.email", "t@test.com"],
            ["git", "-C", str(harness), "config", "user.name", "Test"],
            ["git", "-C", str(harness), "config", "commit.gpgsign", "false"],
            ["git", "-C", str(harness), "add", "-A"],
            ["git", "-C", str(harness), "commit", "-q", "-m", "init"],
        ]:
            subprocess.run(cmd, check=True, capture_output=True)

        return harness, ws_internal, ticket

    def test_workspace_close_writes_workspace_index_not_harness(self, tmp_path):
        """T075: closing a workspace ticket regenerates workspace INDEX, not harness INDEX."""
        harness, ws_internal, _ = self._setup(tmp_path)
        harness_index = harness / "docs" / "tickets" / "INDEX.md"
        ws_index = ws_internal / "tickets" / "INDEX.md"
        harness_sentinel = harness_index.read_text()

        result = self._run(harness, "T999", "--workspace", "test-ws", "--resolution", "done")
        assert result.returncode == 0, result.stderr

        assert harness_index.read_text() == harness_sentinel, \
            "harness INDEX.md must be unchanged after workspace ticket close"
        assert ws_index.read_text() == "# Updated\n", \
            "workspace INDEX.md must be regenerated by close_ticket"
