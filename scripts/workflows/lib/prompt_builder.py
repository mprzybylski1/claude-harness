from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import harness_config as _hc

from .git_ops import _get_root

def build_prompt(ticket_id: str, root: Path | None = None) -> str:
    r = root or _get_root()

    # Locate ticket file
    ticket_dir = r / _hc.tickets_dir()
    matches = list(ticket_dir.glob(f"{ticket_id}-*.md"))
    if not matches:
        raise FileNotFoundError(
            f"No open ticket found for {ticket_id} in {ticket_dir}"
        )
    ticket_body = matches[0].read_text()

    # Read full invariants file — no line cap (Phase 5 + portfolio_component invariants
    # are in the latter half and are most relevant to active 4→5 tickets).
    invariants_path = r / "docs" / "architecture_invariants.md"
    if invariants_path.exists():
        invariants = invariants_path.read_text()
    else:
        invariants = "(architecture_invariants.md not found)"

    return f"""You are implementing a ticket for the Autonomous AI Trading Company project.

## CRITICAL RULES
1. Do NOT run git commit, git add, or any git command that modifies history.
2. Do NOT modify files in: scripts/workflows/, docs/architecture_invariants.md, config.yaml, infra/audit_log.py.
3. Run the test suite after implementing: python -m pytest tests/ -x -q
4. If this ticket touches core/, strategies/runtime.py, or execution/, write failing tests FIRST (TDD).
5. Stop as soon as the ticket's acceptance criteria are satisfied and tests pass.

## Architecture invariants
{invariants}

## Ticket to implement
{ticket_body}

## Instructions
Read the ticket above. Implement all acceptance criteria. Run tests to verify. Do NOT commit.
"""
