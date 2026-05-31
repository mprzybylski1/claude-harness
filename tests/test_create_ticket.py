"""Tests for T089: create_ticket.py scaffolding script."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATE = ROOT / "scripts" / "tools" / "create_ticket.py"


def _setup(tmp_path: Path) -> Path:
    """Minimal harness skeleton. Returns harness root.

    Declares a harness session (.claude/.active_workspace == "__harness__") so a
    bare invocation routes to the harness layer (T140). Tests that want a workspace
    or undeclared session overwrite/remove the state file after _setup returns.
    """
    (tmp_path / "docs" / "tickets" / "open").mkdir(parents=True)
    (tmp_path / "docs" / "archive").mkdir(parents=True)
    (tmp_path / "docs" / "tickets" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (tmp_path / "docs" / "sessions.md").write_text(
        "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
    )
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / ".active_workspace").write_text(
        "__harness__", encoding="utf-8"
    )
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
    (tools / "generate_ticket_index.py").write_text(
        "import os; from pathlib import Path\n"
        "root = Path(os.environ.get('HARNESS_ROOT', '.'))\n"
        "(root / 'docs' / 'tickets' / 'INDEX.md').write_text('# Updated\\n')\n"
    )
    return tmp_path


def _run(harness: Path, *args: str) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(CREATE), *args],
        capture_output=True, text=True,
        env={**_os.environ, "HARNESS_ROOT": str(harness), "PYTHONPATH": str(ROOT)},
    )


class TestCreateTicket:

    def test_happy_path_creates_file(self, tmp_path):
        """Ticket file is created with correct frontmatter."""
        harness = _setup(tmp_path)
        result = _run(harness, "Fix the thing", "--severity", "high")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        assert created.exists(), f"File not created at {created}"
        content = created.read_text(encoding="utf-8")
        assert "id: T001" in content
        assert "title: Fix the thing" in content
        assert "severity: high" in content
        assert "status: open" in content
        assert "- [ ] (fill in)" in content

    def test_auto_id_increments(self, tmp_path):
        """Second ticket gets T002 when T001 already exists in archive."""
        harness = _setup(tmp_path)
        # Seed a T001 in archive
        (harness / "docs" / "archive" / "T001-old.md").write_text("---\nid: T001\n---\n")

        result = _run(harness, "Second ticket")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        content = created.read_text(encoding="utf-8")
        assert "id: T002" in content

    def test_ac_flag_populates_acs(self, tmp_path):
        """--ac flags write checked ACs into the file."""
        harness = _setup(tmp_path)
        result = _run(harness, "Ticket with ACs", "--ac", "AC one", "--ac", "AC two")
        assert result.returncode == 0, result.stderr

        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "- [ ] AC one" in content
        assert "- [ ] AC two" in content
        assert "(fill in)" not in content

    def test_workspace_routing(self, tmp_path):
        """--workspace routes to workspace internal tickets/open/."""
        harness = _setup(tmp_path)
        ws = harness / "workspaces" / "myws"
        (ws / "internal" / "tickets" / "open").mkdir(parents=True)
        (ws / "internal" / "archive").mkdir(parents=True)
        (ws / "internal" / "tickets" / "INDEX.md").write_text("# Index\n")
        (ws / "internal" / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n"
        )
        ws.joinpath("workspace.yaml").write_text("name: myws\n", encoding="utf-8")

        result = _run(harness, "Workspace ticket", "--workspace", "myws")
        assert result.returncode == 0, result.stderr

        created = Path(result.stdout.strip())
        assert "myws" in str(created) or "internal" in str(created), \
            f"Expected ticket in workspace dir, got: {created}"
        assert created.exists()

    def test_index_regenerated(self, tmp_path):
        """INDEX.md is rewritten after ticket creation."""
        harness = _setup(tmp_path)
        original = (harness / "docs" / "tickets" / "INDEX.md").read_text()
        result = _run(harness, "Index test ticket")
        assert result.returncode == 0, result.stderr
        updated = (harness / "docs" / "tickets" / "INDEX.md").read_text()
        assert updated != original, "INDEX.md must be regenerated"

    def test_prints_created_path(self, tmp_path):
        """Script prints the absolute path of the created file to stdout."""
        harness = _setup(tmp_path)
        result = _run(harness, "Path print test")
        assert result.returncode == 0, result.stderr
        printed = result.stdout.strip()
        assert printed.endswith(".md"), f"Expected .md path in stdout, got: {printed!r}"
        assert Path(printed).exists()

    def test_unknown_workspace_exits_nonzero(self, tmp_path):
        """--workspace with non-existent slug exits 1."""
        harness = _setup(tmp_path)
        result = _run(harness, "Bad workspace", "--workspace", "does-not-exist")
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    # T092: --layer flag
    def test_layer_flag_writes_to_frontmatter(self, tmp_path):
        """--layer overrides the default 'tooling' value."""
        harness = _setup(tmp_path)
        result = _run(harness, "Infra ticket", "--layer", "infra")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "layer: infra" in content

    def test_default_layer_is_tooling(self, tmp_path):
        """Default layer is 'tooling' when --layer is omitted."""
        harness = _setup(tmp_path)
        result = _run(harness, "Default layer ticket")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "layer: tooling" in content

    def test_invalid_layer_exits_nonzero(self, tmp_path):
        """Invalid --layer value exits non-zero."""
        harness = _setup(tmp_path)
        result = _run(harness, "Bad layer", "--layer", "nonexistent")
        assert result.returncode != 0

    # T093: --repo flag
    def test_repo_flag_writes_to_frontmatter(self, tmp_path):
        """--repo emits 'repo: <slug>' in frontmatter."""
        harness = _setup(tmp_path)
        result = _run(harness, "Repo ticket", "--repo", "myrepo")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "repo: myrepo" in content

    def test_no_repo_flag_leaves_repo_commented(self, tmp_path):
        """Omitting --repo leaves repo field commented out."""
        harness = _setup(tmp_path)
        result = _run(harness, "No repo ticket")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "repo: myrepo" not in content
        assert "# repo:" in content


def _add_workspace(harness: Path, slug: str = "myws") -> Path:
    """Create a workspace skeleton under harness. Returns its internal dir."""
    ws = harness / "workspaces" / slug
    internal = ws / "internal"
    (internal / "tickets" / "open").mkdir(parents=True)
    (internal / "tickets" / "closed").mkdir(parents=True)
    (internal / "archive").mkdir(parents=True)
    (internal / "tickets" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (internal / "sessions.md").write_text(
        "## Session Log\n\nS1 2026-01-01: init\n", encoding="utf-8"
    )
    ws.joinpath("workspace.yaml").write_text(f"name: {slug}\n", encoding="utf-8")
    return internal


class TestSessionAwareRouting:
    """T140: a bare invocation (no --workspace) must consult .claude/.active_workspace
    and never silently create a HARNESS ticket from a workspace/undeclared session.
    Mirrors generate_ticket_index.py (T136): harness session → harness layer; workspace
    or undeclared session → fail closed; explicit --workspace always wins.
    """

    def _state(self, harness: Path, value: str | None) -> None:
        state_file = harness / ".claude" / ".active_workspace"
        if value is None:
            state_file.unlink()
        else:
            state_file.write_text(value, encoding="utf-8")

    def test_bare_in_harness_session_creates_harness_ticket(self, tmp_path):
        harness = _setup(tmp_path)  # __harness__ declared by _setup
        result = _run(harness, "Harness bare ticket")
        assert result.returncode == 0, result.stderr
        created = Path(result.stdout.strip())
        assert created.exists()
        assert "docs/tickets/open" in str(created), created

    def test_bare_in_workspace_session_fails_closed(self, tmp_path):
        harness = _setup(tmp_path)
        _add_workspace(harness, "scrabble-score")
        self._state(harness, "scrabble-score")
        result = _run(harness, "Should not become a harness ticket")
        assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
        # Error must name the active slug and hand over the exact recovery command.
        assert "scrabble-score" in result.stderr
        assert "--workspace scrabble-score" in result.stderr
        # And nothing was written to the harness layer.
        assert not list((harness / "docs" / "tickets" / "open").glob("T*.md"))

    def test_bare_undeclared_session_fails_closed(self, tmp_path):
        harness = _setup(tmp_path)
        self._state(harness, None)  # remove the state file → undeclared
        result = _run(harness, "Undeclared bare ticket")
        assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
        assert "session-start" in result.stderr
        assert not list((harness / "docs" / "tickets" / "open").glob("T*.md"))

    def test_bare_empty_state_fails_closed(self, tmp_path):
        harness = _setup(tmp_path)
        self._state(harness, "")  # empty → undeclared
        result = _run(harness, "Empty state bare ticket")
        assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)

    def test_explicit_workspace_wins_over_workspace_session(self, tmp_path):
        # --workspace always wins, even when a (different) workspace session is declared.
        harness = _setup(tmp_path)
        _add_workspace(harness, "target-ws")
        self._state(harness, "other-ws")
        result = _run(harness, "Explicit routes regardless of state",
                      "--workspace", "target-ws")
        assert result.returncode == 0, result.stderr
        created = Path(result.stdout.strip())
        assert "target-ws" in str(created), created

    def test_explicit_workspace_wins_in_harness_session(self, tmp_path):
        harness = _setup(tmp_path)  # __harness__ declared
        _add_workspace(harness, "target-ws")
        result = _run(harness, "Explicit workspace from harness session",
                      "--workspace", "target-ws")
        assert result.returncode == 0, result.stderr
        assert "target-ws" in str(Path(result.stdout.strip()))

    def test_harness_flag_bypasses_session_check(self, tmp_path):
        # --harness asserts harness intent for programmatic callers
        # (promote_raised_concern.py) regardless of ambient session state.
        harness = _setup(tmp_path)
        self._state(harness, "some-workspace")  # would otherwise fail closed
        result = _run(harness, "Programmatic harness ticket", "--harness")
        assert result.returncode == 0, result.stderr
        created = Path(result.stdout.strip())
        assert "docs/tickets/open" in str(created), created

    def test_harness_flag_works_when_undeclared(self, tmp_path):
        harness = _setup(tmp_path)
        self._state(harness, None)  # undeclared
        result = _run(harness, "Harness flag undeclared", "--harness")
        assert result.returncode == 0, result.stderr
        assert "docs/tickets/open" in str(Path(result.stdout.strip()))

    def test_harness_and_workspace_mutually_exclusive(self, tmp_path):
        harness = _setup(tmp_path)
        _add_workspace(harness, "myws")
        result = _run(harness, "Conflicting flags", "--harness", "--workspace", "myws")
        assert result.returncode != 0
        assert "not allowed with" in result.stderr or "mutually exclusive" in result.stderr.lower()


class TestPerLayerNumbering:
    """T135: the T-number counter is scoped to the target layer, not global.

    Previously _next_id() scanned harness + every workspace and returned the
    global max+1, so a workspace whose own tickets were T001-T018 got the next
    harness number (T135). The --workspace flag routed only the destination dir.
    """

    def test_workspace_numbering_ignores_harness(self, tmp_path):
        # harness up to T100; workspace's own max is T005 → workspace yields T006.
        harness = _setup(tmp_path)
        (harness / "docs" / "archive" / "T100-harness.md").write_text(
            "---\nid: T100\n---\n", encoding="utf-8"
        )
        internal = _add_workspace(harness)
        (internal / "tickets" / "open" / "T005-ws.md").write_text(
            "---\nid: T005\n---\n", encoding="utf-8"
        )
        result = _run(harness, "Workspace-scoped number", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "id: T006" in content, content
        assert "id: T101" not in content

    def test_harness_numbering_ignores_workspace(self, tmp_path):
        # workspace has a high T200; harness's own max is T003 → harness yields T004.
        harness = _setup(tmp_path)
        (harness / "docs" / "archive" / "T003-harness.md").write_text(
            "---\nid: T003\n---\n", encoding="utf-8"
        )
        internal = _add_workspace(harness)
        (internal / "archive" / "T200-ws.md").write_text(
            "---\nid: T200\n---\n", encoding="utf-8"
        )
        result = _run(harness, "Harness-scoped number")  # no --workspace
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "id: T004" in content, content
        assert "id: T201" not in content

    def test_workspace_scan_includes_its_closed_dir(self, tmp_path):
        # The workspace's own tickets/closed/ must count (the original scan
        # omitted it, scanning only open + archive).
        harness = _setup(tmp_path)
        internal = _add_workspace(harness)
        (internal / "tickets" / "closed" / "T050-ws.md").write_text(
            "---\nid: T050\n---\n", encoding="utf-8"
        )
        result = _run(harness, "After closed ticket", "--workspace", "myws")
        assert result.returncode == 0, result.stderr
        content = Path(result.stdout.strip()).read_text(encoding="utf-8")
        assert "id: T051" in content, content
