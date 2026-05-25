#!/usr/bin/env python3
"""
Enable or disable workflow telemetry.

Updates harness.yaml and creates/removes the .git/workflow_telemetry_on
sentinel file that log_tool_usage.py checks before any non-stdlib import.

Usage:
    python scripts/tools/toggle_telemetry.py on
    python scripts/tools/toggle_telemetry.py off
    python scripts/tools/toggle_telemetry.py status
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = ROOT / ".git" / "workflow_telemetry_on"


def _set_harness_yaml(enabled: bool) -> None:
    harness_yaml = ROOT / "harness.yaml"
    if not harness_yaml.exists():
        return
    text = harness_yaml.read_text(encoding="utf-8")
    import re
    new_val = "true" if enabled else "false"
    # Replace existing setting
    updated, count = re.subn(
        r"^(workflow_telemetry\s*:\s*).*$",
        rf"\g<1>{new_val}",
        text,
        flags=re.MULTILINE,
    )
    if count:
        harness_yaml.write_text(updated, encoding="utf-8")
    else:
        print(
            "WARNING: workflow_telemetry key not found in harness.yaml — add it manually.",
            file=sys.stderr,
        )


def _enable() -> None:
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL.touch()
    _set_harness_yaml(True)
    print("Telemetry ON — sentinel created, harness.yaml updated.")


def _disable() -> None:
    if SENTINEL.exists():
        SENTINEL.unlink()
    _set_harness_yaml(False)
    print("Telemetry OFF — sentinel removed, harness.yaml updated.")


def _status() -> None:
    sentinel_state = "present (ON)" if SENTINEL.exists() else "absent (OFF)"
    print(f"Sentinel file: {sentinel_state}")
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "tools"))
        import harness_config as _hc
        harness = _hc.load()
        yaml_state = harness.get("workflow_telemetry", False)
        print(f"harness.yaml workflow_telemetry: {yaml_state}")
    except Exception as exc:
        print(f"harness.yaml: could not read ({exc})")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off", "status"):
        print("Usage: toggle_telemetry.py on|off|status", file=sys.stderr)
        sys.exit(1)
    {"on": _enable, "off": _disable, "status": _status}[sys.argv[1]]()


if __name__ == "__main__":
    main()
