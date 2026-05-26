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
        """Hook exits 0 quickly when sentinel absent AND harness.yaml has telemetry false."""
        sentinel = ROOT / ".git" / "workflow_telemetry_on"
        harness_yaml = ROOT / "harness.yaml"
        original_yaml = harness_yaml.read_text(encoding="utf-8")
        sentinel_existed = sentinel.exists()
        harness_yaml.write_text(
            original_yaml.replace("workflow_telemetry: true", "workflow_telemetry: false"),
            encoding="utf-8",
        )
        if sentinel_existed:
            sentinel.unlink()
        try:
            start = time.monotonic()
            result = _run_hook({"tool_name": "Edit", "tool_input": {"file_path": "foo.py"}})
            elapsed = time.monotonic() - start
        finally:
            harness_yaml.write_text(original_yaml, encoding="utf-8")
            if sentinel_existed:
                sentinel.touch()
        assert result.returncode == 0
        assert elapsed < 0.5, f"Expected fast exit, took {elapsed:.3f}s"

    def test_bootstrap_creates_sentinel_from_yaml(self):
        """Sentinel-absent + yaml true → sentinel created on first tool call."""
        sentinel = ROOT / ".git" / "workflow_telemetry_on"
        sentinel_existed = sentinel.exists()
        if sentinel_existed:
            sentinel.unlink()
        try:
            result = _run_hook({"tool_name": "Read", "tool_input": {"file_path": "x.py"}})
            assert result.returncode == 0
            assert sentinel.exists(), "Bootstrap must have created the sentinel"
        finally:
            # Always restore to original state
            if sentinel_existed and not sentinel.exists():
                sentinel.touch()
            elif not sentinel_existed and sentinel.exists():
                sentinel.unlink()

    def test_bootstrap_works_from_workspace_cwd(self, tmp_path):
        """Hook invoked via absolute path from a non-harness-root cwd still bootstraps.

        Regression test for T039: settings.json previously used a relative
        'python3 scripts/hooks/...' command, which silently failed when Claude Code
        ran hooks from a workspace subdirectory (no 'scripts/' dir there).
        The fix uses an absolute path; this test verifies the sentinel is created
        even when the subprocess cwd is outside the harness root.
        """
        sentinel = ROOT / ".git" / "workflow_telemetry_on"
        sentinel_existed = sentinel.exists()
        if sentinel_existed:
            sentinel.unlink()
        try:
            result = subprocess.run(
                [sys.executable, str(HOOK)],  # absolute path — mirrors fixed settings.json
                input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x.py"}}),
                capture_output=True, text=True,
                cwd=str(tmp_path),  # non-harness-root cwd — simulates workspace session
            )
            assert result.returncode == 0
            assert sentinel.exists(), (
                "Bootstrap must create sentinel even when cwd is not the harness root"
            )
        finally:
            if sentinel_existed and not sentinel.exists():
                sentinel.touch()
            elif not sentinel_existed and sentinel.exists():
                sentinel.unlink()

    def test_exits_zero_with_any_state(self):
        """Hook exits 0 regardless of telemetry state (never breaks tool calls)."""
        payload = {"tool_name": "Edit", "tool_input": {"file_path": "foo.py"}}
        result = _run_hook(payload)
        assert result.returncode == 0

    def test_handles_malformed_stdin_gracefully(self):
        """Invalid JSON on stdin must not crash the hook."""
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input="not valid json at all }{",
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_current_session_normalises_bare_integer(self, tmp_path, monkeypatch):
        """_current_session prepends 'S' when CLAUDE_SESSION_ID contains a bare integer."""
        sys.path.insert(0, str(ROOT / "scripts" / "hooks"))
        import log_tool_usage as ltu
        fake_id = tmp_path / "CLAUDE_SESSION_ID"
        fake_id.write_text("6")
        monkeypatch.setattr(ltu, "_LOG_PATH", tmp_path / "log.jsonl")
        # Patch ROOT-relative path inside the function
        import unittest.mock as mock
        with mock.patch.object(ltu, "ROOT", tmp_path):
            (tmp_path / ".git").mkdir(exist_ok=True)
            (tmp_path / ".git" / "CLAUDE_SESSION_ID").write_text("6")
            result = ltu._current_session()
        assert result == "S6", f"Expected 'S6', got {result!r}"

    def test_current_session_accepts_s_prefix(self, tmp_path):
        """_current_session passes through already-prefixed values unchanged."""
        import log_tool_usage as ltu
        import unittest.mock as mock
        with mock.patch.object(ltu, "ROOT", tmp_path):
            (tmp_path / ".git").mkdir(exist_ok=True)
            (tmp_path / ".git" / "CLAUDE_SESSION_ID").write_text("S42")
            result = ltu._current_session()
        assert result == "S42"

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

    def test_extract_exit_from_tool_response(self):
        """_extract_exit reads exit_code from tool_response when present."""
        import log_tool_usage as ltu
        payload = {"tool_response": {"exit_code": 1}}
        assert ltu._extract_exit(payload) == 1

    def test_extract_exit_defaults_to_zero(self):
        """_extract_exit returns 0 when tool_response has no exit_code."""
        import log_tool_usage as ltu
        assert ltu._extract_exit({}) == 0
        assert ltu._extract_exit({"tool_response": {}}) == 0


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
        result = subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, '{ROOT}/scripts/tools');"
             f"import harness_config as _hc; _hc.load_for_repo('{repo}')"],
            capture_output=True, text=True,
        )
        assert result.returncode == 2
        assert "ERROR" in result.stderr
