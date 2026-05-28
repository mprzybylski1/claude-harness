"""T124 / SR-004: large data files excluded from prepare_opus_context diff body.

The bug: S9 added sowpods.txt (267,751 lines) and its diff block consumed the
entire 600-line MAX_DIFF_LINES cap, leaving every modified .swift/.py file
truncated. Implementation-review was effectively bypassed.

The fix: files matching _LARGE_ASSET_EXTS whose diff block exceeds
_LARGE_ASSET_LINE_THRESHOLD are excluded from the displayed diff body and
listed separately, regardless of whether the overall cap is hit.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "tools"))

from prepare_opus_context import (  # noqa: E402
    _LARGE_ASSET_LINE_THRESHOLD,
    _apply_diff_cap,
    _is_large_asset,
)


def _make_block(path: str, body_lines: int) -> str:
    """Build a minimal unified-diff block of approximately body_lines content lines."""
    body = "+x\n" * body_lines
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{body_lines} @@\n"
        f"{body}"
    )


class TestIsLargeAsset:

    def test_large_txt_is_large_asset(self):
        block = _make_block("data/words.txt", _LARGE_ASSET_LINE_THRESHOLD + 1)
        assert _is_large_asset("data/words.txt", block) is True

    def test_small_txt_is_not_large_asset(self):
        block = _make_block("data/words.txt", 10)
        assert _is_large_asset("data/words.txt", block) is False

    def test_large_python_is_not_large_asset(self):
        """Source-code extensions never count as large assets even if huge."""
        block = _make_block("src/big.py", _LARGE_ASSET_LINE_THRESHOLD * 10)
        assert _is_large_asset("src/big.py", block) is False

    def test_large_swift_is_not_large_asset(self):
        block = _make_block("src/big.swift", _LARGE_ASSET_LINE_THRESHOLD * 10)
        assert _is_large_asset("src/big.swift", block) is False

    def test_lock_file_recognized(self):
        block = _make_block("pnpm-lock.yaml", _LARGE_ASSET_LINE_THRESHOLD + 50)
        assert _is_large_asset("pnpm-lock.yaml", block) is True


class TestApplyDiffCapLargeAssets:

    def test_under_cap_large_asset_stripped_from_body(self):
        """Under-cap path: large asset block is removed from displayed diff body,
        listed in large_asset_paths."""
        code = _make_block("src/app.py", 50)
        wordlist = _make_block(
            "data/sowpods.txt", _LARGE_ASSET_LINE_THRESHOLD + 100
        )
        diff = code + wordlist
        display, was_truncated, cut, large = _apply_diff_cap(diff, cap=600)

        assert was_truncated is False
        assert cut == []
        assert large == ["data/sowpods.txt"]
        # Code diff block survives in display
        assert "src/app.py" in display
        # Wordlist content does not appear in display body
        assert "data/sowpods.txt" not in display

    def test_under_cap_no_large_assets_unchanged(self):
        """Regression: under-cap diff with no large assets returns the original diff."""
        diff = _make_block("src/a.py", 20) + _make_block("src/b.py", 30)
        display, was_truncated, cut, large = _apply_diff_cap(diff, cap=600)
        assert was_truncated is False
        assert cut == []
        assert large == []
        assert display == diff

    def test_large_asset_does_not_push_signal_over_cap(self):
        """The 267k-line wordlist scenario: code fits cleanly because the wordlist
        was bucketed as a large asset and excluded from signal counting."""
        wordlist = _make_block("data/sowpods.txt", 267_000)
        code_blocks = [_make_block(f"src/file{i}.py", 30) for i in range(5)]
        diff = wordlist + "".join(code_blocks)
        display, was_truncated, cut, large = _apply_diff_cap(diff, cap=600)

        assert was_truncated is False, (
            "code (5 × 30 = 150 lines) should fit cleanly once the wordlist "
            "is excluded from signal"
        )
        assert cut == []
        assert large == ["data/sowpods.txt"]
        for i in range(5):
            assert f"src/file{i}.py" in display, f"src/file{i}.py missing from display"
        assert "data/sowpods.txt" not in display

    def test_small_yaml_not_excluded(self):
        """A normal workspace.yaml edit (50 lines) must NOT be flagged as large."""
        diff = (
            _make_block("workspaces/myws/workspace.yaml", 50)
            + _make_block("src/a.py", 30)
        )
        display, was_truncated, cut, large = _apply_diff_cap(diff, cap=600)
        assert large == []
        assert was_truncated is False
        assert display == diff

    def test_over_cap_large_asset_still_excluded(self):
        """When code alone overflows the cap, the large asset is still excluded
        (not partial-sliced)."""
        wordlist = _make_block("data/sowpods.txt", 5000)
        big_code = _make_block("scripts/tools/big.py", 800)
        diff = wordlist + big_code
        display, was_truncated, cut, large = _apply_diff_cap(diff, cap=600)
        assert large == ["data/sowpods.txt"]
        assert was_truncated is True
        # Wordlist body not in display
        assert "data/sowpods.txt" not in display
        # Code is partial-sliced (first-overflow rule) so its path header is present
        assert "scripts/tools/big.py" in display

    def test_empty_diff_returns_four_tuple(self):
        """Empty input still returns the new 4-tuple shape."""
        result = _apply_diff_cap("", cap=600)
        assert result == ("", False, [], [])
