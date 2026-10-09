"""ThinkPad backend — thinkpad_acpi varsa (fan, LED, inhibit)."""
from __future__ import annotations

import os

from .. import utils

BASE = "/sys/devices/platform/thinkpad_acpi"


def exists() -> bool:
    return os.path.isdir(BASE)


def get() -> dict:
    if not exists():
        return {"present": False}
    out: dict = {"present": True}
    for node in ("fan1_input", "fan2_input", "fan1_output",
                 "bluetooth_enable", "wwan_enable", "hotkey_mask",
                 "light", "panel", "volume", "mute"):
        for root in (BASE, f"{BASE}/hwmon/hwmon0" if os.path.isdir(f"{BASE}/hwmon/hwmon0") else BASE):
            p = os.path.join(root, node)
            if os.path.exists(p):
                out[node] = utils.read_str(p)
                break
    return out
