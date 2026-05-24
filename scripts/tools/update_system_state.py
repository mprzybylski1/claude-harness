#!/usr/bin/env python3
"""
scripts/tools/update_system_state.py
Generate docs/system_state.md — a structured user-facing snapshot of current system state.

Sources (all deterministic, no LLM):
  - docs/sessions.md       — phase & gate status (Current Phase & Status section)
  - docs/tickets/INDEX.md  — open ticket summary
  - config.yaml            — broker, data source, risk limits

Run at session close; output committed alongside sessions.md.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_config as _hc
_HARNESS = _hc.load()


def _extract_phase_status(sessions_md: str) -> str:
    """Extract the Current Phase & Status block from sessions.md."""
    match = re.search(
        r"## Current Phase & Status\n(.*?)\n---",
        sessions_md,
        re.DOTALL,
    )
    if not match:
        return "_(could not extract — check docs/sessions.md)_"

    text = match.group(1).strip()
    # Drop the housekeeping annotation line
    text = re.sub(r"\*\(Rewritten each session[^\n]*\)\*\n+", "", text)
    # Drop the "Open tickets: see..." trailing line
    text = re.sub(r"\*\*Open tickets:\*\*[^\n]*\n?", "", text)
    return text.strip()


def _extract_session_id(sessions_md: str) -> str:
    """Read session ID from the Active Work header line."""
    m = re.search(r"\*\*S(\d+) —", sessions_md)
    return f"S{m.group(1)}" if m else "unknown"


def _extract_open_tickets(index_md: str) -> str:
    """Return a markdown table of open tickets from INDEX.md."""
    total_m = re.search(r"(\d+) open tickets", index_md)
    total = int(total_m.group(1)) if total_m else 0

    if total == 0:
        return "_No open tickets._"

    rows = [line for line in index_md.splitlines() if line.startswith("| T")]
    if not rows:
        return "_No open tickets._"

    return (
        f"**{total} open ticket{'s' if total != 1 else ''}**\n\n"
        "| ID | Title | Phase | Age |\n"
        "|----|-------|-------|-----|\n"
        + "\n".join(rows)
    )


def _build_config_sections(cfg: dict) -> str:
    """Build Deployment, Configuration, and Key Paths sections from config.yaml contents."""
    trading_mode     = cfg.get("trading_mode", "?")
    capital          = cfg.get("starting_capital", 0)
    data_source      = cfg.get("data_source", "yfinance")
    broker_cfg       = cfg.get("broker", {})
    broker_type      = broker_cfg.get("type", "paper")
    slippage_bps     = broker_cfg.get("paper", {}).get("slippage_bps", 5.0)
    ibkr_broker_cfg  = broker_cfg.get("ibkr", {})
    ibkr_host        = ibkr_broker_cfg.get("host", "127.0.0.1")
    ibkr_port        = ibkr_broker_cfg.get("port", 4002)
    db_path          = cfg.get("db_path", "audit.db")
    max_drawdown_pct = cfg.get("max_drawdown_pct", 0) * 100
    max_daily_loss   = cfg.get("max_daily_loss_pct", 0) * 100
    max_position     = cfg.get("max_position_pct", 0) * 100

    _BROKER_LABELS = {"paper": "PaperTrader", "ig_spreadbet": "IGBroker", "ibkr": "IBKRBroker"}
    broker_label = _BROKER_LABELS.get(broker_type, broker_type)
    data_label   = (
        "IBKRDataClient" if data_source == "ibkr"
        else "MarketDataClient (yfinance)"
    )

    return f"""\
## Deployment

| Host | Role | Status |
|------|------|--------|
| Linux laptop (HP OMEN) | Phase 4 active / Phase 5 live (planned) | Cron 9:31 AM ET Mon–Fri — IB Gateway `{ibkr_host}:{ibkr_port}` |

**Broker:** `{broker_label}` (`broker.type: "{broker_type}"`)
**Data source:** `{data_label}` (`data_source: "{data_source}"`)
**Trading mode:** `{trading_mode}`

---

## Configuration

| Setting | Value |
|---------|-------|
| Starting capital | ${capital:,.0f} |
| Max position | {max_position:.0f}% per instrument |
| Max drawdown | {max_drawdown_pct:.0f}% → halt |
| Max daily loss | {max_daily_loss:.0f}% → circuit breaker |
| Slippage model | {slippage_bps:.0f} bps |
| Audit DB | `{db_path}` |

---

## Key Paths

| Item | Path |
|------|------|
| Pi app root | `/home/pi/trading_app/ai-trading-company/` |
| Pi log | `logs/trading_cycle.log` |
| Pi audit DB | `audit.db` |
| Laptop audit DB | `audit.db` (project root) |
| Strategy specs | `strategies/specs/` |
| IB Gateway (paper) | `{ibkr_host}:{ibkr_port}` |
| IB Gateway (live) | `{ibkr_host}:4001` |
| Config | `config.yaml` |

---
"""


def main() -> None:
    sessions_path = ROOT / "docs" / "sessions.md"
    index_path    = ROOT / "docs" / "tickets" / "INDEX.md"
    config_path   = ROOT / "config.yaml"
    output_path   = ROOT / "docs" / "system_state.md"

    sessions_md = sessions_path.read_text()
    index_md    = index_path.read_text()

    session_id   = _extract_session_id(sessions_md)
    phase_status = _extract_phase_status(sessions_md)
    tickets_text = _extract_open_tickets(index_md)
    today        = date.today().isoformat()

    if config_path.exists():
        cfg = yaml.safe_load(config_path.read_text())
        config_sections = _build_config_sections(cfg)
    else:
        config_sections = (
            "## Deployment\n\n"
            "_config.yaml not present — deployment details unavailable._\n\n---\n"
        )

    content = f"""\
# System State

_Last updated: {session_id} {today}_

---

{config_sections}
## Phase & Gate Status

{phase_status}

---

## Open Tickets

{tickets_text}

---

_Generated by `scripts/tools/update_system_state.py` — do not edit by hand._
_Re-runs automatically at session close; overwrites this file._
"""

    output_path.write_text(content)
    print(f"Written {output_path.relative_to(ROOT)} ({session_id} {today})")


if __name__ == "__main__":
    main()
