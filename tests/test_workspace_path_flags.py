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
