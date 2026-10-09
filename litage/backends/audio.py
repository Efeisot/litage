"""Audio mute backend: tries wpctl, then amixer, then pactl (whatever exists)."""
from __future__ import annotations

import shutil
import subprocess


def _run(cmd: list[str]) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return (True, p.stdout.strip() or "ok") if p.returncode == 0 else (False, p.stderr.strip())


def get() -> dict:
    out: dict = {"tool": None}
    if shutil.which("wpctl"):
        out["tool"] = "wpctl"
        ok, msg = _run(["wpctl", "get-mute", "@DEFAULT_AUDIO_SINK@"])
        if ok:
            out["speaker_mute"] = msg
        ok2, msg2 = _run(["wpctl", "get-mute", "@DEFAULT_AUDIO_SOURCE@"])
        if ok2:
            out["mic_mute"] = msg2
    elif shutil.which("amixer"):
        out["tool"] = "amixer"
        ok, msg = _run(["amixer", "get", "Master"])
        if ok:
            out["master"] = "off" if "[off]" in msg else "on"
        ok2, msg2 = _run(["amixer", "get", "Capture"])
        if ok2:
            out["capture"] = "off" if "[off]" in msg2 else "on"
    return out


def set_mute(target: str, mute: bool) -> tuple[bool, str]:
    v = {"on": False, "off": True, "mute": True, "unmute": False}
    m = mute if isinstance(mute, bool) else v.get(str(mute).lower(), True)
    if shutil.which("wpctl"):
        node = "@DEFAULT_AUDIO_SINK@" if target in ("speaker", "sink") else "@DEFAULT_AUDIO_SOURCE@"
        return _run(["wpctl", "set-mute", node, "1" if m else "0"])
    if shutil.which("amixer"):
        ctl = "Master" if target in ("speaker", "sink") else "Capture"
        return _run(["amixer", "set", ctl, "mute" if m else "unmute"])
    return False, "no audio tool found (wpctl/amixer)"
