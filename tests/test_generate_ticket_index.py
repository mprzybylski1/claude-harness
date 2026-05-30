"""Tests for T136: generate_ticket_index.py workspace-scoping + idempotency.

SR-009: running `generate_ticket_index.py` bare from a workspace session
defaulted to the harness-root INDEX and silently overwrote it (cross-layer
write the check_cross_layer_writes hook can't catch, since it's a python open()
not an Edit/Write). Fix: read .claude/.active_workspace; a declared workspace or
an undeclared session fails closed rather than touch the harness INDEX. Explicit
paths and --workspace always win. Determinism (already true) is locked by an
idempotency test.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "tools" / "generate_ticket_index.py"


def _harness(tmp_path: Path, state: str | None) -> Path:
    """Minimal harness skeleton. state → .claude/.active_workspace contents
    ('__harness__', a slug, or None to leave the file absent)."""
    h = tmp_path / "harness"
    (h / ".claude").mkdir(parents=True)
    (h / "docs" / "tickets" / "open").mkdir(parents=True)
    (h / "docs" / "sessions.md").write_text(
        "## Session Log\n\nS5 2026-01-01: init\n", encoding="utf-8"
    )
    (h / "docs" / "tickets" / "INDEX.md").write_text("HARNESS-SENTINEL\n", encoding="utf-8")
    if state is not None:
        (h / ".claude" / ".active_workspace").write_text(state, encoding="utf-8")
    return h


def _add_ws(h: Path, slug: str = "myws") -> Path:
    """Add a workspace with its own ticket + sessions. Returns its internal dir."""
    internal = h / "workspaces" / slug / "internal"
    (internal / "tickets" / "open").mkdir(parents=True)
    (internal / "tickets" / "INDEX.md").write_text("WS-SENTINEL\n", encoding="utf-8")
    (internal / "sessions.md").write_text(
        "## Session Log\n\nS2 2026-01-01: ws\n", encoding="utf-8"
    )
    (internal / "tickets" / "open" / "T003-ws.md").write_text(
        "---\nid: T003\ntitle: ws ticket\nseverity: low\nphase: 2\nopened: S2 2026-01-01\n---\n",
        encoding="utf-8",
    )
    (h / "workspaces" / slug / "workspace.yaml").write_text(f"name: {slug}\n", encoding="utf-8")
    return internal


def _run(h: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(GEN), *args],
        capture_output=True, text=True, cwd=str(cwd or h),
        env={**os.environ, "HARNESS_ROOT": str(h), "PYTHONPATH": str(ROOT)},
    )


class TestFailClosed:

    def test_workspace_session_bare_fails_closed(self, tmp_path):
        # Declared workspace + no output path → exit 2, harness INDEX untouched.
        h = _harness(tmp_path, state="myws")
        _add_ws(h)
        before = (h / "docs" / "tickets" / "INDEX.md").read_text()
        result = _run(h)
        assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
        assert "myws" in result.stderr
        # The guard: harness INDEX must be byte-for-byte untouched.
        assert (h / "docs" / "tickets" / "INDEX.md").read_text() == before

    def test_undeclared_session_bare_fails_closed(self, tmp_path):
        # No .active_workspace file at all → exit 2, harness INDEX untouched.
        h = _harness(tmp_path, state=None)
        before = (h / "docs" / "tickets" / "INDEX.md").read_text()
        result = _run(h)
        assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
        assert (h / "docs" / "tickets" / "INDEX.md").read_text() == before

    def test_empty_state_bare_fails_closed(self, tmp_path):
        h = _harness(tmp_path, state="")
        before = (h / "docs" / "tickets" / "INDEX.md").read_text()
        result = _run(h)
        assert result.returncode == 2
        assert (h / "docs" / "tickets" / "INDEX.md").read_text() == before


class TestHarnessSession:

    def test_harness_session_bare_regenerates_harness_index(self, tmp_path):
        h = _harness(tmp_path, state="__harness__")
        result = _run(h)
        assert result.returncode == 0, result.stderr
        # Sentinel replaced by a real generated index.
        content = (h / "docs" / "tickets" / "INDEX.md").read_text()
        assert "HARNESS-SENTINEL" not in content
        assert "# Ticket Index" in content


class TestWorkspaceFlag:

    def test_workspace_flag_routes_to_workspace_index(self, tmp_path):
        h = _harness(tmp_path, state="__harness__")
        internal = _add_ws(h)
        harness_before = (h / "docs" / "tickets" / "INDEX.md").read_text()
        result = _run(h, "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        ws_index = (internal / "tickets" / "INDEX.md").read_text()
        assert "WS-SENTINEL" not in ws_index
        assert "T003" in ws_index
        # Harness INDEX untouched by a --workspace run.
        assert (h / "docs" / "tickets" / "INDEX.md").read_text() == harness_before

    def test_unknown_workspace_exits_nonzero(self, tmp_path):
        h = _harness(tmp_path, state="__harness__")
        result = _run(h, "--workspace", "does-not-exist")
        assert result.returncode != 0
        assert "ERROR" in result.stderr


class TestExplicitPathsBypassState:

    def test_explicit_output_in_workspace_session_still_works(self, tmp_path):
        # Even with .active_workspace=myws, explicit --tickets-dir/--output win
        # (this is how the regen hook / session-close / close_ticket call it).
        h = _harness(tmp_path, state="myws")
        out = tmp_path / "explicit_INDEX.md"
        result = _run(
            h,
            "--tickets-dir", str(h / "docs" / "tickets"),
            "--output", str(out),
            "--sessions-file", str(h / "docs" / "sessions.md"),
        )
        assert result.returncode == 0, result.stderr
        assert out.exists()
        assert "# Ticket Index" in out.read_text()


class TestIdempotency:

    def test_two_runs_byte_identical(self, tmp_path):
        h = _harness(tmp_path, state="__harness__")
        _add_ws(h)  # give it some content
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        common = ["--tickets-dir", str(h / "docs" / "tickets"),
                  "--sessions-file", str(h / "docs" / "sessions.md")]
        r1 = _run(h, *common, "--output", str(a))
        r2 = _run(h, *common, "--output", str(b))
        assert r1.returncode == 0 and r2.returncode == 0, (r1.stderr, r2.stderr)
        assert a.read_bytes() == b.read_bytes(), "regeneration must be deterministic"
