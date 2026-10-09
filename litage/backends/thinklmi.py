"""think-lmi backend (BIOS attributes). Reads need root on most machines."""
from __future__ import annotations

import os

from .. import utils
from ..capabilities import Capability


def get(cap: Capability) -> dict:
    out: dict = {}
    base = "/sys/class/firmware-attributes/thinklmi/attributes"
    for attr in cap.thinklmi_attrs:
        if attr == "pending_reboot":
            continue
        cur = utils.read_str(f"{base}/{attr}/current_value")
        poss = utils.read_str(f"{base}/{attr}/possible_values")
        out[attr] = {
            "current": cur if cur is not None else "(need root)",
            "possible": poss,
        }
    pending = utils.read_str(f"{base}/pending_reboot")
    if pending is not None:
        out["pending_reboot"] = pending
    return out
