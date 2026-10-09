"""ideapad-laptop (VPC2004) backend: conservation/fan/fn_lock/camera/usb/kbd."""
from __future__ import annotations

import os

from .. import utils
from ..capabilities import Capability

FEATURES = {
    "conservation": ("conservation_mode", ("0", "1"), {"0": "off", "1": "on"}),
    "fan_mode": ("fan_mode", None, None),  # numeric, model-dependent
    "fn_lock": ("fn_lock", ("0", "1"), {"0": "off", "1": "on"}),
    "camera_power": ("camera_power", ("0", "1"), {"0": "off", "1": "on"}),
    "usb_charging": ("usb_charging", ("0", "1"), {"0": "off", "1": "on"}),
}


def _p(cap: Capability, node: str) -> str | None:
    if not cap.ideapad_path:
        return None
    return os.path.join(cap.ideapad_path, node)


def get_all(cap: Capability) -> dict:
    out: dict = {}
    if not cap.has_ideapad:
        return out
    for feat, (node, _, _) in FEATURES.items():
        out[feat] = utils.read_str(_p(cap, node) or "")
    out["kbd_backlight"] = utils.read_str("/sys/class/leds/platform::kbd_backlight/brightness")
    out["kbd_backlight_max"] = utils.read_str(
        "/sys/class/leds/platform::kbd_backlight/max_brightness"
    )
    out["fnlock_led"] = utils.read_str("/sys/class/leds/platform::fnlock/brightness")
    return out


def set_feature(cap: Capability, feature: str, value: str) -> tuple[bool, str]:
    if not cap.has_ideapad:
        return False, "ideapad-laptop device not present on this machine"
    # friendly on/off -> 1/0
    v = {"on": "1", "off": "0", "true": "1", "false": "0"}.get(value.lower(), value)
    if feature in FEATURES:
        node, allowed, _ = FEATURES[feature]
        if allowed and v not in allowed:
            return False, f"invalid value {value!r} for {feature}, use on/off"
        return utils.write_str(_p(cap, node) or "", v)
    if feature == "kbd_backlight":
        try:
            iv = int(v)
        except ValueError:
            return False, "kbd_backlight needs integer 0..max"
        if not 0 <= iv <= (cap.kbd_backlight_max or 2):
            return False, f"out of range 0..{cap.kbd_backlight_max}"
        return utils.write_str("/sys/class/leds/platform::kbd_backlight/brightness", str(iv))
    return False, f"unknown ideapad feature {feature!r}"
