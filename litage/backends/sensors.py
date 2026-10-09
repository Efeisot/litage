"""Sensors backend: hwmon + `sensors` output (read-only)."""
from __future__ import annotations

import glob
import subprocess

from .. import utils


def get() -> dict:
    out: dict = {"hwmon": {}, "sensors_text": ""}
    for hw in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name = utils.read_str(f"{hw}/name") or "?"
        vals: dict = {}
        for node in ("temp1_input", "temp2_input", "temp3_input", "fan1_input",
                     "fan2_input", "power1_average", "in0_input"):
            v = utils.read_str(f"{hw}/{node}")
            if v is not None:
                vals[node] = v
        out["hwmon"][f"{hw.split('/')[-1]}:{name}"] = vals
    try:
        p = subprocess.run(["sensors"], capture_output=True, text=True, timeout=5)
        if p.returncode == 0:
            out["sensors_text"] = p.stdout[:4000]
    except (OSError, subprocess.SubprocessError):
        pass
    return out
