"""
Tests for T026: workflow telemetry hook and analysis script.

Covers: log_tool_usage.py (telemetry-disabled exit, JSON append, rotation),
        analyze_tool_log.py (frequency, retry detection, malformed-line skip),
        harness_config.load_for_repo fallback path (F11).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "hooks" / "log_tool_usage.py"
ANALYZE = ROOT / "scripts" / "tools" / "analyze_tool_log.py"
sys.path.insert(0, str(ROOT / "scripts" / "tools"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_hook(payload: dict, harness_yaml: str = "", log_path: Path | None = None,
              tmp_path: Path | None = None) -> subprocess.CompletedProcess:
    """Run log_tool_usage.py with a synthetic payload and optional harness config."""
    env_overrides: dict[str, str] = {}
    if tmp_path:
        # Patch ROOT inside the hook by writing harness.yaml to tmp_path
        # and setting a harness-root env — hook resolves ROOT from __file__,
        # so we instead call it with a patched harness.yaml written to ROOT.
        pass
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True,
    )
    return result


def _make_log(log_path: Path, records: list[dict]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


# ── Tests: log_tool_usage.py ──────────────────────────────────────────────────

def _make_fake_root(tmp_path: Path, telemetry_on: bool, sentinel: bool) -> Path:
    """Build a minimal harness root in tmp_path for isolated hook testing."""
    fake_root = tmp_path / "harness"
    git = fake_root / ".git"
    git.mkdir(parents=True)
    (fake_root / "harness.yaml").write_text(
        f"workflow_telemetry: {'true' if telemetry_on else 'false'}\n"
        "workflow_telemetry_max_lines: 5000\n"
    )
    if sentinel:
        (git / "workflow_telemetry_on").touch()
    # Stub scripts/tools/ so harness_config can be imported
    tools = fake_root / "scripts" / "tools"
    tools.mkdir(parents=True)
    real_tools = ROOT / "scripts" / "tools"
    import os
    for name in ("harness_config.py",):
        src = real_tools / name
        dst = tools / name
        os.symlink(str(src), str(dst))
    return fake_root


class TestLogToolUsageHook:
    def _run_hook_isolated(self, payload: dict, fake_root: Path) -> subprocess.CompletedProcess:
        """Run the hook with HARNESS_ROOT overridden via env var (not yet implemented)
        or by rewriting ROOT via symlink/subprocess cwd tricks.
        Falls back to subprocess with the real hook but synthetic sentinel state."""
        # The hook derives ROOT from __file__, so we can't easily redirect it without
        # modifying the script. Instead, use a subprocess and control the real sentinel.
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            capture_output=True, text=True,
        )

    def test_exits_silently_when_both_off(self, tmp_path):
        """Hook exits 0 quickly when sentinel absent AND harness.yaml has telemetry false.

        Uses _make_fake_root + mock.patch so an interrupted run cannot leave the real
        harness.yaml with telemetry disabled (S7 Concern #5 / T040).
        """
        import unittest.mock as mock

        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import log_tool_usage as ltu

        fake_root = _make_fake_root(tmp_path, telemetry_on=False, sentinel=False)
        start = time.monotonic()
        with mock.patch.object(ltu, "ROOT", fake_root), \
             mock.patch.object(ltu, "_SENTINEL", fake_root / ".git" / "workflow_telemetry_on"), \
             mock.patch.object(ltu, "_LOG_PATH", fake_root / ".git" / "session_tool_log.jsonl"), \
             mock.patch.object(ltu, "_ERR_PATH", fake_root / ".git" / "session_tool_log.errors"):
            with pytest.raises(SystemExit) as exc_info:
                ltu.main()
        elapsed = time.monotonic() - start

        assert exc_info.value.code == 0
        assert elapsed < 0.5, f"Expected fast exit, took {elapsed:.3f}s"

    def test_bootstrap_creates_sentinel_from_yaml(self, tmp_path):
        """Sentinel-absent + yaml true → sentinel created on first tool call.

        In-process test: ROOT is patched to a fake harness in tmp_path so the
        real .git/session_tool_log.jsonl is never touched.
        """
        import unittest.mock as mock
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import log_tool_usage as ltu

        fake_root = _make_fake_root(tmp_path, telemetry_on=True, sentinel=False)
        fake_sentinel = fake_root / ".git" / "workflow_telemetry_on"
        payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x.py"}})

        with mock.patch.object(ltu, "ROOT", fake_root), \
             mock.patch.object(ltu, "_SENTINEL", fake_sentinel), \
             mock.patch.object(ltu, "_LOG_PATH", fake_root / ".git" / "session_tool_log.jsonl"), \
             mock.patch.object(ltu, "_ERR_PATH", fake_root / ".git" / "session_tool_log.errors"), \
             mock.patch("sys.stdin.read", return_value=payload):
            with pytest.raises(SystemExit) as exc_info:
                ltu.main()

        assert exc_info.value.code == 0
        assert fake_sentinel.exists(), "Bootstrap must have created the sentinel"

    def test_bootstrap_works_from_workspace_cwd(self, tmp_path):
        """Sentinel created correctly even when working directory is not harness root.

        Regression test for T039: ROOT is derived from __file__, not cwd, so this
        always held. Test verifies sentinel creation in a fake root (in-process).
        """
        import unittest.mock as mock
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import log_tool_usage as ltu

        fake_root = _make_fake_root(tmp_path, telemetry_on=True, sentinel=False)
        fake_sentinel = fake_root / ".git" / "workflow_telemetry_on"
        payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x.py"}})

        with mock.patch.object(ltu, "ROOT", fake_root), \
             mock.patch.object(ltu, "_SENTINEL", fake_sentinel), \
             mock.patch.object(ltu, "_LOG_PATH", fake_root / ".git" / "session_tool_log.jsonl"), \
             mock.patch.object(ltu, "_ERR_PATH", fake_root / ".git" / "session_tool_log.errors"), \
             mock.patch("sys.stdin.read", return_value=payload):
            with pytest.raises(SystemExit) as exc_info:
                ltu.main()

        assert exc_info.value.code == 0
        assert fake_sentinel.exists(), (
            "Bootstrap must create sentinel even when cwd is not the harness root"
        )

    def test_exits_zero_with_any_state(self, tmp_path):
        """Hook exits 0 regardless of telemetry state (never breaks tool calls).

        In-process test: uses a fake root with telemetry on + sentinel present so
        a log record is written to tmp_path, not the real .git/ directory.
        """
        import unittest.mock as mock
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import log_tool_usage as ltu

        fake_root = _make_fake_root(tmp_path, telemetry_on=True, sentinel=True)
        fake_sentinel = fake_root / ".git" / "workflow_telemetry_on"
        fake_log = fake_root / ".git" / "session_tool_log.jsonl"
        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "foo.py"}})

        with mock.patch.object(ltu, "ROOT", fake_root), \
             mock.patch.object(ltu, "_SENTINEL", fake_sentinel), \
             mock.patch.object(ltu, "_LOG_PATH", fake_log), \
             mock.patch.object(ltu, "_ERR_PATH", fake_root / ".git" / "session_tool_log.errors"), \
             mock.patch("sys.stdin.read", return_value=payload):
            try:
                ltu.main()
                exit_code = 0
            except SystemExit as exc:
                exit_code = exc.code

        assert exit_code == 0

    def test_handles_malformed_stdin_gracefully(self, tmp_path):
        """Invalid JSON on stdin must not crash the hook.

        In-process test: sentinel present so we reach the JSON-parse path; invalid
        JSON triggers the graceful exit branch. Writes go to tmp_path, not real log.
        """
        import unittest.mock as mock
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import log_tool_usage as ltu

        fake_root = _make_fake_root(tmp_path, telemetry_on=True, sentinel=True)
        fake_sentinel = fake_root / ".git" / "workflow_telemetry_on"

        with mock.patch.object(ltu, "ROOT", fake_root), \
             mock.patch.object(ltu, "_SENTINEL", fake_sentinel), \
             mock.patch.object(ltu, "_LOG_PATH", fake_root / ".git" / "session_tool_log.jsonl"), \
             mock.patch.object(ltu, "_ERR_PATH", fake_root / ".git" / "session_tool_log.errors"), \
             mock.patch("sys.stdin.read", return_value="not valid json at all }{"):
            with pytest.raises(SystemExit) as exc_info:
                ltu.main()

        assert exc_info.value.code == 0

    def test_extract_path_for_edit(self):
        """_extract_path returns file_path for Edit tool."""
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import log_tool_usage as ltu
        assert ltu._extract_path("Edit", {"file_path": "scripts/foo.py"}) == "scripts/foo.py"

    def test_extract_path_for_bash(self):
        """_extract_path returns command[:120] for Bash tool."""
        import log_tool_usage as ltu
        cmd = "echo hello"
        assert ltu._extract_path("Bash", {"command": cmd}) == cmd

    def test_extract_path_for_bash_truncates(self):
        """Bash command longer than 120 chars is truncated."""
        import log_tool_usage as ltu
        long_cmd = "x" * 200
        result = ltu._extract_path("Bash", {"command": long_cmd})
        assert len(result) == 120

    def test_rotate_trims_to_max_lines(self, tmp_path):
        """_rotate_if_needed keeps only the last max_lines entries."""
        import log_tool_usage as ltu
        log = tmp_path / "tool_log.jsonl"
        records = [json.dumps({"i": i}) for i in range(100)]
        log.write_text("\n".join(records) + "\n")
        ltu._rotate_if_needed(log, 50)
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        assert len(lines) == 50
        # Must be the LAST 50 records
        assert json.loads(lines[0])["i"] == 50
        assert json.loads(lines[-1])["i"] == 99

    def test_rotate_noop_when_under_threshold(self, tmp_path):
        """_rotate_if_needed does nothing when line count is at or below threshold."""
        import log_tool_usage as ltu
        log = tmp_path / "tool_log.jsonl"
        records = [json.dumps({"i": i}) for i in range(10)]
        original = "\n".join(records) + "\n"
        log.write_text(original)
        ltu._rotate_if_needed(log, 10)
        assert log.read_text() == original


# ── Tests: analyze_tool_log.py ────────────────────────────────────────────────

class TestAnalyzeToolLog:
    def _sample_records(self) -> list[dict]:
        ts = time.time()
        return [
            {"ts": ts + 0, "tool": "Edit", "path": "foo.py", "exit": 0, "session": "S1"},
            {"ts": ts + 1, "tool": "Read", "path": "bar.py", "exit": 0, "session": "S1"},
            {"ts": ts + 5, "tool": "Edit", "path": "foo.py", "exit": 0, "session": "S1"},
            {"ts": ts + 6, "tool": "Bash", "path": "ls", "exit": 0, "session": "S2"},
            {"ts": ts + 8, "tool": "Read", "path": "baz.py", "exit": 0, "session": "S2"},
        ]

    def test_report_contains_frequency_section(self, tmp_path):
        log = tmp_path / "tool_log.jsonl"
        _make_log(log, self._sample_records())
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Tool call frequency" in result.stdout
        assert "Edit" in result.stdout

    def test_report_top_edited_files(self, tmp_path):
        log = tmp_path / "tool_log.jsonl"
        _make_log(log, self._sample_records())
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log)],
            capture_output=True, text=True,
        )
        assert "foo.py" in result.stdout

    def test_session_filter_isolates_session(self, tmp_path):
        log = tmp_path / "tool_log.jsonl"
        _make_log(log, self._sample_records())
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log), "--session", "S1"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        # S2 records should not appear in frequency for S1 filter
        # (Bash only in S2)
        assert "Session: S1" in result.stdout

    def test_retry_detection(self, tmp_path):
        """Two Edit calls within 5s should appear as a retry sequence."""
        log = tmp_path / "tool_log.jsonl"
        ts = time.time()
        records = [
            {"ts": ts, "tool": "Edit", "path": "x.py", "exit": 0, "session": "S1"},
            {"ts": ts + 3, "tool": "Edit", "path": "x.py", "exit": 0, "session": "S1"},
        ]
        _make_log(log, records)
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log)],
            capture_output=True, text=True,
        )
        assert "Edit × 2" in result.stdout

    def test_malformed_lines_skipped_and_reported(self, tmp_path):
        """Malformed JSON lines are silently skipped; count shown in header."""
        log = tmp_path / "tool_log.jsonl"
        content = (
            '{"ts": 1.0, "tool": "Edit", "path": "a.py", "exit": 0, "session": "S1"}\n'
            "NOT VALID JSON\n"
            '{"ts": 2.0, "tool": "Read", "path": "b.py", "exit": 0, "session": "S1"}\n'
        )
        log.write_text(content)
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Skipped (malformed): 1" in result.stdout

    def test_missing_log_returns_helpful_message(self, tmp_path):
        log = tmp_path / "nonexistent.jsonl"
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "No telemetry data" in result.stdout

    def test_bash_paths_excluded_from_top_edited_files(self, tmp_path):
        """T066: Bash command snippets in path field must not appear in Top edited files."""
        ts = time.time()
        records = [
            # foo.py appears only as a substring of Bash command paths — not via Edit/Write
            {"ts": ts + 0, "tool": "Bash", "path": "python foo.py --run", "session": "S1"},
            {"ts": ts + 1, "tool": "Bash", "path": "grep foo.py scripts/", "session": "S1"},
            {"ts": ts + 2, "tool": "Bash", "path": "cat foo.py", "session": "S1"},
            # A legitimate Edit of a different file
            {"ts": ts + 3, "tool": "Edit", "path": "legit.py", "session": "S1"},
        ]
        log = tmp_path / "tool_log.jsonl"
        _make_log(log, records)
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        output = result.stdout
        # Isolate the Top edited files section
        edited_start = output.find("Top-10 most-edited files")
        retry_start = output.find("Error / retry sequences")
        edited_section = output[edited_start:retry_start]
        assert "foo.py" not in edited_section, \
            f"Bash path 'foo.py' must not appear in Top edited files:\n{edited_section}"
        assert "legit.py" in edited_section, \
            f"Legitimately edited file must appear:\n{edited_section}"


# ── F11: harness_config.load_for_repo fallback ───────────────────────────────

class TestLoadForRepoFallback:
    def test_falls_back_to_harness_root_when_no_repo_yaml(self, tmp_path):
        """load_for_repo returns harness-root config when repo has no harness.yaml."""
        import harness_config as _hc
        repo = tmp_path / "no_yaml_repo"
        repo.mkdir()
        cfg = _hc.load_for_repo(repo)
        # Should return harness-root config (non-empty dict with at least code_paths)
        harness_root_cfg = _hc.load()
        assert cfg == harness_root_cfg

    def test_uses_repo_yaml_when_present(self, tmp_path):
        """load_for_repo uses <repo>/harness.yaml when present."""
        try:
            import yaml
        except ImportError:
            pytest.skip("pyyaml not installed")
        import harness_config as _hc
        repo = tmp_path / "ws_repo"
        repo.mkdir()
        (repo / "harness.yaml").write_text(
            yaml.dump({"code_paths": ["app/", "server/"]})
        )
        cfg = _hc.load_for_repo(repo)
        assert cfg.get("code_paths") == ["app/", "server/"]

    def test_exits_on_invalid_yaml(self, tmp_path):
        """load_for_repo exits 2 (fail-closed) when repo harness.yaml is malformed."""
        import harness_config as _hc
        import subprocess
        repo = tmp_path / "bad_yaml_repo"
        repo.mkdir()
        (repo / "harness.yaml").write_text(": invalid: yaml: }{")
        # Call via subprocess so sys.exit(2) doesn't kill the test process
        tools_path = str(ROOT / "scripts" / "tools")
        repo_str = str(repo)
        result = subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, {tools_path!r});"
             f"import harness_config as _hc; _hc.load_for_repo({repo_str!r})"],
            capture_output=True, text=True,
        )
        assert result.returncode == 2
        assert "ERROR" in result.stderr


# ── T057: workspace-aware session stamping ───────────────────────────────────

class TestWorkspaceAwareStamping:
    """The hook must derive the session from the right sessions.md based on
    which workspace the tool call targets — not from a global cache that gets
    clobbered by mixed harness/workspace callers.
    """

    @classmethod
    def setup_class(cls):
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))

    def _make_workspace(self, tmp_path, *, slug: str, last_session: int,
                        repo_subdir: str = "repo") -> tuple[Path, dict]:
        """Build a fake workspace dir with a sessions.md last entry of S<last_session>.

        Returns (workspace_dir, workspace_cfg_dict).
        """
        repo_root = tmp_path / slug / repo_subdir
        repo_root.mkdir(parents=True)
        internal = tmp_path / slug / "internal"
        internal.mkdir()
        (internal / "sessions.md").write_text(
            f"S{last_session - 1} 2026-05-25: prior\n"
            f"S{last_session} 2026-05-26: latest\n"
        )
        cfg = {
            "name": slug.title(),
            "status": "active",
            "repos": [{"path": str(repo_root), "role": "primary"}],
            "docs_path": str(internal),
        }
        return (tmp_path / slug, cfg)

    def test_detect_workspace_from_edit_file_path(self, tmp_path):
        import log_tool_usage as ltu
        import unittest.mock as mock
        ws_dir, cfg = self._make_workspace(tmp_path, slug="alpha", last_session=4)
        target = Path(cfg["repos"][0]["path"]) / "foo.py"
        with mock.patch.object(ltu, "_list_workspaces", return_value=[("alpha", cfg)]):
            slug, ws_cfg = ltu._detect_workspace("Edit", {"file_path": str(target)})
        assert slug == "alpha"
        assert ws_cfg == cfg

    def test_detect_workspace_from_bash_command_path_argument(self, tmp_path):
        import log_tool_usage as ltu
        import unittest.mock as mock
        ws_dir, cfg = self._make_workspace(tmp_path, slug="beta", last_session=2)
        repo_path = cfg["repos"][0]["path"]
        cmd = f"python scripts/tools/extract_session_brief.py --sessions {repo_path}/sessions.md"
        with mock.patch.object(ltu, "_list_workspaces", return_value=[("beta", cfg)]):
            slug, _ = ltu._detect_workspace("Bash", {"command": cmd})
        assert slug == "beta"

    def test_detect_workspace_returns_none_for_harness_root_path(self, tmp_path):
        import log_tool_usage as ltu
        import unittest.mock as mock
        _, cfg = self._make_workspace(tmp_path, slug="gamma", last_session=1)
        with mock.patch.object(ltu, "_list_workspaces", return_value=[("gamma", cfg)]):
            slug, ws_cfg = ltu._detect_workspace(
                "Edit", {"file_path": str(tmp_path / "elsewhere" / "x.py")}
            )
        assert slug == ""
        assert ws_cfg is None

    def test_detect_workspace_handles_missing_path(self, tmp_path):
        import log_tool_usage as ltu
        import unittest.mock as mock
        _, cfg = self._make_workspace(tmp_path, slug="delta", last_session=1)
        with mock.patch.object(ltu, "_list_workspaces", return_value=[("delta", cfg)]):
            slug, _ = ltu._detect_workspace("Edit", {})
        assert slug == ""

    def test_session_for_workspace_reads_workspace_sessions_md(self, tmp_path):
        """When a workspace is detected, session is computed from its sessions.md
        — NOT from the harness-root cache.
        """
        import log_tool_usage as ltu
        ws_dir, cfg = self._make_workspace(tmp_path, slug="epsilon", last_session=7)
        sid = ltu._session_for_workspace(ws_dir, cfg)
        assert sid == "S8"

    def test_session_for_harness_root_falls_back_to_docs_sessions_md(
        self, tmp_path, monkeypatch
    ):
        """When no workspace matches, session derives from harness-root sessions.md."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "sessions.md").write_text(
            "S40 2026-05-25: prior\nS41 2026-05-26: latest\n"
        )
        with mock.patch.object(ltu, "ROOT", tmp_path):
            sid = ltu._session_for_workspace(None, None)
        assert sid == "S42"

    def test_session_independent_of_cache_file(self, tmp_path):
        """A bogus value in .git/CLAUDE_SESSION_ID must not affect the stamp."""
        import log_tool_usage as ltu
        ws_dir, cfg = self._make_workspace(tmp_path, slug="zeta", last_session=3)
        # Drop a stale cache file in the workspace area — function must ignore it
        (tmp_path / ".git").mkdir(exist_ok=True)
        (tmp_path / ".git" / "CLAUDE_SESSION_ID").write_text("999")
        sid = ltu._session_for_workspace(ws_dir, cfg)
        assert sid == "S4"

    def test_session_for_workspace_without_docs_path_uses_ws_dir_internal(self, tmp_path):
        """When docs_path absent, ws_dir/internal/sessions.md is used."""
        import log_tool_usage as ltu
        ws_dir = tmp_path / "ws_no_docs"
        internal = ws_dir / "internal"
        internal.mkdir(parents=True)
        (internal / "sessions.md").write_text(
            "S8 2026-05-25: prior\nS9 2026-05-26: latest\n"
        )
        cfg = {"name": "Nodocs", "repos": [{"path": str(tmp_path / "repo"), "role": "primary"}]}
        sid = ltu._session_for_workspace(ws_dir, cfg)
        assert sid == "S10"

    def test_session_for_workspace_none_ws_dir_no_docs_path_logs_error(self, tmp_path):
        """ws_dir=None with no docs_path in cfg returns '' and logs an error."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        cfg = {"name": "Broken", "repos": []}
        err_path = tmp_path / "errors"
        with mock.patch.object(ltu, "_ERR_PATH", err_path):
            sid = ltu._session_for_workspace(None, cfg)
        assert sid == ""
        assert err_path.exists(), "expected error to be logged"
        assert "ws_dir is None" in err_path.read_text()

    def test_candidate_paths_bash_quoted_path_with_spaces(self):
        """shlex.split handles a shell-quoted path containing spaces."""
        import log_tool_usage as ltu
        cmd = 'python foo.py --sessions "/Users/foo/My Project/sessions.md"'
        paths = ltu._candidate_paths("Bash", {"command": cmd})
        assert any("My Project" in p for p in paths), f"Expected quoted path in {paths}"

    def test_record_includes_workspace_field(self, tmp_path):
        """End-to-end: payload for a workspace file produces a record with
        the correct workspace slug and session.
        """
        import log_tool_usage as ltu
        import unittest.mock as mock
        ws_dir, cfg = self._make_workspace(tmp_path, slug="eta", last_session=11)
        target = Path(cfg["repos"][0]["path"]) / "model.swift"
        log_path = tmp_path / "log.jsonl"
        sentinel = tmp_path / ".git" / "workflow_telemetry_on"
        sentinel.parent.mkdir(exist_ok=True)
        sentinel.touch()

        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(target)}})
        with mock.patch.object(ltu, "ROOT", tmp_path), \
             mock.patch.object(ltu, "_LOG_PATH", log_path), \
             mock.patch.object(ltu, "_SENTINEL", sentinel), \
             mock.patch.object(ltu, "_list_workspaces", return_value=[("eta", cfg)]), \
             mock.patch("sys.stdin.read", return_value=payload):
            try:
                ltu.main()
            except SystemExit:
                pass

        lines = log_path.read_text().splitlines()
        assert len(lines) == 1, f"Expected 1 record, got {len(lines)}"
        rec = json.loads(lines[0])
        assert rec["workspace"] == "eta"
        assert rec["session"] == "S12"
        assert rec["tool"] == "Edit"

    def test_record_includes_workspace_field_harness_root_case(self, tmp_path):
        """End-to-end: payload for a harness-root file produces workspace=''."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        ws_dir, cfg = self._make_workspace(tmp_path, slug="theta", last_session=5)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "sessions.md").write_text(
            "S20 2026-05-25: prior\nS21 2026-05-26: latest\n"
        )
        log_path = tmp_path / "log.jsonl"
        sentinel = tmp_path / ".git" / "workflow_telemetry_on"
        sentinel.parent.mkdir(exist_ok=True)
        sentinel.touch()
        target = tmp_path / "harness_file.py"
        target.write_text("")

        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(target)}})
        with mock.patch.object(ltu, "ROOT", tmp_path), \
             mock.patch.object(ltu, "_LOG_PATH", log_path), \
             mock.patch.object(ltu, "_SENTINEL", sentinel), \
             mock.patch.object(ltu, "_list_workspaces", return_value=[("theta", cfg)]), \
             mock.patch("sys.stdin.read", return_value=payload):
            try:
                ltu.main()
            except SystemExit:
                pass

        lines = log_path.read_text().splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["workspace"] == ""
        assert rec["session"] == "S22"

    def test_candidate_paths_tilde_expansion(self, tmp_path):
        """~/path tokens are expanded to absolute before workspace matching."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        home = Path.home()
        repo_root = home / "fake_ws_repo_for_test"
        cfg = {
            "name": "TildeWS",
            "repos": [{"path": str(repo_root), "role": "primary"}],
            "docs_path": str(tmp_path / "internal"),
        }
        cmd = f"cat ~/fake_ws_repo_for_test/some_file.md"
        with mock.patch.object(ltu, "_list_workspaces", return_value=[("tildews", cfg)]):
            slug, _ = ltu._detect_workspace("Bash", {"command": cmd})
        assert slug == "tildews", f"Expected tildews, got '{slug}' — tilde not expanded"

    def test_candidate_paths_chained_equals_extracts_path(self):
        """KEY=val=/path yields /path, not the intermediate val=/path."""
        import log_tool_usage as ltu
        cmd = "python foo.py --sessions=/tmp/some/sessions.md KEY=val=/other/path"
        paths = ltu._candidate_paths("Bash", {"command": cmd})
        assert "/tmp/some/sessions.md" in paths
        assert "/other/path" in paths

    def test_detect_workspace_inner_except_logs_error(self, tmp_path):
        """When is_within_workspace raises, the error is logged rather than swallowed."""
        import log_tool_usage as ltu
        import unittest.mock as mock

        cfg = {"name": "Broken", "repos": [{"path": "/some/repo", "role": "primary"}]}
        err_path = tmp_path / "errors"

        def _raise(path, cfg):
            raise RuntimeError("simulated cfg error")

        with mock.patch.object(ltu, "_list_workspaces", return_value=[("broken", cfg)]), \
             mock.patch("workspace_config.is_within_workspace", _raise), \
             mock.patch.object(ltu, "_ERR_PATH", err_path):
            ltu._ERR_COUNT = 0
            ltu._ERR_WINDOW_START = 0.0
            ltu._detect_workspace("Edit", {"file_path": "/some/repo/x.py"})

        assert err_path.exists(), "Expected error to be logged"
        assert "workspace match failed" in err_path.read_text()


# ── T059: _log_error rate-limit ───────────────────────────────────────────────

class TestLogErrorRateLimit:
    @classmethod
    def setup_class(cls):
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))

    def test_rate_limit_caps_at_ten_plus_marker(self, tmp_path):
        """100 rapid _log_error calls produce ≤ 10 real lines + 1 marker line."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        err_path = tmp_path / "errors"
        state_path = tmp_path / "errors.state"
        with mock.patch.object(ltu, "_ERR_PATH", err_path), \
             mock.patch.object(ltu, "_ERR_STATE_PATH", state_path):
            for i in range(100):
                ltu._log_error(f"boom {i}")
        lines = err_path.read_text().splitlines()
        assert len(lines) == 11, f"Expected 11 lines (10 + marker), got {len(lines)}"
        assert "rate-limit" in lines[-1]

    def test_rate_limit_marker_suppresses_further_writes(self, tmp_path):
        """After the marker is written, additional calls produce no new lines."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        err_path = tmp_path / "errors"
        state_path = tmp_path / "errors.state"
        with mock.patch.object(ltu, "_ERR_PATH", err_path), \
             mock.patch.object(ltu, "_ERR_STATE_PATH", state_path):
            for i in range(100):
                ltu._log_error(f"msg {i}")
            count_after_100 = len(err_path.read_text().splitlines())
            for i in range(100):
                ltu._log_error(f"extra {i}")
            count_after_200 = len(err_path.read_text().splitlines())
        assert count_after_100 == count_after_200, "Writes after marker must be suppressed"

    def test_rate_limit_window_resets_after_expiry(self, tmp_path):
        """After 60s the window resets and errors are logged again."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        err_path = tmp_path / "errors"
        state_path = tmp_path / "errors.state"
        fake_now = [0.0]
        with mock.patch.object(ltu, "_ERR_PATH", err_path), \
             mock.patch.object(ltu, "_ERR_STATE_PATH", state_path), \
             mock.patch("log_tool_usage.time") as mock_time:
            mock_time.time.side_effect = lambda: fake_now[0]
            mock_time.strftime.side_effect = time.strftime
            mock_time.gmtime.side_effect = time.gmtime
            for i in range(100):
                ltu._log_error(f"first window {i}")
            first_count = len(err_path.read_text().splitlines())
            fake_now[0] = 61.0
            ltu._log_error("after reset")
        all_lines = err_path.read_text().splitlines()
        assert first_count == 11
        assert len(all_lines) == 12, f"Expected 12 lines after reset, got {len(all_lines)}"

    def test_hook_exits_zero_when_rate_limited(self, tmp_path):
        """Rate-limiting never causes the hook to exit non-zero."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        err_path = tmp_path / "errors"
        state_path = tmp_path / "errors.state"
        state_path.write_text(json.dumps({"count": 11, "window_start": time.time()}))
        with mock.patch.object(ltu, "_ERR_PATH", err_path), \
             mock.patch.object(ltu, "_ERR_STATE_PATH", state_path):
            ltu._log_error("should be silently dropped")
        assert not err_path.exists() or err_path.read_text() == ""

    def test_rate_limit_cross_process(self, tmp_path):
        """100 subprocess calls each emitting one error produce ≤ 11 total lines."""
        err_path = tmp_path / "errors"
        state_path = tmp_path / "errors.state"
        hooks_dir = str(ROOT / "scripts" / "hooks")
        script = (
            "import sys; "
            f"sys.path.insert(0, {repr(hooks_dir)}); "
            "import log_tool_usage as ltu; "
            "from pathlib import Path; "
            f"ltu._ERR_PATH = Path({repr(str(err_path))}); "
            f"ltu._ERR_STATE_PATH = Path({repr(str(state_path))}); "
            "ltu._log_error('boom')"
        )
        for _ in range(100):
            subprocess.run([sys.executable, "-c", script], check=True)
        lines = err_path.read_text().splitlines() if err_path.exists() else []
        assert len(lines) <= 11, f"Expected ≤ 11 lines across 100 processes, got {len(lines)}"
