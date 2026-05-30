"""Tests for T104: raise_for_harness.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "raise_for_harness.py"


_STUB_CURRENT_SESSION = """\
import sys, re
if "--sessions" in sys.argv:
    p = sys.argv[sys.argv.index("--sessions") + 1]
    try:
        txt = open(p).read()
        m = re.findall(r"S(\\d+) ", txt)
        if m:
            print("S" + m[-1])
            sys.exit(0)
    except Exception:
        pass
print("S9")
"""


def _setup(tmp_path: Path, slug: str = "myws", with_ws_sessions: bool = True) -> tuple[Path, Path]:
    """Minimal harness skeleton with one workspace. Returns (harness, ws_dir).

    By default writes a workspace internal/sessions.md (S2) so the fail-closed
    guard in raise_for_harness._current_session is satisfied. Pass
    with_ws_sessions=False to exercise the missing-sessions.md path.
    """
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "sessions.md").write_text(
        "## Session Log\n\nS9 2026-05-27: init\n", encoding="utf-8"
    )
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text(_STUB_CURRENT_SESSION, encoding="utf-8")
    ws_dir = tmp_path / "workspaces" / slug
    ws_dir.mkdir(parents=True)
    (ws_dir / "workspace.yaml").write_text(f"name: {slug}\n", encoding="utf-8")
    if with_ws_sessions:
        _add_workspace_sessions_md(ws_dir, "S2 2026-05-27: ws session")
    return tmp_path, ws_dir


def _add_workspace_sessions_md(ws_dir: Path, last_session_line: str) -> None:
    """Create <ws_dir>/internal/sessions.md with the given last log line."""
    internal = ws_dir / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "sessions.md").write_text(
        f"## Session Log\n\n{last_session_line}\n", encoding="utf-8"
    )


def _run(
    harness: Path, *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or harness),
        env={**_os.environ, "HARNESS_ROOT": str(harness), "PYTHONPATH": str(ROOT)},
    )


class TestRaiseForHarness:

    def test_happy_path_creates_file(self, tmp_path):
        """SR file created in boundary slot with correct frontmatter."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Database timeout bug", "--severity", "high",
                      "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        assert created.exists(), f"File not created at {created}"
        content = created.read_text(encoding="utf-8")
        assert "id: SR-001" in content
        assert "from: myws" in content
        assert "title: Database timeout bug" in content
        assert "severity: high" in content
        assert "status: raised" in content
        assert "harness_ticket:" in content

    def test_required_sections_present(self, tmp_path):
        """File body contains Context, Proposed change, and Harness disposition sections."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Any concern", "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "## Context" in content
        assert "## Proposed change" in content
        assert "## Harness disposition" in content

    def test_file_lands_in_boundary_slot(self, tmp_path):
        """Output path is workspaces/<slug>/raised/<SR>.md, not elsewhere."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Location test", "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        assert created.parent == harness / "workspaces" / "myws" / "raised"

    def test_sequence_number_increments(self, tmp_path):
        """SR-002 allocated when SR-001 already exists in raised/."""
        harness, ws_dir = _setup(tmp_path)
        raised = ws_dir / "raised"
        raised.mkdir()
        (raised / "SR-001-old.md").write_text("---\nid: SR-001\n---\n", encoding="utf-8")

        result = _run(harness, "Second concern", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "id: SR-002" in content

    def test_sequence_scans_archive(self, tmp_path):
        """SR number allocation includes raised/archive/ so archived SRs are never reused."""
        harness, ws_dir = _setup(tmp_path)
        raised = ws_dir / "raised"
        archive = raised / "archive"
        raised.mkdir()
        archive.mkdir()
        (archive / "SR-003-archived.md").write_text("---\nid: SR-003\n---\n", encoding="utf-8")

        result = _run(harness, "After archive gap", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "id: SR-004" in content

    def test_no_workspace_context_exits_nonzero(self, tmp_path):
        """Refuses without --workspace and CWD not inside a workspace directory."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Should fail")  # cwd=harness, not inside workspaces/
        assert result.returncode != 0
        assert "workspace" in result.stderr.lower()

    def test_unknown_workspace_exits_nonzero(self, tmp_path):
        """--workspace with non-existent slug exits non-zero with ERROR."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Bad slug", "--workspace", "does-not-exist")
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_cwd_workspace_detection(self, tmp_path):
        """Auto-detects workspace slug from CWD when inside workspaces/<slug>/."""
        harness, ws_dir = _setup(tmp_path)
        result = _run(harness, "Auto-detected workspace", cwd=ws_dir)
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "from: myws" in content

    def test_filename_slug_from_title(self, tmp_path):
        """Filename follows SR-NNN-<slug>.md pattern with title-derived slug."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Fix the broken widget", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        created = Path(result.stdout.strip())
        assert created.name.startswith("SR-001-")
        assert "fix" in created.name
        assert created.name.endswith(".md")

    def test_archive_dir_created_automatically(self, tmp_path):
        """raised/archive/ is created if it does not exist."""
        harness, ws_dir = _setup(tmp_path)
        result = _run(harness, "Any concern", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        assert (ws_dir / "raised" / "archive").is_dir()


class TestSessionIdSource:
    """T116: SRs stamped with workspace session #, not harness session #."""

    def test_uses_workspace_session_number_when_internal_sessions_md_exists(self, tmp_path):
        """workspace at S5, harness at S9 → SR is stamped S5."""
        harness, ws_dir = _setup(tmp_path)
        _add_workspace_sessions_md(ws_dir, "S5 2026-05-27: ws session")
        result = _run(harness, "Workspace-side concern", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "raised: S5" in content, f"Expected workspace S5, got: {content}"
        assert "raised: S9" not in content

    def test_uses_workspace_session_for_cwd_detected_workspace(self, tmp_path):
        """CWD-detected workspace also gets workspace session number."""
        harness, ws_dir = _setup(tmp_path)
        _add_workspace_sessions_md(ws_dir, "S3 2026-05-26: ws session")
        result = _run(harness, "CWD concern", cwd=ws_dir)
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "raised: S3" in content

    def test_refuses_to_fall_back_when_internal_sessions_md_missing(self, tmp_path):
        """T132: workspace with no sessions.md must NOT fall back to harness session.

        Writing the harness session number into a workspace SR's `raised:`
        frontmatter field would contaminate the workspace audit trail with a
        cross-layer session ID — exactly the workspace↔harness separation
        invariant. Fail closed (exit 2) instead.
        """
        harness, _ = _setup(tmp_path, with_ws_sessions=False)
        result = _run(harness, "Fallback case", "--workspace", "myws")
        assert result.returncode == 2, (
            f"expected exit 2, got {result.returncode}; "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "sessions.md" in result.stderr
        # No SR file should have been created on the fail-closed path.
        sr_files = list((tmp_path / "workspaces" / "myws" / "raised").glob("SR-*.md"))
        assert sr_files == [], f"SR file should not be created on fail-closed: {sr_files}"

    def test_respects_docs_path_override_in_workspace_yaml(self, tmp_path):
        """docs_path in workspace.yaml redirects sessions.md to a custom location."""
        harness, ws_dir = _setup(tmp_path)
        custom_docs = tmp_path / "custom-docs-root"
        custom_docs.mkdir()
        (custom_docs / "sessions.md").write_text(
            "## Session Log\n\nS7 2026-05-28: custom\n", encoding="utf-8"
        )
        (ws_dir / "workspace.yaml").write_text(
            f"name: myws\ndocs_path: {custom_docs}\n", encoding="utf-8"
        )
        result = _run(harness, "Custom docs_path", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "raised: S7" in content


class TestTitleQuoting:
    """T123: titles with colons must survive yaml.safe_load.

    Pre-T123, a title like 'prepare_opus_context.py: exclude X' was written
    unquoted, so yaml.safe_load read 'prepare_opus_context.py' as a mapping
    key and errored on the next colon — causing list_raised_concerns.py to
    silently skip the SR. SR-004..SR-007 (S22 2026-05-28) were all affected.
    """

    def _frontmatter(self, path: Path) -> dict:
        import yaml
        text = path.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        assert len(parts) >= 3, f"missing frontmatter delimiters in {path}"
        return yaml.safe_load(parts[1])

    def test_title_with_colon_round_trips(self, tmp_path):
        harness, _ = _setup(tmp_path)
        title = "prepare_opus_context.py: exclude large text/binary resources"
        result = _run(harness, title, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        data = self._frontmatter(Path(result.stdout.strip()))
        assert data["title"] == title

    def test_title_with_hash_round_trips(self, tmp_path):
        harness, _ = _setup(tmp_path)
        title = "Bug #42 needs handling"
        result = _run(harness, title, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        data = self._frontmatter(Path(result.stdout.strip()))
        assert data["title"] == title

    def test_plain_title_unquoted(self, tmp_path):
        """Backward-compat: titles that don't need quoting stay unquoted."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Database timeout bug", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "title: Database timeout bug\n" in content
        data = self._frontmatter(Path(result.stdout.strip()))
        assert data["title"] == "Database timeout bug"

    def test_title_with_embedded_quote_escaped(self, tmp_path):
        harness, _ = _setup(tmp_path)
        title = 'Strange: with "quotes" inside'
        result = _run(harness, title, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        data = self._frontmatter(Path(result.stdout.strip()))
        assert data["title"] == title


class TestExplicitSession:
    """T139: --session stamps the running session verbatim.

    current_session.py returns last-logged+1, which is correct mid-session (the
    running session's log line is not yet written) but over-counts once the close
    protocol appends that line. SR-011 was raised during the S13 close, after the
    S13 Session Log line existed, so it was mis-stamped S14. The close skill knows
    the running session (captured at Step 0, pre-append) and passes it via
    --session, which is correct regardless of close-flow append ordering.
    """

    def test_explicit_session_overrides_lookup(self, tmp_path):
        # sessions.md last line is S99 — deliberately ≠ the --session value so the
        # test fails if --session were ignored and the lookup path were taken.
        # This is the raise-during-close case: the running session's log line is
        # already appended, so only the explicit value is correct.
        harness, ws_dir = _setup(tmp_path)
        _add_workspace_sessions_md(ws_dir, "S99 2026-05-30: close in progress")
        result = _run(harness, "Raised during close", "--workspace", "myws",
                      "--session", "S13")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "raised: S13" in content, content
        assert "raised: S99" not in content
        assert "raised: S14" not in content

    def test_explicit_session_bypasses_missing_sessions_md(self, tmp_path):
        # An explicit value is a declared input, not a silent default, so it is
        # NOT an Invariant-3 violation and does not require sessions.md to exist.
        harness, _ = _setup(tmp_path, with_ws_sessions=False)
        result = _run(harness, "Explicit despite no sessions.md",
                      "--workspace", "myws", "--session", "S4")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "raised: S4" in content

    def test_invalid_session_rejected(self, tmp_path):
        # Malformed declared value fails closed (exit 2), creates no SR file.
        harness, _ = _setup(tmp_path)
        result = _run(harness, "Bad session", "--workspace", "myws",
                      "--session", "13")
        assert result.returncode == 2, (result.returncode, result.stderr)
        sr_files = list((tmp_path / "workspaces" / "myws" / "raised").glob("SR-*.md"))
        assert sr_files == [], sr_files

    def test_no_session_flag_preserves_lookup(self, tmp_path):
        # Without --session the sessions.md lookup path is unchanged.
        harness, ws_dir = _setup(tmp_path)
        _add_workspace_sessions_md(ws_dir, "S6 2026-05-30: ws")
        result = _run(harness, "No flag", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "raised: S6" in content
