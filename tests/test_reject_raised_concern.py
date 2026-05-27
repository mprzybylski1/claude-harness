"""Tests for T107: reject_raised_concern.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "reject_raised_concern.py"

_SR_BODY = """\
---
id: SR-001
from: myws
raised: S5 2026-05-27
title: Fix the broken thing
severity: high
status: raised
harness_ticket:
resolved_in:
---

## Context

Something broke.

## Harness disposition

(Filled by harness on promotion or rejection.)
"""

_SR_BODY_NO_RESOLVED_IN = """\
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

Something broke.

## Harness disposition

(Filled by harness on promotion or rejection.)
"""


def _setup(tmp_path: Path, sr_body: str = _SR_BODY) -> tuple[Path, Path]:
    """Minimal harness + workspace skeleton. Returns (harness, sr_path)."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "sessions.md").write_text(
        "## Session Log\n\nS9 2026-01-01: init\n", encoding="utf-8"
    )
    tools = tmp_path / "scripts" / "tools"
    tools.mkdir(parents=True)
    (tools / "current_session.py").write_text("print('S9')\n", encoding="utf-8")
    ws_dir = tmp_path / "workspaces" / "myws"
    raised_dir = ws_dir / "raised"
    (raised_dir / "archive").mkdir(parents=True)
    (ws_dir / "workspace.yaml").write_text("name: myws\n", encoding="utf-8")
    sr_path = raised_dir / "SR-001-fix-the-broken-thing.md"
    sr_path.write_text(sr_body, encoding="utf-8")
    return tmp_path, sr_path


def _run(harness: Path, *args: str) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
        env={**_os.environ, "HARNESS_ROOT": str(harness), "PYTHONPATH": str(ROOT)},
    )


class TestRejectRaisedConcern:

    def test_happy_path_exits_zero(self, tmp_path):
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001", "--reason", "Out of scope for now.")
        assert result.returncode == 0, result.stderr

    def test_status_updated_to_rejected(self, tmp_path):
        """SR frontmatter status becomes rejected."""
        harness, sr_path = _setup(tmp_path)
        result = _run(harness, "myws/SR-001", "--reason", "Out of scope.")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "status: rejected" in content
        assert "status: raised" not in content

    def test_resolved_in_set_when_field_present(self, tmp_path):
        """resolved_in: is updated when field already exists in frontmatter."""
        harness, sr_path = _setup(tmp_path)
        result = _run(harness, "myws/SR-001", "--reason", "Irrelevant.")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "resolved_in: S9" in content

    def test_resolved_in_inserted_when_field_absent(self, tmp_path):
        """resolved_in: is inserted into frontmatter even when missing from original SR."""
        harness, sr_path = _setup(tmp_path, _SR_BODY_NO_RESOLVED_IN)
        result = _run(harness, "myws/SR-001", "--reason", "Irrelevant.")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "resolved_in: S9" in content

    def test_reason_appended_to_disposition_section(self, tmp_path):
        """Reason text appears in ## Harness disposition section."""
        harness, sr_path = _setup(tmp_path)
        result = _run(harness, "myws/SR-001", "--reason", "Does not align with phase goals.")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "Does not align with phase goals" in content
        disp_pos = content.index("## Harness disposition")
        reason_pos = content.index("Does not align with phase goals")
        assert reason_pos > disp_pos, "Reason must appear after ## Harness disposition header"

    def test_disposition_placeholder_replaced(self, tmp_path):
        """The (Filled by harness...) placeholder is removed."""
        harness, sr_path = _setup(tmp_path)
        result = _run(harness, "myws/SR-001", "--reason", "No.")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "(Filled by harness" not in content

    def test_refuses_if_already_rejected(self, tmp_path):
        """Exits non-zero when SR is already rejected (terminal)."""
        harness, sr_path = _setup(tmp_path)
        text = sr_path.read_text(encoding="utf-8")
        sr_path.write_text(text.replace("status: raised", "status: rejected"), encoding="utf-8")
        result = _run(harness, "myws/SR-001", "--reason", "Again.")
        assert result.returncode != 0
        assert "terminal" in result.stderr.lower() or "rejected" in result.stderr.lower()

    def test_refuses_if_resolved(self, tmp_path):
        """Exits non-zero when SR is resolved (terminal)."""
        harness, sr_path = _setup(tmp_path)
        text = sr_path.read_text(encoding="utf-8")
        sr_path.write_text(text.replace("status: raised", "status: resolved"), encoding="utf-8")
        result = _run(harness, "myws/SR-001", "--reason", "Moot.")
        assert result.returncode != 0

    def test_sr_not_found_exits_nonzero(self, tmp_path):
        """Non-existent SR ID exits non-zero with ERROR."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-999", "--reason", "Whatever.")
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_missing_reason_exits_nonzero(self, tmp_path):
        """--reason is required; missing it exits non-zero."""
        harness, _ = _setup(tmp_path)
        result = _run(harness, "myws/SR-001")
        assert result.returncode != 0

    def test_promoted_sr_can_be_rejected(self, tmp_path):
        """A promoted (not yet resolved) SR can still be rejected."""
        harness, sr_path = _setup(tmp_path)
        text = sr_path.read_text(encoding="utf-8")
        sr_path.write_text(
            text.replace("status: raised", "status: promoted")
                .replace("harness_ticket:", "harness_ticket: T999"),
            encoding="utf-8",
        )
        result = _run(harness, "myws/SR-001", "--reason", "Ticket superseded.")
        assert result.returncode == 0, result.stderr
        content = sr_path.read_text(encoding="utf-8")
        assert "status: rejected" in content
