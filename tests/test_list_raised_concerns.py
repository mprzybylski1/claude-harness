"""Tests for T105: list_raised_concerns.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "list_raised_concerns.py"

_SR_TEMPLATE = """\
---
id: {sr_id}
from: {slug}
raised: S5 2026-05-27
title: {title}
severity: {severity}
status: {status}
harness_ticket: {harness_ticket}
---

## Context

Some context.
"""


def _make_sr(raised_dir: Path, sr_id: str, slug: str, title: str,
             severity: str = "medium", status: str = "raised",
             harness_ticket: str = "") -> Path:
    raised_dir.mkdir(parents=True, exist_ok=True)
    (raised_dir / "archive").mkdir(exist_ok=True)
    dest = raised_dir / f"{sr_id}-{title.lower().replace(' ', '-')[:30]}.md"
    dest.write_text(_SR_TEMPLATE.format(
        sr_id=sr_id, slug=slug, title=title,
        severity=severity, status=status, harness_ticket=harness_ticket,
    ), encoding="utf-8")
    return dest


def _setup(tmp_path: Path) -> Path:
    """Minimal harness skeleton. Returns harness root."""
    (tmp_path / "workspaces").mkdir()
    return tmp_path


def _run(harness: Path) -> subprocess.CompletedProcess:
    import os as _os
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True, text=True,
        env={**_os.environ, "HARNESS_ROOT": str(harness), "PYTHONPATH": str(ROOT)},
    )


class TestListRaisedConcerns:

    def test_no_concerns_produces_no_output(self, tmp_path):
        """When no raised/promoted items exist, exits 0 with empty stdout."""
        harness = _setup(tmp_path)
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == ""

    def test_single_raised_concern_shown(self, tmp_path):
        """A single raised SR appears in the output."""
        harness = _setup(tmp_path)
        _make_sr(harness / "workspaces" / "myws" / "raised",
                 "SR-001", "myws", "Fix the timeout", severity="high")
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        assert "SR-001" in result.stdout
        assert "Fix the timeout" in result.stdout
        assert "myws" in result.stdout

    def test_promoted_item_shown(self, tmp_path):
        """Promoted (not yet resolved) SR also appears."""
        harness = _setup(tmp_path)
        _make_sr(harness / "workspaces" / "myws" / "raised",
                 "SR-002", "myws", "Promoted concern", status="promoted",
                 harness_ticket="T999")
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        assert "SR-002" in result.stdout

    def test_excludes_resolved_items(self, tmp_path):
        """Resolved SRs are not shown."""
        harness = _setup(tmp_path)
        _make_sr(harness / "workspaces" / "myws" / "raised",
                 "SR-001", "myws", "Already done", status="resolved")
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == ""

    def test_excludes_rejected_items(self, tmp_path):
        """Rejected SRs are not shown."""
        harness = _setup(tmp_path)
        _make_sr(harness / "workspaces" / "myws" / "raised",
                 "SR-001", "myws", "Rejected thing", status="rejected")
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == ""

    def test_excludes_archive_subdirectory(self, tmp_path):
        """Files inside raised/archive/ are not scanned."""
        harness = _setup(tmp_path)
        raised = harness / "workspaces" / "myws" / "raised"
        raised.mkdir(parents=True)
        archive = raised / "archive"
        archive.mkdir()
        (archive / "SR-001-old.md").write_text(
            "---\nid: SR-001\nstatus: raised\ntitle: Archived concern\n"
            "severity: high\nfrom: myws\nraised: S1 2026-01-01\nharness_ticket:\n---\n",
            encoding="utf-8",
        )
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == ""

    def test_groups_by_workspace(self, tmp_path):
        """Output groups concerns under their workspace slug."""
        harness = _setup(tmp_path)
        _make_sr(harness / "workspaces" / "ws-a" / "raised",
                 "SR-001", "ws-a", "Alpha concern")
        _make_sr(harness / "workspaces" / "ws-b" / "raised",
                 "SR-001", "ws-b", "Beta concern")
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "ws-a" in out
        assert "ws-b" in out
        assert "Alpha concern" in out
        assert "Beta concern" in out

    def test_severity_order_within_workspace(self, tmp_path):
        """Within a workspace, higher severity items appear before lower ones."""
        harness = _setup(tmp_path)
        raised = harness / "workspaces" / "myws" / "raised"
        _make_sr(raised, "SR-001", "myws", "Low thing", severity="low")
        _make_sr(raised, "SR-002", "myws", "Critical thing", severity="critical")
        _make_sr(raised, "SR-003", "myws", "High thing", severity="high")
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert out.index("Critical thing") < out.index("High thing") < out.index("Low thing")

    def test_triage_instructions_shown_when_concerns_exist(self, tmp_path):
        """Output includes promote/reject command hints when concerns are present."""
        harness = _setup(tmp_path)
        _make_sr(harness / "workspaces" / "myws" / "raised",
                 "SR-001", "myws", "Some issue")
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        assert "promote" in result.stdout.lower() or "promote_raised_concern" in result.stdout
        assert "reject" in result.stdout.lower() or "reject_raised_concern" in result.stdout

    def test_no_triage_instructions_when_empty(self, tmp_path):
        """No triage instructions printed when there are no pending concerns."""
        harness = _setup(tmp_path)
        result = _run(harness)
        assert result.returncode == 0, result.stderr
        assert "promote" not in result.stdout.lower()
