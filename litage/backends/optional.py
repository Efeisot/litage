"""Optional backends: Legion module + NVIDIA dGPU.

Both are capability-gated. On Yoga 14AKP10 (no legion module, no NVIDIA)
detect() is False and GUI hides these pages entirely.
"""
from __future__ import annotations

import glob
import os
import subprocess

from .. import utils
from ..capabilities import Capability


def legion_get(cap: Capability) -> dict:
    if not cap.has_legion_module:
        return {"present": False}
    base = cap.legion_path
    out: dict = {"present": True, "path": base}
    if not base or not os.path.isdir(base):
        return out
    for node in utils.list_dir(base):
        if node.startswith(("power", "fan", "cpu_", "gpu_", "battery", "fn_", "rapid")):
            out[node] = utils.read_str(f"{base}/{node}")
    return out


def nvidia_get(cap: Capability) -> dict:
    if not cap.has_nvidia:
        return {"present": False}
    out: dict = {"present": True}
    try:
        p = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if p.returncode == 0:
            out["smi"] = p.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    # /proc presence
    out["proc_gpus"] = sorted(glob.glob("/proc/driver/nvidia/gpus/*"))
    return out
