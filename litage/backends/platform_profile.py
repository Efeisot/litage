"""platform_profile backend — handles ideapad-laptop + amd-pmf dual providers.

Live host has TWO class devices (platform-profile-0=ideapad-laptop,
platform-profile-1=amd-pmf) plus the legacy /sys/firmware/acpi/platform_profile.
Writing to the firmware path updates both; we do that first, then fall back
to per-device writes for partial failures.
"""
from __future__ import annotations

from .. import utils
from ..capabilities import Capability

FIRMWARE = "/sys/firmware/acpi/platform_profile"
FIRMWARE_CHOICES = "/sys/firmware/acpi/platform_profile_choices"
CLASS = "/sys/class/platform-profile"

VALID = ("low-power", "balanced", "performance", "balanced-performance", "custom")


def get(cap: Capability) -> dict:
    out: dict = {
        "active": utils.read_str(FIRMWARE),
        "choices": (utils.read_str(FIRMWARE_CHOICES) or "").split(),
        "providers": {},
    }
    for name in cap.platform_profiles:
        out["providers"][name] = {
            "driver": utils.read_str(f"{CLASS}/{name}/name"),
            "profile": utils.read_str(f"{CLASS}/{name}/profile"),
            "choices": (utils.read_str(f"{CLASS}/{name}/choices") or "").split(),
        }
    return out


def set_profile(value: str) -> tuple[bool, str]:
    if value not in VALID:
        return False, f"invalid profile {value!r}, choices: {', '.join(VALID)}"
    ok, msg = utils.write_str(FIRMWARE, value)
    if ok:
        return True, "ok (firmware path)"
    # fallback: try each class device directly
    errors = [msg]
    wrote = 0
    for dev in utils.list_dir(CLASS):
        o, m = utils.write_str(f"{CLASS}/{dev}/profile", value)
        if o:
            wrote += 1
        else:
            errors.append(f"{dev}: {m}")
    if wrote:
        return True, f"ok ({wrote} provider(s))"
    return False, "; ".join(errors)
