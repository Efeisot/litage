"""cpufreq backend: governor / EPP / boost / freq (amd-pstate-epp + intel paths)."""
from __future__ import annotations

import glob

from .. import utils

POL = "/sys/devices/system/cpu/cpufreq/policy0"
ALL_POLS = sorted(glob.glob("/sys/devices/system/cpu/cpufreq/policy*"))


def get() -> dict:
    freqs = []
    for p in ALL_POLS:
        cur = utils.read_str(f"{p}/scaling_cur_freq")
        if cur:
            try:
                freqs.append(int(cur) // 1000)
            except ValueError:
                pass
    return {
        "driver": utils.read_str(f"{POL}/scaling_driver"),
        "governor": utils.read_str(f"{POL}/scaling_governor"),
        "governors": (utils.read_str(f"{POL}/scaling_available_governors") or "").split(),
        "epp": utils.read_str(f"{POL}/energy_performance_preference"),
        "epp_available": (
            utils.read_str(f"{POL}/energy_performance_available_preferences") or ""
        ).split(),
        "boost": utils.read_str("/sys/devices/system/cpu/cpufreq/boost"),
        "cpu_mhz_avg": (sum(freqs) // len(freqs)) if freqs else None,
    }


def set_governor(value: str) -> tuple[bool, str]:
    oks, errs = 0, []
    for p in ALL_POLS or [POL]:
        ok, msg = utils.write_str(f"{p}/scaling_governor", value)
        oks += ok
        if not ok:
            errs.append(msg)
    return (True, f"ok ({oks} policies)") if oks else (False, "; ".join(errs))


def set_epp(value: str) -> tuple[bool, str]:
    oks, errs = 0, []
    for p in ALL_POLS or [POL]:
        ok, msg = utils.write_str(f"{p}/energy_performance_preference", value)
        oks += ok
        if not ok:
            errs.append(msg)
    return (True, f"ok ({oks} policies)") if oks else (False, "; ".join(errs))


def set_boost(value: str) -> tuple[bool, str]:
    v = {"on": "1", "off": "0"}.get(value.lower(), value)
    if v not in ("0", "1"):
        return False, "boost needs on/off"
    return utils.write_str("/sys/devices/system/cpu/cpufreq/boost", v)
