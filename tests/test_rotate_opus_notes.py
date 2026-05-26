"""tests/test_rotate_opus_notes.py

Tests for T050: rotate_opus_notes.py decade-bucketing and multi-section rotation.
Also verifies expand_carry_forward.py finds findings across multiple archive files.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))


def _make_review(session_n: int, finding: str = "finding text") -> str:
    return (
        f"# Opus Review — S{session_n}\n\n"
        f"## Invariant Violations\nNone\n\n"
        f"## Architectural Concerns\n1. {finding}\n\n"
        f"## Suggested Next Session Focus\nFix it.\n\n"
    )


class TestRotateOpusNotes:
    """rotate_opus_notes.py archives to per-decade bucket files."""

    def _notes_with(self, *session_ns: int) -> str:
        header = "<!-- header -->\n\n"
        return header + "\n".join(_make_review(n) for n in session_ns)

    def test_single_section_no_rotation(self, tmp_path):
        """One section in opus_notes.md — nothing should be rotated."""
        from rotate_opus_notes import rotate
        notes = tmp_path / "opus_notes.md"
        notes.write_text(_make_review(5), encoding="utf-8")
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        rotate(notes=notes, archive_dir=archive_dir)

        assert list(archive_dir.iterdir()) == [], "No archive file should be created"
        assert notes.read_text(encoding="utf-8") == _make_review(5)

    def test_two_sections_oldest_archived(self, tmp_path):
        """Two sections: oldest (S5) is archived, newest (S9) stays in opus_notes.md."""
        from rotate_opus_notes import rotate
        notes = tmp_path / "opus_notes.md"
        notes.write_text(self._notes_with(5, 9), encoding="utf-8")
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        rotate(notes=notes, archive_dir=archive_dir)

        archive_file = archive_dir / "opus_notes_S0-S9.md"
        assert archive_file.exists(), "S0-S9 archive file should be created"
        archived = archive_file.read_text(encoding="utf-8")
        assert "# Opus Review — S5" in archived
        assert "# Opus Review — S9" not in archived

        remaining = notes.read_text(encoding="utf-8")
        assert "# Opus Review — S9" in remaining
        assert "# Opus Review — S5" not in remaining

    def test_decade_routing_s13_goes_to_s10_s19(self, tmp_path):
        """S13 review routes to opus_notes_S10-S19.md, not S0-S9."""
        from rotate_opus_notes import rotate
        notes = tmp_path / "opus_notes.md"
        notes.write_text(self._notes_with(13, 14), encoding="utf-8")
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        rotate(notes=notes, archive_dir=archive_dir)

        assert (archive_dir / "opus_notes_S10-S19.md").exists()
        assert not (archive_dir / "opus_notes_S0-S9.md").exists()
        archived = (archive_dir / "opus_notes_S10-S19.md").read_text(encoding="utf-8")
        assert "# Opus Review — S13" in archived

    def test_cross_decade_routing(self, tmp_path):
        """S9 routes to S0-S9 bucket and S10 routes to S10-S19 bucket."""
        from rotate_opus_notes import rotate
        notes = tmp_path / "opus_notes.md"
        notes.write_text(self._notes_with(9, 10, 11), encoding="utf-8")
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        rotate(notes=notes, archive_dir=archive_dir)

        assert (archive_dir / "opus_notes_S0-S9.md").exists()
        assert (archive_dir / "opus_notes_S10-S19.md").exists()
        assert "S9" in (archive_dir / "opus_notes_S0-S9.md").read_text()
        assert "S10" in (archive_dir / "opus_notes_S10-S19.md").read_text()
        remaining = notes.read_text()
        assert "# Opus Review — S11" in remaining
        assert "# Opus Review — S9" not in remaining
        assert "# Opus Review — S10" not in remaining

    def test_appends_to_existing_archive_file(self, tmp_path):
        """A second rotation appends to an existing archive file, not overwrites it."""
        from rotate_opus_notes import rotate
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        # First rotation: archive S1
        notes = tmp_path / "opus_notes.md"
        notes.write_text(self._notes_with(1, 2), encoding="utf-8")
        rotate(notes=notes, archive_dir=archive_dir)

        # Second rotation: archive S2
        notes.write_text(
            notes.read_text() + "\n\n" + _make_review(3),
            encoding="utf-8",
        )
        rotate(notes=notes, archive_dir=archive_dir)

        archive_file = archive_dir / "opus_notes_S0-S9.md"
        content = archive_file.read_text(encoding="utf-8")
        assert "# Opus Review — S1" in content
        assert "# Opus Review — S2" in content

    def test_leaves_exactly_one_section(self, tmp_path):
        """After rotating N sections, exactly 1 remains in opus_notes.md."""
        from rotate_opus_notes import rotate
        notes = tmp_path / "opus_notes.md"
        notes.write_text(self._notes_with(1, 2, 3, 4), encoding="utf-8")
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        rotate(notes=notes, archive_dir=archive_dir)

        remaining = notes.read_text(encoding="utf-8")
        count = remaining.count("# Opus Review — S")
        assert count == 1, f"Expected 1 section, found {count}"


class TestExpandCarryForwardMultiFile:
    """expand_carry_forward.py glob covers multiple decade archive files (T046/T050)."""

    def test_glob_covers_multiple_decade_files(self, tmp_path):
        """opus_notes*.md glob in expand_carry_forward catches both decade buckets."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        (archive_dir / "opus_notes_S0-S9.md").write_text("old s0-s9", encoding="utf-8")
        (archive_dir / "opus_notes_S10-S19.md").write_text("newer s10-s19", encoding="utf-8")

        matched = sorted(archive_dir.glob("opus_notes*.md"))
        names = [p.name for p in matched]
        assert "opus_notes_S0-S9.md" in names
        assert "opus_notes_S10-S19.md" in names

    def test_opus_files_collects_all_decade_archives(self, tmp_path, monkeypatch):
        """_opus_files() returns entries from both opus_notes.md and all decade archive files."""
        import expand_carry_forward as ecf

        # Patch ROOT so _opus_files() looks at tmp_path instead of harness root
        monkeypatch.setattr(ecf, "ROOT", tmp_path)

        docs = tmp_path / "docs"
        docs.mkdir()
        archive_dir = docs / "archive"
        archive_dir.mkdir()

        # Put a finding in the S0-S9 archive
        (archive_dir / "opus_notes_S0-S9.md").write_text(
            "# Opus Review Notes — Archive\n\n"
            + _make_review(5, "old cross-file finding"),
            encoding="utf-8",
        )
        # Current opus_notes with a newer review
        (docs / "opus_notes.md").write_text(
            _make_review(15, "current finding"),
            encoding="utf-8",
        )

        files = ecf._opus_files()
        all_text = "\n".join(p.read_text(encoding="utf-8") for p in files)
        assert "old cross-file finding" in all_text, \
            "expand_carry_forward must search all archive decade files"
        assert "current finding" in all_text
