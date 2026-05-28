"""Tests for T106: promote_raised_concern.py."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "promote_raised_concern.py"

_SR_BODY = """\
---
id: SR-001
from: myws
raised: S5 2026-05-27
title: Fix the broken thing
severity: high
status: raised
harness_ticket:
---

## Context

Something broke because of X.

## Proposed change

Do Y to fix it.

## Harness disposition

(Filled by harness on promotion or rejection.)
"""


def _setup(tmp_path: Path, slug: str = "myws") -> tuple[Path, Path]:
    """Minimal harness + workspace skeleton. Returns (harness, sr_path)."""
    (tmp_path / "docs" / "tickets" / "open").mkdir(parents=True)
    (tmp_path / "docs" / "archive").mkdir(parents=True)
    (tmp_path / "docs" / "tickets" / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (tmp_path / "docs" / "sessions.md").write_text(
        "## Session Log\n\nS9 2026-01-01: init\n", encoding="utf-8"
    )
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text("print('S9')\n", encoding="utf-8")
    (tools / "generate_ticket_index.py").write_text(
        "import os; from pathlib import Path\n"
        "root = Path(os.environ.get('HARNESS_ROOT', '.'))\n"
        "(root / 'docs' / 'tickets' / 'INDEX.md').write_text('# Updated\\n')\n",
        encoding="utf-8",
    )
    ws_dir = tmp_path / "workspaces" / slug
    raised_dir = ws_dir / "raised"
    (raised_dir / "archive").mkdir(parents=True)
    (ws_dir / "workspace.yaml").write_text(f"name: {slug}\n", encoding="utf-8")
    sr_path = raised_dir / "SR-001-fix-the-broken-thing.md"
    sr_path.write_text(_SR_BODY, encoding="utf-8")
    return tmp_path, sr_path


def _run(harness: Path, *args: str) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
        env={**_os.environ, "HARNESS_ROOT": str(harness), "PYTHONPATH": str(ROOT)},
    )


def _open_ticket(harness: Path) -> Path:
    tickets = list((harness / "docs" / "tickets" / "open").glob("T*.md"))
    assert len(tickets) == 1, f"Expected 1 ticket, found: {tickets}"
    return tickets[0]


class TestPromoteRaisedConcern:

    def test_happy_path_exits_zero(self, tmp_path):
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr

    def test_harness_ticket_created_with_correct_title_and_severity(self, tmp_path):
        """Ticket file created in docs/tickets/open/ with SR title and severity."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "Fix the broken thing" in content
        assert "severity: high" in content

    def test_ticket_has_source_field(self, tmp_path):
        """Ticket frontmatter contains source: myws/SR-001."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "source: myws/SR-001" in content

    def test_sr_status_updated_to_promoted(self, tmp_path):
        """SR file status field changes from raised to promoted."""
        harness, sr_path = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "status: promoted" in content
        assert "status: raised" not in content

    def test_sr_harness_ticket_field_updated(self, tmp_path):
        """SR file harness_ticket field is set to the new ticket ID."""
        harness, sr_path = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert re.search(r"harness_ticket:\s*T\d+", content), \
            f"harness_ticket not updated:\n{content}"

    def test_body_copied_to_problem_section(self, tmp_path):
        """SR Context content is placed in the ticket Problem section."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "Something broke because of X" in content

    def test_proposed_change_copied(self, tmp_path):
        """SR Proposed change section is also copied into the ticket body."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "Do Y to fix it" in content

    def test_harness_disposition_not_copied(self, tmp_path):
        """Harness disposition section is NOT copied into the ticket body."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "Harness disposition" not in content

    def test_refuses_if_already_promoted(self, tmp_path):
        """Exits non-zero when SR status is already promoted."""
        harness, sr_path = _setup(tmp_path)
        text = sr_path.read_text(encoding="utf-8")
        sr_path.write_text(text.replace("status: raised", "status: promoted"), encoding="utf-8")
        result = _run(harness, "myws/SR-001")
        assert result.returncode != 0
        assert "raised" in result.stderr or "promoted" in result.stderr

    def test_refuses_if_resolved(self, tmp_path):
        """Exits non-zero when SR status is resolved (terminal)."""
        harness, sr_path = _setup(tmp_path)
        text = sr_path.read_text(encoding="utf-8")
        sr_path.write_text(text.replace("status: raised", "status: resolved"), encoding="utf-8")
        result = _run(harness, "myws/SR-001")
        assert result.returncode != 0

    def test_sr_not_found_exits_nonzero(self, tmp_path):
        """Non-existent SR ID causes exit non-zero with ERROR."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-999")
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_bad_usage_exits_nonzero(self, tmp_path):
        """Missing slug/SR-NNN format exits non-zero."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "SR-001")
        assert result.returncode != 0


_MULTI_SECTION_SR = """\
---
id: SR-001
from: myws
raised: S5 2026-05-27
title: Multi-section SR
severity: high
status: raised
harness_ticket:
---

## Context

Context body that should be copied.

## Principle

PRINCIPLE_BODY_DO_NOT_COPY

## Boundary slot

BOUNDARY_BODY_DO_NOT_COPY

## File format

FILE_FORMAT_BODY_DO_NOT_COPY

## Proposed change

Proposed body that should be copied.

## CLIs to build

CLIS_BODY_DO_NOT_COPY

## Guardrails

GUARDRAILS_BODY_DO_NOT_COPY

## Harness disposition

(Filled by harness.)
"""


class TestLayerFlag:
    """T119: promote_raised_concern.py accepts --layer to override default."""

    def test_layer_flag_sets_ticket_layer(self, tmp_path):
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001", "--layer", "infra")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "layer: infra" in content

    def test_default_layer_is_tooling(self, tmp_path):
        """Backwards compat: omitting --layer still produces layer: tooling."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "layer: tooling" in content

    def test_invalid_layer_rejected(self, tmp_path):
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001", "--layer", "nonsense")
        assert result.returncode != 0


class TestExtractBodyH2Boundary:
    """T117: _extract_body must stop at any unknown H2, not just the stop_on allowlist."""

    def test_unknown_h2_between_copy_sections_not_included(self, tmp_path):
        """## Principle, ## Boundary slot, ## File format between Context and
        Proposed change must NOT appear in the ticket body."""
        harness, sr_path = _setup(tmp_path)
        sr_path.write_text(_MULTI_SECTION_SR, encoding="utf-8")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "PRINCIPLE_BODY_DO_NOT_COPY" not in content
        assert "BOUNDARY_BODY_DO_NOT_COPY" not in content
        assert "FILE_FORMAT_BODY_DO_NOT_COPY" not in content

    def test_unknown_h2_after_proposed_change_not_included(self, tmp_path):
        """Sections between Proposed change and Harness disposition (## CLIs to
        build, ## Guardrails) must NOT appear in the ticket body."""
        harness, sr_path = _setup(tmp_path)
        sr_path.write_text(_MULTI_SECTION_SR, encoding="utf-8")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "CLIS_BODY_DO_NOT_COPY" not in content
        assert "GUARDRAILS_BODY_DO_NOT_COPY" not in content

    def test_known_copy_sections_still_included(self, tmp_path):
        """Regression: Context and Proposed change bodies still copied through
        even when other H2 sections sit between them."""
        harness, sr_path = _setup(tmp_path)
        sr_path.write_text(_MULTI_SECTION_SR, encoding="utf-8")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "Context body that should be copied" in content
        assert "Proposed body that should be copied" in content

    def test_h3_subheadings_inside_copy_section_are_preserved(self, tmp_path):
        """### subheadings inside Context/Proposed change must NOT be treated as
        section terminators — they're part of the section content."""
        harness, sr_path = _setup(tmp_path)
        sr_with_h3 = """\
---
id: SR-001
from: myws
raised: S5 2026-05-27
title: H3 inside Context
severity: high
status: raised
harness_ticket:
---

## Context

Before subheading.

### Sub-section

H3_BODY_SHOULD_BE_COPIED

After subheading.

## Harness disposition

(skip)
"""
        sr_path.write_text(sr_with_h3, encoding="utf-8")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        content = _open_ticket(harness).read_text(encoding="utf-8")
        assert "H3_BODY_SHOULD_BE_COPIED" in content
        assert "Sub-section" in content


class TestProposedChangeACs:
    """T127: bullet/numbered list items in the SR's ## Proposed change section
    are carried into the harness ticket as Acceptance Criteria."""

    def _make_sr(self, sr_path: Path, proposed_change_body: str) -> None:
        sr_path.write_text(
            "---\n"
            "id: SR-001\nfrom: myws\nraised: S5 2026-05-27\n"
            "title: AC seeding test\nseverity: medium\nstatus: raised\n"
            "harness_ticket:\n---\n\n"
            "## Context\n\nSome context.\n\n"
            "## Proposed change\n\n" + proposed_change_body + "\n\n"
            "## Harness disposition\n\n(skip)\n",
            encoding="utf-8",
        )

    def _ac_block(self, ticket_content: str) -> str:
        """Return the Acceptance Criteria block (between ## AC and the next H2)."""
        m = re.search(
            r"## Acceptance Criteria\n(.*?)(?:\n## |\Z)",
            ticket_content,
            re.DOTALL,
        )
        assert m is not None, f"No AC section in ticket:\n{ticket_content}"
        return m.group(1)

    def test_bullet_list_becomes_acs(self, tmp_path):
        """- and * bullets in Proposed change → one AC each, default placeholder gone."""
        harness, sr_path = _setup(tmp_path)
        self._make_sr(sr_path,
                      "- Add fail-closed guard in foo()\n"
                      "- Update test_foo to cover the new branch\n"
                      "* Document the guard in CLAUDE.md")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        ac_block = self._ac_block(_open_ticket(harness).read_text(encoding="utf-8"))
        assert "- [ ] Add fail-closed guard in foo()" in ac_block
        assert "- [ ] Update test_foo to cover the new branch" in ac_block
        assert "- [ ] Document the guard in CLAUDE.md" in ac_block
        assert "(fill in)" not in ac_block

    def test_numbered_list_becomes_acs(self, tmp_path):
        """1. and 2) numbered list items in Proposed change → one AC each."""
        harness, sr_path = _setup(tmp_path)
        self._make_sr(sr_path,
                      "1. First step\n"
                      "2. Second step\n"
                      "3) Third step")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        ac_block = self._ac_block(_open_ticket(harness).read_text(encoding="utf-8"))
        assert "- [ ] First step" in ac_block
        assert "- [ ] Second step" in ac_block
        assert "- [ ] Third step" in ac_block
        assert "(fill in)" not in ac_block

    def test_prose_only_falls_back_to_placeholder(self, tmp_path):
        """No list items in Proposed change → ticket keeps create_ticket.py's
        default '- [ ] (fill in)' placeholder so operator can hand-fill."""
        harness, sr_path = _setup(tmp_path)
        self._make_sr(sr_path,
                      "We should refactor the foo module to use the bar pattern. "
                      "It will simplify the call sites and improve testability.")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        ac_block = self._ac_block(_open_ticket(harness).read_text(encoding="utf-8"))
        assert "- [ ] (fill in)" in ac_block

    def test_mixed_bullets_and_prose(self, tmp_path):
        """When bullets and prose are interleaved, only bullets become ACs;
        prose paragraphs do not leak into the AC list."""
        harness, sr_path = _setup(tmp_path)
        self._make_sr(sr_path,
                      "Here's what we should do:\n\n"
                      "- Replace the cached value\n"
                      "- Add a TTL guard\n\n"
                      "This will let downstream callers stop polling.")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        ac_block = self._ac_block(_open_ticket(harness).read_text(encoding="utf-8"))
        assert "- [ ] Replace the cached value" in ac_block
        assert "- [ ] Add a TTL guard" in ac_block
        # Prose lines must not be turned into ACs.
        assert "Here's what we should do" not in ac_block
        assert "This will let downstream callers" not in ac_block
        assert "(fill in)" not in ac_block

    def test_bullets_inside_fenced_code_block_are_ignored(self, tmp_path):
        """Bullet-like lines inside a fenced code block must not become ACs."""
        harness, sr_path = _setup(tmp_path)
        self._make_sr(sr_path,
                      "Run the migration script:\n\n"
                      "```bash\n"
                      "- old-flag  # looks like a bullet\n"
                      "- new-flag\n"
                      "```\n\n"
                      "- Verify the output matches expected")
        result = _run(harness, "myws/SR-001")
        assert result.returncode == 0, result.stderr
        ac_block = self._ac_block(_open_ticket(harness).read_text(encoding="utf-8"))
        assert "- [ ] Verify the output matches expected" in ac_block
        assert "old-flag" not in ac_block
        assert "new-flag" not in ac_block
