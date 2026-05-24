from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .git_ops import _get_root

DEFAULT_TIMEOUT_S = 1800  # 30 minutes

_CREDIT_EXHAUSTION_PATTERNS = [
    "credit balance",
    "insufficient credits",
    "usage limit",
    "billing",
    "quota exceeded",
    "rate limit",
]


def _cli_path(cli_path: str | None) -> Path:
    if cli_path:
        return Path(cli_path)
    env = os.environ.get("CLAUDE_CLI_PATH")
    if env:
        return Path(env)
    return Path.home() / ".local" / "bin" / "claude"


def detect_credit_exhaustion(stderr: str) -> bool:
    low = stderr.lower()
    return any(p in low for p in _CREDIT_EXHAUSTION_PATTERNS)


def spawn(
    prompt: str,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    cli_path: str | None = None,
    root: Path | None = None,
) -> subprocess.Popen:
    """Spawn claude -p as a Popen so the watcher can call process.terminate()."""
    r = root or _get_root()
    cli = _cli_path(cli_path)
    return subprocess.Popen(
        [str(cli), "-p", prompt],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        cwd=r,
    )
