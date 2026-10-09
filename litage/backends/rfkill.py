"""rfkill backend: wifi / bluetooth soft block (airplane mode = both)."""
from __future__ import annotations

import glob
import subprocess

from .. import utils


def get() -> dict:
    out: dict = {"devices": []}
    for rf in sorted(glob.glob("/sys/class/rfkill/rfkill*")):
        out["devices"].append(
            {
                "name": utils.read_str(f"{rf}/name"),
                "type": utils.read_str(f"{rf}/type"),
                "soft": utils.read_str(f"{rf}/soft"),
                "hard": utils.read_str(f"{rf}/hard"),
            }
        )
    return out


def _run(*args: str) -> tuple[bool, str]:
    try:
        p = subprocess.run(["rfkill", *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return (True, "ok") if p.returncode == 0 else (False, p.stderr.strip() or p.stdout.strip())


def set_block(kind: str, block: bool) -> tuple[bool, str]:
    action = "block" if block else "unblock"
    if kind in ("wifi", "wlan", "bluetooth", "bt"):
        return _run(action, kind if kind in ("wifi", "bluetooth") else kind)
    if kind in ("all", "airplane"):
        if block:
            o1, m1 = _run("block", "wifi")
            o2, m2 = _run("block", "bluetooth")
            return (o1 and o2, f"wifi:{m1} bt:{m2}")
        o1, m1 = _run("unblock", "wifi")
        o2, m2 = _run("unblock", "bluetooth")
        return (o1 and o2, f"wifi:{m1} bt:{m2}")
    return False, f"unknown rfkill kind {kind!r} (wifi/bluetooth/all)"
