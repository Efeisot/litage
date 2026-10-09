"""Display backlight + mode listing (xrandr read-only, brightness writable)."""
from __future__ import annotations

import subprocess

from .. import utils
from ..capabilities import Capability


def get(cap: Capability) -> dict:
    out: dict = {"backlights": {}}
    for bl in cap.backlights:
        out["backlights"][bl] = {
            "brightness": utils.read_str(f"/sys/class/backlight/{bl}/brightness"),
            "max": utils.read_str(f"/sys/class/backlight/{bl}/max_brightness"),
            "actual": utils.read_str(f"/sys/class/backlight/{bl}/actual_brightness"),
        }
    out["modes"] = _xrandr_modes()
    return out


def _xrandr_modes() -> list[str]:
    try:
        p = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return []
    if p.returncode != 0:
        return []
    modes = []
    current = ""
    for line in p.stdout.splitlines():
        if " connected " in line:
            current = line.split()[0]
        elif line.strip().startswith(("1920", "2560", "2880", "3840", "1366", "1600")) and current:
            modes.append(f"{current}: {line.strip()}")
    return modes[:20]


def set_brightness(name: str, value: str) -> tuple[bool, str]:
    try:
        iv = int(value)
    except ValueError:
        # percent support: "50%"
        if value.endswith("%"):
            try:
                pct = float(value[:-1])
            except ValueError:
                return False, "brightness needs integer or percent like 50%"
            mx = utils.read_int(f"/sys/class/backlight/{name}/max_brightness")
            if not mx:
                return False, "cannot read max_brightness"
            iv = int(mx * pct / 100)
        else:
            return False, "brightness needs integer or percent like 50%"
    return utils.write_str(f"/sys/class/backlight/{name}/brightness", str(iv))
