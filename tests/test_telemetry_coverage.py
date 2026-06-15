"""
Tests for T156: telemetry_coverage.py — compares telemetry record count vs native
transcript tool_use count for a session (the under-counting smoke check).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tools" / "telemetry_coverage.py"


def _transcript(path: Path, tool_uses: int) -> None:
    lines = []
    for i in range(tool_uses):
        lines.append(json.dumps({
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Bash", "id": f"t{i}"}
            ]}
        }))
    # a non-tool_use line that must be ignored
    lines.append(json.dumps({"message": {"role": "user", "content": "hi"}}))
    path.write_text("\n".join(lines) + "\n")


def _log(path: Path, uuid: str, count: int, other_uuid_count: int = 0) -> None:
    lines = []
    for _ in range(count):
        lines.append(json.dumps({"tool": "Bash", "claude_session_uuid": uuid}))
    for _ in range(other_uuid_count):
        lines.append(json.dumps({"tool": "Bash", "claude_session_uuid": "other"}))
    path.write_text("\n".join(lines) + "\n")


def _run(transcript: Path, log: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--transcript", str(transcript), "--log", str(log), *extra],
        capture_output=True, text=True,
    )


def test_full_coverage(tmp_path):
    t = tmp_path / "abc.jsonl"
    log = tmp_path / "log.jsonl"
    _transcript(t, 10)
    _log(log, "abc", 10, other_uuid_count=5)  # other-uuid records must not count
    result = _run(t, log)
    assert result.returncode == 0, result.stderr
    assert "native tool_use calls : 10" in result.stdout
    assert "telemetry records     : 10" in result.stdout
    assert "coverage              : 100%" in result.stdout


def test_under_coverage_flags_with_threshold(tmp_path):
    t = tmp_path / "abc.jsonl"
    log = tmp_path / "log.jsonl"
    _transcript(t, 100)
    _log(log, "abc", 21)  # the historical under-count shape
    result = _run(t, log, "--min-coverage", "0.8")
    assert result.returncode == 1
    assert "21%" in result.stdout
    assert "below threshold" in result.stderr.lower()


def test_telemetry_exceeds_native_notes_conflation(tmp_path):
    t = tmp_path / "abc.jsonl"
    log = tmp_path / "log.jsonl"
    _transcript(t, 180)
    _log(log, "abc", 196)  # this session: ghost-S30 conflation made telemetry higher
    result = _run(t, log)
    assert result.returncode == 0
    assert "conflation" in result.stdout.lower()


def test_no_transcript_is_advisory(tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text("")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--transcript", str(tmp_path / "nope.jsonl"),
         "--log", str(log)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "no transcript" in result.stderr.lower()


def test_empty_transcript_does_not_report_false_coverage(tmp_path):
    """A transcript with 0 tool_use must NOT report 100% / pass --min-coverage (fail-open)."""
    t = tmp_path / "abc.jsonl"
    log = tmp_path / "log.jsonl"
    t.write_text(json.dumps({"message": {"role": "user", "content": "hi"}}) + "\n")  # no tool_use
    _log(log, "abc", 0)
    # Without a threshold: must not claim 100%.
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--transcript", str(t), "--log", str(log)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "100%" not in result.stdout
    assert "N/A" in result.stdout or "no tool_use" in result.stdout.lower()
    # With a threshold: unverifiable coverage must FAIL closed, not pass.
    result2 = subprocess.run(
        [sys.executable, str(SCRIPT), "--transcript", str(t), "--log", str(log),
         "--min-coverage", "0.8"],
        capture_output=True, text=True,
    )
    assert result2.returncode == 1, "empty transcript must fail the --min-coverage gate"
