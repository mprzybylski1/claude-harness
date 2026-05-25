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


def _set_harness_yaml(enabled: bool) -> bool:
    """Return True if harness.yaml was updated, False if key not found."""
    harness_yaml = ROOT / "harness.yaml"
    if not harness_yaml.exists():
        return False
    text = harness_yaml.read_text(encoding="utf-8")
    import re
    new_val = "true" if enabled else "false"
    # Match both active and commented-out forms:
    #   workflow_telemetry: false
    #   # workflow_telemetry: true
    updated, count = re.subn(
        r"^#?\s*(workflow_telemetry\s*:\s*).*$",
        rf"\g<1>{new_val}",
        text,
        flags=re.MULTILINE,
    )
    if count:
        harness_yaml.write_text(updated, encoding="utf-8")
        return True
    return False


def _enable() -> None:
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL.touch()
    yaml_ok = _set_harness_yaml(True)
    if yaml_ok:
        print("Telemetry ON — sentinel created, harness.yaml updated.")
    else:
        print("Telemetry ON — sentinel created. WARNING: workflow_telemetry key not found in harness.yaml — add it manually.", file=sys.stderr)
        sys.exit(1)


def _disable() -> None:
    if SENTINEL.exists():
        SENTINEL.unlink()
    yaml_ok = _set_harness_yaml(False)
    if yaml_ok:
        print("Telemetry OFF — sentinel removed, harness.yaml updated.")
    else:
        print("Telemetry OFF — sentinel removed. WARNING: workflow_telemetry key not found in harness.yaml — add it manually.", file=sys.stderr)
        sys.exit(1)


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
