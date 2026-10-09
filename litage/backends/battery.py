"""Battery backend: sysfs + upower (read-only thresholds where kernel allows).

conservation_mode lives in ideapad backend; this module handles BAT0
status/capacity/charge_types and upower details.
"""
from __future__ import annotations

import subprocess

from .. import utils
from ..capabilities import Capability

BAT = "/sys/class/power_supply/BAT0"


def get(cap: Capability) -> dict:
    out: dict = {}
    if not cap.has_battery:
        return out
    for node in (
        "status",
        "capacity",
        "capacity_level",
        "cycle_count",
        "energy_full",
        "energy_full_design",
        "energy_now",
        "power_now",
        "voltage_now",
        "technology",
        "manufacturer",
        "model_name",
    ):
        out[node] = utils.read_str(f"{BAT}/{node}")
    ct = utils.read_str(f"{BAT}/charge_types")
    if ct:
        out["charge_types_raw"] = ct
        for tok in ct.split():
            if tok.startswith("[") and tok.endswith("]"):
                out["charge_type_active"] = tok.strip("[]")
    out["upower"] = _upower()
    return out


def _upower() -> dict:
    try:
        p = subprocess.run(
            ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    info: dict = {}
    if p.returncode != 0:
        return info
    for line in p.stdout.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip().replace(" ", "_")
            if k in ("percentage", "state", "capacity", "charge-cycles", "energy-rate"):
                info[k] = v.strip()
    return info
