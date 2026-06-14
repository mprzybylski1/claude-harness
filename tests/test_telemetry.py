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

    def test_retry_detection_different_path_not_flagged(self, tmp_path):
        """Two Edit calls within 5s on DIFFERENT files must not appear as a retry."""
        log = tmp_path / "tool_log.jsonl"
        ts = time.time()
        records = [
            {"ts": ts, "tool": "Edit", "path": "a.py", "exit": 0, "session": "S1"},
            {"ts": ts + 3, "tool": "Edit", "path": "b.py", "exit": 0, "session": "S1"},
        ]
        _make_log(log, records)
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log)],
            capture_output=True, text=True,
        )
        assert "Edit × 2" not in result.stdout, \
            "Different-path same-tool calls must not be flagged as retries"

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


class TestWorkspaceFilter:
    """T137: analyze_tool_log --workspace + (workspace, session) filtering."""

    def _records(self) -> list[dict]:
        ts = time.time()
        return [
            {"ts": ts + 0, "tool": "Edit", "path": "a.swift", "session": "S12",
             "workspace": "scrabble-score"},
            {"ts": ts + 1, "tool": "Bash", "path": "echo", "session": "S12",
             "workspace": "scrabble-score"},
            {"ts": ts + 2, "tool": "Edit", "path": "log_tool_usage.py", "session": "S12",
             "workspace": ""},
            {"ts": ts + 3, "tool": "Read", "path": "legacy.py", "session": "S12"},  # no key
        ]

    def test_workspace_filter_isolates_workspace(self, tmp_path):
        log = tmp_path / "l.jsonl"
        _make_log(log, self._records())
        r = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log),
             "--session", "S12", "--workspace", "scrabble-score"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "Records: 2" in r.stdout
        assert "Workspace: scrabble-score" in r.stdout

    def test_harness_alias_filters_empty_and_legacy(self, tmp_path):
        # "harness" alias → workspace=="" plus legacy records (missing key → "").
        log = tmp_path / "l.jsonl"
        _make_log(log, self._records())
        r = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log),
             "--session", "S12", "--workspace", "harness"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "Records: 2" in r.stdout
        assert "Workspace: harness" in r.stdout

    def test_explicit_log_does_not_autodetect(self, tmp_path):
        # --log given → auto-detect suppressed → no workspace filter → all 4.
        log = tmp_path / "l.jsonl"
        _make_log(log, self._records())
        r = subprocess.run(
            [sys.executable, str(ANALYZE), "--log", str(log), "--session", "S12"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "Records: 4" in r.stdout

    def test_autodetect_workspace_from_active_state(self, tmp_path):
        # No --log → default log under HARNESS_ROOT; auto-detect reads .active_workspace.
        import os as _os
        h = tmp_path / "harness"
        (h / ".git").mkdir(parents=True)
        (h / ".claude").mkdir(parents=True)
        (h / ".claude" / ".active_workspace").write_text("scrabble-score", encoding="utf-8")
        _make_log(h / ".git" / "session_tool_log.jsonl", self._records())
        r = subprocess.run(
            [sys.executable, str(ANALYZE), "--session", "S12"],
            capture_output=True, text=True,
            env={**_os.environ, "HARNESS_ROOT": str(h), "PYTHONPATH": str(ROOT)},
        )
        assert r.returncode == 0, r.stderr
        assert "Workspace: scrabble-score" in r.stdout
        assert "Records: 2" in r.stdout


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


# ── T137: active-workspace session stamping (replaces path-based T057) ─────────

class TestActiveWorkspaceStamping:
    """T137: attribution is by the ACTIVE session, read from
    .claude/.active_workspace (via workspace_config.read_session_state), NOT by
    the path of the touched file. Every call in a session inherits that session's
    (workspace, S<N>) + a live claude_session_uuid join key. This replaces the
    path-based T057 scheme, which under-attributed non-repo-path calls to harness.
    """

    @classmethod
    def setup_class(cls):
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))

    def _fake_harness(self, tmp_path, *, state, ws_slug=None,
                      ws_last=None, harness_last=None):
        h = tmp_path / "harness"
        (h / ".claude").mkdir(parents=True)
        (h / "docs").mkdir(parents=True)
        if harness_last is not None:
            (h / "docs" / "sessions.md").write_text(
                f"S{harness_last} 2026-05-26: latest\n", encoding="utf-8")
        (h / ".claude" / ".active_workspace").write_text(state, encoding="utf-8")
        if ws_slug:
            internal = h / "workspaces" / ws_slug / "internal"
            internal.mkdir(parents=True)
            (h / "workspaces" / ws_slug / "workspace.yaml").write_text(
                f"name: {ws_slug}\n", encoding="utf-8")
            if ws_last is not None:
                (internal / "sessions.md").write_text(
                    f"S{ws_last} 2026-05-26: ws\n", encoding="utf-8")
        return h

    # ── _session_from_sessions_md ──────────────────────────────────────────────

    def test_session_from_sessions_md_last_plus_one(self, tmp_path):
        import log_tool_usage as ltu
        sm = tmp_path / "sessions.md"
        sm.write_text("S6 2026-05-25: a\nS7 2026-05-26: b\n", encoding="utf-8")
        assert ltu._session_from_sessions_md(sm) == "S8"

    def test_session_from_sessions_md_none_returns_empty(self):
        import log_tool_usage as ltu
        assert ltu._session_from_sessions_md(None) == ""

    def test_session_from_sessions_md_missing_returns_empty(self, tmp_path):
        import log_tool_usage as ltu
        assert ltu._session_from_sessions_md(tmp_path / "nope.md") == ""

    # ── _active_workspace_and_sessions_md ──────────────────────────────────────

    def test_active_resolves_workspace(self, tmp_path):
        import log_tool_usage as ltu
        import unittest.mock as mock
        h = self._fake_harness(tmp_path, state="myws", ws_slug="myws", ws_last=11)
        with mock.patch.object(ltu, "ROOT", h):
            ws, sm = ltu._active_workspace_and_sessions_md()
        assert ws == "myws"
        assert ltu._session_from_sessions_md(sm) == "S12"

    def test_active_resolves_harness_sentinel(self, tmp_path):
        import log_tool_usage as ltu
        import unittest.mock as mock
        h = self._fake_harness(tmp_path, state="__harness__", harness_last=21)
        with mock.patch.object(ltu, "ROOT", h):
            ws, sm = ltu._active_workspace_and_sessions_md()
        assert ws == ""
        assert ltu._session_from_sessions_md(sm) == "S22"

    def test_active_undeclared_falls_to_harness(self, tmp_path):
        import log_tool_usage as ltu
        import unittest.mock as mock
        h = self._fake_harness(tmp_path, state="", harness_last=3)
        with mock.patch.object(ltu, "ROOT", h):
            ws, sm = ltu._active_workspace_and_sessions_md()
        assert ws == ""
        assert ltu._session_from_sessions_md(sm) == "S4"

    # ── end-to-end record shape ────────────────────────────────────────────────

    def test_bare_bash_in_workspace_attributes_to_active_workspace(self, tmp_path):
        """The fix: a path-less call (bare Bash) during a workspace session is
        stamped with the active workspace + its session — path-based T057 wrongly
        stamped workspace='' harness for these."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        h = self._fake_harness(tmp_path, state="myws", ws_slug="myws", ws_last=11)
        log_path = h / ".git" / "session_tool_log.jsonl"
        sentinel = h / ".git" / "workflow_telemetry_on"
        sentinel.parent.mkdir(parents=True)
        sentinel.touch()
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
        with mock.patch.object(ltu, "ROOT", h), \
             mock.patch.object(ltu, "_LOG_PATH", log_path), \
             mock.patch.object(ltu, "_SENTINEL", sentinel), \
             mock.patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "uuid-123"}), \
             mock.patch("sys.stdin.read", return_value=payload):
            try:
                ltu.main()
            except SystemExit:
                pass
        rec = json.loads(log_path.read_text().splitlines()[0])
        assert rec["workspace"] == "myws"
        assert rec["session"] == "S12"
        assert rec["claude_session_uuid"] == "uuid-123"
        assert rec["tool"] == "Bash"

    def test_harness_session_record_has_empty_workspace(self, tmp_path):
        import log_tool_usage as ltu
        import unittest.mock as mock
        h = self._fake_harness(tmp_path, state="__harness__", harness_last=20)
        log_path = h / ".git" / "session_tool_log.jsonl"
        sentinel = h / ".git" / "workflow_telemetry_on"
        sentinel.parent.mkdir(parents=True)
        sentinel.touch()
        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "scripts/x.py"}})
        with mock.patch.object(ltu, "ROOT", h), \
             mock.patch.object(ltu, "_LOG_PATH", log_path), \
             mock.patch.object(ltu, "_SENTINEL", sentinel), \
             mock.patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "uuid-h"}), \
             mock.patch("sys.stdin.read", return_value=payload):
            try:
                ltu.main()
            except SystemExit:
                pass
        rec = json.loads(log_path.read_text().splitlines()[0])
        assert rec["workspace"] == ""
        assert rec["session"] == "S21"
        assert rec["claude_session_uuid"] == "uuid-h"


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

    def test_rate_limit_window_resets_at_exact_boundary(self, tmp_path):
        """Window resets when elapsed == _ERR_WINDOW_SECS (>= not just >).

        Sets count=11 (at limit) with window_start=0, then calls _log_error
        with time.time() returning exactly window_start + _ERR_WINDOW_SECS.
        Expects the error to be logged (window reset), not suppressed.
        """
        import log_tool_usage as ltu
        import unittest.mock as mock
        err_path = tmp_path / "errors"
        state_path = tmp_path / "errors.state"
        state_path.write_text(
            json.dumps({"count": 11, "window_start": 0.0}), encoding="utf-8"
        )
        boundary = float(ltu._ERR_WINDOW_SECS)
        with mock.patch.object(ltu, "_ERR_PATH", err_path), \
             mock.patch.object(ltu, "_ERR_STATE_PATH", state_path), \
             mock.patch("log_tool_usage.time") as mock_time:
            mock_time.time.return_value = boundary
            mock_time.strftime.side_effect = time.strftime
            mock_time.gmtime.side_effect = time.gmtime
            ltu._log_error("boundary reset")
        assert err_path.exists(), "Error should have been logged after window reset at exact boundary"
        lines = err_path.read_text().splitlines()
        assert len(lines) == 1, f"Expected 1 line after boundary reset, got {len(lines)}"

    def test_rate_limit_cross_process_concurrent(self, tmp_path):
        """Concurrent cross-process _log_error calls produce ≤ 11 total lines.

        Spawns 30 processes simultaneously (all started before any finishes)
        to exercise real TOCTOU races. Without flock this may produce > 11.
        """
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
            "ltu._log_error('concurrent')"
        )
        procs = [subprocess.Popen([sys.executable, "-c", script]) for _ in range(30)]
        for p in procs:
            p.wait()
        lines = err_path.read_text().splitlines() if err_path.exists() else []
        assert len(lines) <= 11, f"Expected ≤ 11 lines (concurrent), got {len(lines)}"


# ── T081: bootstrap-path errors bypass rate-limit ────────────────────────────

class TestLogErrorBootstrapGuard:
    """T081: _log_error must not flood when .git/ is absent or state IO fails."""

    @classmethod
    def setup_class(cls):
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))

    def test_git_absent_bounded_at_one_stderr_line(self, tmp_path, capsys):
        """With .git/ absent, 100 _log_error calls produce ≤ 1 total output line."""
        import log_tool_usage as ltu
        import unittest.mock as mock

        no_dir = tmp_path / "no_git_dir"  # parent directory that does NOT exist
        state_path = no_dir / "errors.state"
        err_path = no_dir / "errors"

        ltu._BOOTSTRAP_STDERR_LOGGED = False  # reset for test isolation

        with mock.patch.object(ltu, "_ERR_PATH", err_path), \
             mock.patch.object(ltu, "_ERR_STATE_PATH", state_path):
            for i in range(100):
                ltu._log_error(f"bootstrap-error {i}")

        captured = capsys.readouterr()
        stderr_lines = [ln for ln in captured.err.splitlines() if ln.strip()]
        file_lines = err_path.read_text().splitlines() if err_path.exists() else []
        total = len(stderr_lines) + len(file_lines)
        assert total <= 1, (
            f"Expected ≤ 1 output line with .git/ absent, got {total}:\n"
            f"  stderr: {stderr_lines}\n"
            f"  file: {file_lines}"
        )

    def test_git_absent_first_message_goes_to_stderr(self, tmp_path, capsys):
        """The one allowed line must go to stderr, not to _ERR_PATH."""
        import log_tool_usage as ltu
        import unittest.mock as mock

        no_dir = tmp_path / "no_git_dir"
        state_path = no_dir / "errors.state"
        err_path = no_dir / "errors"

        ltu._BOOTSTRAP_STDERR_LOGGED = False

        with mock.patch.object(ltu, "_ERR_PATH", err_path), \
             mock.patch.object(ltu, "_ERR_STATE_PATH", state_path):
            ltu._log_error("first-bootstrap-error")

        captured = capsys.readouterr()
        assert "first-bootstrap-error" in captured.err or "bootstrap" in captured.err.lower(), \
            f"Expected bootstrap message in stderr, got: {captured.err!r}"
        assert not err_path.exists() or err_path.stat().st_size == 0, \
            "bootstrap error must NOT be written to _ERR_PATH"

    def test_state_io_failure_does_not_bypass_rate_limit(self, tmp_path, capsys):
        """When state file is unreadable (IsADirectoryError), output is bounded, not unlimited.

        Placing a directory at _ERR_STATE_PATH causes open(path, 'a+') to raise
        IsADirectoryError, exercising the exact bypass that Opus flagged: inner except
        fires, count stays 0, and without the fix all 100 calls reach _ERR_PATH.
        """
        import log_tool_usage as ltu
        import unittest.mock as mock

        err_path = tmp_path / "errors"
        state_path = tmp_path / "errors.state"
        state_path.mkdir()  # directory → open("a+") raises IsADirectoryError
        # tmp_path EXISTS → bootstrap guard does NOT trigger (this tests the normal-path fix)

        ltu._BOOTSTRAP_STDERR_LOGGED = False

        with mock.patch.object(ltu, "_ERR_PATH", err_path), \
             mock.patch.object(ltu, "_ERR_STATE_PATH", state_path):
            for i in range(100):
                ltu._log_error(f"io-fail-{i}")

        captured = capsys.readouterr()
        stderr_lines = [ln for ln in captured.err.splitlines() if ln.strip()]
        file_lines = err_path.read_text().splitlines() if err_path.exists() else []
        total = len(stderr_lines) + len(file_lines)
        assert total <= 1, (
            f"State IO failure must not bypass rate limit: got {total} lines "
            f"(stderr={stderr_lines}, file={file_lines})"
        )


# ── T156: session-uuid join key sourced from the stdin payload ────────────────

class TestSessionUuidSource:
    """claude_session_uuid must come from the stdin payload (session_id /
    transcript_path), not only the CLAUDE_CODE_SESSION_ID env var which is unset
    in many session contexts (left ~68% of records with an empty uuid)."""

    def _log_record(self, tmp_path, payload_dict, env_uuid=None):
        import os
        import unittest.mock as mock
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import log_tool_usage as ltu

        fake_root = _make_fake_root(tmp_path, telemetry_on=True, sentinel=True)
        fake_log = fake_root / ".git" / "session_tool_log.jsonl"
        env = dict(os.environ)
        env.pop("CLAUDE_CODE_SESSION_ID", None)
        if env_uuid is not None:
            env["CLAUDE_CODE_SESSION_ID"] = env_uuid
        with mock.patch.object(ltu, "ROOT", fake_root), \
             mock.patch.object(ltu, "_SENTINEL", fake_root / ".git" / "workflow_telemetry_on"), \
             mock.patch.object(ltu, "_LOG_PATH", fake_log), \
             mock.patch.object(ltu, "_ERR_PATH", fake_root / ".git" / "session_tool_log.errors"), \
             mock.patch.dict(os.environ, env, clear=True), \
             mock.patch("sys.stdin.read", return_value=json.dumps(payload_dict)):
            try:
                ltu.main()
            except SystemExit:
                pass
        lines = [ln for ln in fake_log.read_text().splitlines() if ln.strip()]
        assert lines, "hook must have written a record"
        return json.loads(lines[-1])

    def test_uuid_from_payload_session_id(self, tmp_path):
        rec = self._log_record(
            tmp_path,
            {"tool_name": "Read", "tool_input": {"file_path": "x.py"},
             "session_id": "abc-123-uuid",
             "transcript_path": "/p/other-uuid.jsonl"},
            env_uuid="env-uuid",
        )
        assert rec["claude_session_uuid"] == "abc-123-uuid"

    def test_uuid_from_transcript_path_when_no_session_id(self, tmp_path):
        rec = self._log_record(
            tmp_path,
            {"tool_name": "Read", "tool_input": {"file_path": "x.py"},
             "transcript_path": "/p/projects/def-456-uuid.jsonl"},
            env_uuid="env-uuid",
        )
        assert rec["claude_session_uuid"] == "def-456-uuid"

    def test_uuid_falls_back_to_env_var(self, tmp_path):
        rec = self._log_record(
            tmp_path,
            {"tool_name": "Read", "tool_input": {"file_path": "x.py"}},
            env_uuid="env-789-uuid",
        )
        assert rec["claude_session_uuid"] == "env-789-uuid"

    def test_uuid_empty_when_no_source(self, tmp_path):
        rec = self._log_record(
            tmp_path,
            {"tool_name": "Read", "tool_input": {"file_path": "x.py"}},
            env_uuid=None,
        )
        assert rec["claude_session_uuid"] == ""
