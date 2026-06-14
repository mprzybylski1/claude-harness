"""
Tests for T079: close_ticket.py --files flag stages code/test paths alongside archive move.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import git_init, make_harness_tree, run_close_ticket

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


def _git_status_staged(repo: Path) -> list[str]:
    """Return lines from git status --porcelain where the index column is not blank."""
    out = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [ln for ln in out.splitlines() if ln[:1] not in ("", " ", "?")]


class TestCloseTicketStageFiles:
    """T079: --files stages code/test paths alongside archive move."""

    # ── Happy path: --files stages code + archive in one operation ───────────

    def test_files_flag_stages_code_alongside_archive(self, tmp_path):
        """--files foo.py bar.py → all five paths staged together (delete open, add archive,
        update INDEX.md, update foo.py, update bar.py)."""
        make_harness_tree(tmp_path, OPEN_TICKET)

        scripts_dir = tmp_path / "scripts" / "tools"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        foo = scripts_dir / "foo.py"
        bar = scripts_dir / "bar.py"
        foo.write_text("# v1\n")
        bar.write_text("# v1\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(foo), str(bar)],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "add scripts"],
                       check=True, capture_output=True)
        foo.write_text("# v2\n")
        bar.write_text("# v2\n")

        result = run_close_ticket(tmp_path, "T999", "--resolution", "done",
                                  "--files", str(foo), str(bar))
        assert result.returncode == 0, result.stderr

        staged = _git_status_staged(tmp_path)
        staged_str = "\n".join(staged)

        assert any("T999" in ln and "open" in ln for ln in staged), \
            f"open/ ticket deletion not staged:\n{staged_str}"
        assert any("T999" in ln and "archive" in ln for ln in staged), \
            f"archive file not staged:\n{staged_str}"
        assert any("INDEX.md" in ln for ln in staged), \
            f"INDEX.md not staged:\n{staged_str}"
        assert any("foo.py" in ln for ln in staged), \
            f"foo.py not staged:\n{staged_str}"
        assert any("bar.py" in ln for ln in staged), \
            f"bar.py not staged:\n{staged_str}"

    def test_files_flag_no_unstaged_residue(self, tmp_path):
        """After --files close, the named code files must not appear as unstaged."""
        make_harness_tree(tmp_path, OPEN_TICKET)
        scripts_dir = tmp_path / "scripts" / "tools"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        code = scripts_dir / "helper.py"
        code.write_text("# v1\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(code)],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "add helper"],
                       check=True, capture_output=True)
        code.write_text("# v2\n")

        run_close_ticket(tmp_path, "T999", "--resolution", "done", "--files", str(code))

        all_status = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        unstaged = [ln for ln in all_status.splitlines() if len(ln) >= 2 and ln[1] != " "]
        assert not any("helper.py" in ln for ln in unstaged), \
            f"helper.py must not appear as unstaged after --files close:\n{all_status}"

    # ── Validation: exit before moving ticket ────────────────────────────────

    def test_nonexistent_files_path_exits_before_move(self, tmp_path):
        """--files with a nonexistent path exits nonzero WITHOUT moving the ticket."""
        ticket = make_harness_tree(tmp_path, OPEN_TICKET)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done",
                                  "--files", str(tmp_path / "nonexistent.py"))
        assert result.returncode != 0
        assert "ERROR" in result.stderr
        assert ticket.exists(), "ticket must not be moved when --files validation fails"
        assert not (tmp_path / "docs" / "archive" / ticket.name).exists(), \
            "archive must not be created when --files validation fails"

    def test_directory_as_files_path_exits_before_move(self, tmp_path):
        """--files with a directory exits nonzero WITHOUT moving the ticket."""
        ticket = make_harness_tree(tmp_path, OPEN_TICKET)
        some_dir = tmp_path / "scripts"
        some_dir.mkdir(exist_ok=True)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done",
                                  "--files", str(some_dir))
        assert result.returncode != 0
        assert "ERROR" in result.stderr
        assert ticket.exists(), "ticket must not be moved when --files is a directory"

    # ── Warning when --files is omitted ─────────────────────────────────────

    def test_no_files_warns_when_unstaged_code_exists(self, tmp_path):
        """Omitting --files warns when unstaged non-doc files exist in the repo."""
        make_harness_tree(tmp_path, OPEN_TICKET)

        scripts_dir = tmp_path / "scripts" / "tools"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        code = scripts_dir / "myscript.py"
        code.write_text("# v1\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(code)],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "add script"],
                       check=True, capture_output=True)
        code.write_text("# v2 — modified\n")

        result = run_close_ticket(tmp_path, "T999", "--resolution", "done")
        assert result.returncode == 0, result.stderr
        assert "--files" in result.stderr or "no code files staged" in result.stderr.lower(), \
            f"Expected unstaged-code warning mentioning --files in stderr:\n{result.stderr}"

    def test_no_files_no_warning_when_no_unstaged_code(self, tmp_path):
        """Omitting --files must NOT warn when there are no unstaged code files."""
        make_harness_tree(tmp_path, OPEN_TICKET)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done")
        assert result.returncode == 0, result.stderr
        assert "no code files staged" not in result.stderr.lower(), \
            f"Spurious --files warning when no unstaged code exists:\n{result.stderr}"

    def test_no_files_no_warning_when_code_already_staged(self, tmp_path):
        """Omitting --files must NOT warn when a code file is already staged (T087)."""
        make_harness_tree(tmp_path, OPEN_TICKET)
        scripts_dir = tmp_path / "scripts" / "tools"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        code = scripts_dir / "already_staged.py"
        code.write_text("# v1\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(code)],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "add"],
                       check=True, capture_output=True)
        code.write_text("# v2\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(code)],
                       check=True, capture_output=True)

        result = run_close_ticket(tmp_path, "T999", "--resolution", "done")
        assert result.returncode == 0, result.stderr
        assert "no code files staged" not in result.stderr.lower(), \
            f"Spurious warning for already-staged code file:\n{result.stderr}"

    # ── Workspace: --files routed to correct git root ────────────────────────

    def test_workspace_files_staged_in_project_repo(self, tmp_path):
        """--files paths from a workspace project repo are staged in that project repo."""
        harness = tmp_path / "harness"
        (harness / "docs" / "tickets" / "open").mkdir(parents=True)
        (harness / "docs" / "archive").mkdir(parents=True)
        (harness / "docs" / "tickets" / "INDEX.md").write_text("# Index\n")
        (harness / "docs" / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n"
        )
        tools = harness / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
        (tools / "generate_ticket_index.py").write_text(
            "import sys; from pathlib import Path\n"
            "args = sys.argv\n"
            "if '--output' in args:\n"
            "    Path(args[args.index('--output') + 1]).write_text('# Updated\\n')\n"
        )

        project = tmp_path / "project"
        harness_dir = project / ".harness"
        (harness_dir / "tickets" / "open").mkdir(parents=True)
        (harness_dir / "archive").mkdir(parents=True)
        (harness_dir / "tickets" / "INDEX.md").write_text("# Index\n")
        (harness_dir / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n"
        )
        ticket = harness_dir / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(OPEN_TICKET, encoding="utf-8")

        src_dir = project / "src"
        src_dir.mkdir()
        code_file = src_dir / "main.py"
        code_file.write_text("# v1\n")

        git_init(project)
        code_file.write_text("# v2\n")
        git_init(harness)

        ws_dir = harness / "workspaces" / "test-ws"
        (ws_dir / "internal" / "tickets" / "open").mkdir(parents=True)
        ws_dir.joinpath("workspace.yaml").write_text(
            f"name: test-ws\ndocs_path: {harness_dir}\n", encoding="utf-8"
        )

        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done",
            "--files", str(code_file),
        )
        assert result.returncode == 0, f"Expected exit 0; got {result.returncode}\n{result.stderr}"

        proj_status = subprocess.run(
            ["git", "-C", str(project), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        harness_status = subprocess.run(
            ["git", "-C", str(harness), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout

        assert "main.py" in proj_status, \
            f"main.py must be staged in project repo:\n{proj_status}"
        assert "main.py" not in harness_status, \
            f"main.py must not appear in harness repo staging:\n{harness_status}"

    # ── T084: staged-files summary in stdout ─────────────────────────────────

    def test_staging_summary_printed_on_success(self, tmp_path):
        """After staging, stdout must include 'staged:' lines for the archive and INDEX."""
        make_harness_tree(tmp_path, OPEN_TICKET)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done")
        assert result.returncode == 0, result.stderr
        assert "staged:" in result.stdout.lower(), \
            f"Expected staging summary in stdout:\n{result.stdout}"

    def test_staging_summary_includes_files_flag_paths(self, tmp_path):
        """--files paths must appear in the staging summary."""
        make_harness_tree(tmp_path, OPEN_TICKET)
        scripts_dir = tmp_path / "scripts" / "tools"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        code = scripts_dir / "myscript.py"
        code.write_text("# v1\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(code)],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "add"],
                       check=True, capture_output=True)
        code.write_text("# v2\n")

        result = run_close_ticket(tmp_path, "T999", "--resolution", "done", "--files", str(code))
        assert result.returncode == 0, result.stderr
        assert "myscript.py" in result.stdout, \
            f"Expected --files path in staging summary:\n{result.stdout}"

    # ── T098: gitignored --files rejected upfront ────────────────────────────

    def test_gitignored_file_in_files_exits_before_move(self, tmp_path):
        """--files with a gitignored path exits nonzero WITHOUT moving the ticket (T098)."""
        ticket = make_harness_tree(tmp_path, OPEN_TICKET)
        (tmp_path / ".gitignore").write_text("ignored_file.py\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", str(tmp_path / ".gitignore")],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "add gitignore"],
                       check=True, capture_output=True)
        ignored = tmp_path / "ignored_file.py"
        ignored.write_text("# ignored\n")

        result = run_close_ticket(tmp_path, "T999", "--resolution", "done", "--files", str(ignored))
        assert result.returncode != 0, "Should fail for gitignored --files path"
        assert "ignore" in result.stderr.lower() or "gitignore" in result.stderr.lower(), \
            f"Expected gitignore mention in stderr:\n{result.stderr}"
        assert ticket.exists(), "ticket must not be moved when --files contains a gitignored path"
        assert not (tmp_path / "docs" / "archive" / ticket.name).exists(), \
            "archive must not be created when --files validation fails"

    # ── T099: extra_files staged before ticket move ───────────────────────────

    def test_staging_failure_leaves_ticket_in_open(self, tmp_path):
        """If --files path does not exist, ticket stays in open/ (T099 — atomic ordering)."""
        ticket = make_harness_tree(tmp_path, OPEN_TICKET)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done",
                                  "--files", str(tmp_path / "does_not_exist.py"))
        assert result.returncode != 0
        assert ticket.exists(), "ticket must remain in open/ when --files fails"
        assert not (tmp_path / "docs" / "archive" / ticket.name).exists()


class TestCloseTicketCrossRepoFiles:
    """T159: --files may span multiple git repos — stage + commit each repo separately
    (one commit per root, shared message). Only a path in NO git repo is rejected.
    (Supersedes the T125 blanket reject; see Invariant 3.)"""

    def _setup_workspace(self, tmp_path: Path) -> tuple[Path, Path, Path, Path]:
        """Build a harness repo + a workspace project repo with docs_path pointing into the project.

        Returns (harness_root, project_root, ticket_path, project_code_file).
        """
        harness = tmp_path / "harness"
        (harness / "docs" / "tickets" / "open").mkdir(parents=True)
        (harness / "docs" / "archive").mkdir(parents=True)
        (harness / "docs" / "tickets" / "INDEX.md").write_text("# Index\n")
        (harness / "docs" / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n"
        )
        tools = harness / "scripts" / "tools"
        tools.mkdir(parents=True)
        (tools / "current_session.py").write_text("import sys\nprint('S9')\n")
        (tools / "generate_ticket_index.py").write_text(
            "import sys; from pathlib import Path\n"
            "args = sys.argv\n"
            "if '--output' in args:\n"
            "    Path(args[args.index('--output') + 1]).write_text('# Updated\\n')\n"
        )
        harness_side_file = harness / "scripts" / "tools" / "shared.py"
        harness_side_file.write_text("# v1\n")

        project = tmp_path / "project"
        harness_dir = project / ".harness"
        (harness_dir / "tickets" / "open").mkdir(parents=True)
        (harness_dir / "archive").mkdir(parents=True)
        (harness_dir / "tickets" / "INDEX.md").write_text("# Index\n")
        (harness_dir / "sessions.md").write_text(
            "## Session Log\n\nS1 2026-01-01: init\n"
        )
        ticket = harness_dir / "tickets" / "open" / "T999-synthetic-test-ticket.md"
        ticket.write_text(OPEN_TICKET, encoding="utf-8")

        src_dir = project / "src"
        src_dir.mkdir()
        project_code = src_dir / "main.py"
        project_code.write_text("# v1\n")

        git_init(project)
        project_code.write_text("# v2\n")
        git_init(harness)
        harness_side_file.write_text("# v2\n")

        ws_dir = harness / "workspaces" / "test-ws"
        (ws_dir / "internal" / "tickets" / "open").mkdir(parents=True)
        ws_dir.joinpath("workspace.yaml").write_text(
            f"name: test-ws\ndocs_path: {harness_dir}\n", encoding="utf-8"
        )

        return harness, project, ticket, project_code

    def test_workspace_ticket_stages_harness_rooted_file(self, tmp_path):
        """Workspace ticket + harness-repo --files path → succeeds; file staged in harness repo."""
        harness, project, ticket, _ = self._setup_workspace(tmp_path)
        harness_file = harness / "scripts" / "tools" / "shared.py"

        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done",
            "--files", str(harness_file),
        )
        assert result.returncode == 0, (
            f"Cross-repo --files should now succeed, got {result.returncode}\n{result.stderr}"
        )
        assert not ticket.exists(), "ticket should be archived"
        harness_status = subprocess.run(
            ["git", "-C", str(harness), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        assert "shared.py" in harness_status and any(
            "shared.py" in ln and ln[:1] not in (" ", "?") for ln in harness_status.splitlines()
        ), f"shared.py must be staged in the harness repo:\n{harness_status}"

    def test_workspace_ticket_mixed_files_staged_in_both_repos(self, tmp_path):
        """Mixed --files: project file staged in project repo, harness file in harness repo."""
        harness, project, ticket, project_code = self._setup_workspace(tmp_path)
        harness_file = harness / "scripts" / "tools" / "shared.py"

        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done",
            "--files", str(project_code), str(harness_file),
        )
        assert result.returncode == 0, result.stderr
        proj_status = subprocess.run(
            ["git", "-C", str(project), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        harness_status = subprocess.run(
            ["git", "-C", str(harness), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout
        assert "main.py" in proj_status, f"project file must stage in project repo:\n{proj_status}"
        assert "shared.py" in harness_status, f"harness file must stage in harness repo:\n{harness_status}"

    def test_cross_repo_commit_lands_in_each_repo(self, tmp_path):
        """--commit with cross-repo --files creates one commit per repo, shared message."""
        harness, project, ticket, project_code = self._setup_workspace(tmp_path)
        harness_file = harness / "scripts" / "tools" / "shared.py"

        def _head_subject(repo: Path) -> str:
            return subprocess.run(
                ["git", "-C", str(repo), "log", "-1", "--format=%s"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()

        before_project = _head_subject(project)
        before_harness = _head_subject(harness)

        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done",
            "--files", str(project_code), str(harness_file), "--commit",
        )
        assert result.returncode == 0, result.stderr
        after_project = _head_subject(project)
        after_harness = _head_subject(harness)
        assert after_project != before_project, "a new commit must land in the project repo"
        assert after_harness != before_harness, "a new commit must land in the harness repo"
        # Shared ticket-derived message (fix prefix because code files are included).
        assert "T999" in after_project and "T999" in after_harness
        assert after_project == after_harness, "both repos must share the ticket commit message"

    def test_files_path_in_no_repo_rejected(self, tmp_path):
        """A --files path inside NO git repo is still rejected; ticket stays in open/."""
        harness, project, ticket, _ = self._setup_workspace(tmp_path)
        loose = tmp_path / "loose.py"  # tmp_path itself is not a git repo
        loose.write_text("# loose\n")

        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done",
            "--files", str(loose),
        )
        assert result.returncode != 0, "a path in no git repo must be rejected"
        assert ticket.exists(), "ticket must remain in open/ when --files is rejected"

    def test_workspace_ticket_workspace_files_still_works(self, tmp_path):
        """Regression: workspace ticket + workspace-project --files closes cleanly."""
        harness, project, _, project_code = self._setup_workspace(tmp_path)
        result = run_close_ticket(
            harness, "T999", "--workspace", "test-ws", "--resolution", "done",
            "--files", str(project_code),
        )
        assert result.returncode == 0, (
            f"Expected success for workspace-only --files, got:\n{result.stderr}"
        )


class TestCloseTicketTickAcs:
    """T100: --tick-acs auto-checks unchecked ACs before close."""

    OPEN_TICKET_UNCHECKED = """\
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

- [ ] AC one
- [ ] AC two
- [ ] AC three

## Resolution
(Fill in on close.)
"""

    def test_tick_acs_allows_close_with_unchecked_acs(self, tmp_path):
        """--tick-acs marks all unchecked ACs and closes successfully."""
        make_harness_tree(tmp_path, self.OPEN_TICKET_UNCHECKED)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done", "--tick-acs")
        assert result.returncode == 0, f"Expected success with --tick-acs:\n{result.stderr}"
        archive = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        assert archive.exists()
        content = archive.read_text(encoding="utf-8")
        assert "- [ ]" not in content, "All ACs must be ticked in archived ticket"
        assert content.count("- [x]") == 3, "All 3 ACs must be ticked"

    def test_tick_acs_and_force_are_mutually_exclusive(self, tmp_path):
        """--tick-acs and --force together must be rejected."""
        make_harness_tree(tmp_path, self.OPEN_TICKET_UNCHECKED)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done", "--tick-acs", "--force")
        assert result.returncode != 0, "Expected error when both --tick-acs and --force used"

    def test_tick_acs_without_flag_still_blocked(self, tmp_path):
        """Without --tick-acs or --force, unchecked ACs block the close."""
        make_harness_tree(tmp_path, self.OPEN_TICKET_UNCHECKED)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done")
        assert result.returncode != 0
        assert "unchecked" in result.stderr.lower() or "AC" in result.stderr

    def test_tick_acs_scoped_to_ac_section_only(self, tmp_path):
        """--tick-acs must not rewrite '- [ ]' checkboxes outside the Acceptance Criteria section."""
        ticket_content = """\
---
id: T999
title: Tick scope test
severity: low
status: open
phase: 2
layer: tooling
opened: S1 2026-01-01
closed:
---

## Problem

- [ ] This checkbox is in Problem, not ACs — must NOT be ticked

## Acceptance Criteria

- [ ] AC one
- [ ] AC two

## Resolution
(Fill in on close.)
"""
        make_harness_tree(tmp_path, ticket_content)
        result = run_close_ticket(tmp_path, "T999", "--resolution", "done", "--tick-acs")
        assert result.returncode == 0, f"Expected success:\n{result.stderr}"
        archive = tmp_path / "docs" / "archive" / "T999-synthetic-test-ticket.md"
        content = archive.read_text(encoding="utf-8")
        assert "- [x] AC one" in content
        assert "- [x] AC two" in content
        assert "- [ ] This checkbox is in Problem" in content, \
            "Problem-section checkbox must not be ticked by --tick-acs"
