"""Capability detection — the core of Litage's adaptive UI.

Every page/feature in GUI/CLI checks these flags first. Unsupported hardware
(e.g. dGPU on iGPU-only Yoga 14AKP10, Legion fan curves without legion_laptop
module, RGB without gamezone WMI) is hidden, never shown as broken toggle.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field

from . import utils

SYSFS_PLATFORM = "/sys/bus/platform/devices"
WMI_BUS = "/sys/bus/wmi/devices"
HWMON = "/sys/class/hwmon"
BACKLIGHT = "/sys/class/backlight"
POWER_SUPPLY = "/sys/class/power_supply"
PLATFORM_PROFILE_CLASS = "/sys/class/platform-profile"
FIRMWARE_PROFILE = "/sys/firmware/acpi/platform_profile"
THINKLMI = "/sys/class/firmware-attributes/thinklmi/attributes"

GAMEZONE_GUID = "887B54E3-DDDC-11E4-9A98-E3B0671FC9B"
FAN_GUID = "92549549-4BDE-11E4-A993-B8B9233AA983"


@dataclass
class Capability:
    vendor: str = ""
    product_name: str = ""
    product_version: str = ""
    bios_version: str = ""
    # providers
    has_ideapad: bool = False
    ideapad_path: str = ""
    platform_profiles: list[str] = field(default_factory=list)  # class device names
    has_firmware_profile: bool = False
    has_amd_pmf: bool = False
    thinklmi_attrs: list[str] = field(default_factory=list)
    # legion / gaming
    has_legion_module: bool = False
    legion_path: str = ""
    legion_nodes: list[str] = field(default_factory=list)
    has_gamezone_wmi: bool = False
    has_fan_wmi: bool = False
    # thinkpad
    has_thinkpad: bool = False
    # tlp (tek opsiyonel bağımlılık)
    has_tlp: bool = False
    tlp_profile: str = ""
    # gpu
    has_amdgpu: bool = False
    has_nvidia: bool = False
    has_intel_gpu: bool = False
    # input/light
    has_kbd_backlight: bool = False
    kbd_backlight_max: int = 0
    has_fnlock_led: bool = False
    # power/cpu
    governors: list[str] = field(default_factory=list)
    epp_prefs: list[str] = field(default_factory=list)
    scaling_driver: str = ""
    has_boost: bool = False
    # battery
    has_battery: bool = False
    batteries: list[str] = field(default_factory=list)
    charge_types: list[str] = field(default_factory=list)
    # display
    backlights: list[str] = field(default_factory=list)
    # rf
    has_wifi_rfkill: bool = False
    has_bt_rfkill: bool = False

    @property
    def is_lenovo(self) -> bool:
        return self.vendor.strip().upper() == "LENOVO"

    @property
    def show_legion_page(self) -> bool:
        return self.has_legion_module or self.has_gamezone_wmi

    @property
    def show_dgpu_page(self) -> bool:
        return self.has_nvidia

    @property
    def show_fan_curve_page(self) -> bool:
        return self.has_legion_module  # only legion module exposes curves


def _dmi(name: str) -> str:
    return utils.read_str(f"/sys/class/dmi/id/{name}") or ""


def _wmi_guids() -> set[str]:
    guids: set[str] = set()
    for entry in utils.list_dir(WMI_BUS):
        # entries look like GUID-instance; guid is first 36 chars
        guids.add(entry[:36].upper())
    return guids


def detect(sys_root: str = "/") -> Capability:
    """Detect capabilities. sys_root allows tests with a mock tree."""
    cap = Capability()
    if sys_root == "/":
        cap.vendor = _dmi("sys_vendor")
        cap.product_name = _dmi("product_name")
        cap.product_version = _dmi("product_version")
        cap.bios_version = _dmi("bios_version")

        # ideapad VPC
        for dev in glob.glob(f"{SYSFS_PLATFORM}/VPC*"):
            if os.path.exists(os.path.join(dev, "conservation_mode")):
                cap.has_ideapad = True
                cap.ideapad_path = dev
                break

        pp_names = utils.list_dir(PLATFORM_PROFILE_CLASS)
        cap.platform_profiles = pp_names
        cap.has_firmware_profile = os.path.exists(FIRMWARE_PROFILE)
        for n in pp_names:
            if (utils.read_str(f"{PLATFORM_PROFILE_CLASS}/{n}/name") or "") == "amd-pmf":
                cap.has_amd_pmf = True

        cap.thinklmi_attrs = utils.list_dir(THINKLMI)

        guids = _wmi_guids()
        cap.has_gamezone_wmi = GAMEZONE_GUID in guids
        cap.has_fan_wmi = FAN_GUID in guids

        # legion module: /sys/module/legion_laptop or platform device
        if os.path.exists("/sys/module/legion_laptop"):
            cap.has_legion_module = True
            cand = utils.first_existing(
                [
                    "/sys/module/legion_laptop/drivers/platform:legion/legion",
                    "/sys/bus/platform/drivers/legion/PNP0C09:00",
                ]
            )
            cap.legion_path = cand or ""
            if cap.legion_path and os.path.isdir(cap.legion_path):
                cap.legion_nodes = utils.list_dir(cap.legion_path)
        else:
            for dev in glob.glob(f"{SYSFS_PLATFORM}/*/legion") + glob.glob(
                "/sys/module/legion_laptop/drivers/*/*"
            ):
                if os.path.exists(dev):
                    cap.has_legion_module = True
                    cap.legion_path = dev
                    if os.path.isdir(dev):
                        cap.legion_nodes = utils.list_dir(dev)
                    break

        # thinkpad_acpi
        cap.has_thinkpad = os.path.isdir("/sys/devices/platform/thinkpad_acpi")

        # tlp (tek opsiyonel bağımlılık)
        import shutil as _shutil

        cap.has_tlp = _shutil.which("tlp") is not None

        # gpus
        for hw in glob.glob(f"{HWMON}/hwmon*"):
            name = utils.read_str(f"{hw}/name") or ""
            if name == "amdgpu":
                cap.has_amdgpu = True
            elif name == "nvidia":
                cap.has_nvidia = True
            elif name == "i915":
                cap.has_intel_gpu = True
        if os.path.exists("/proc/driver/nvidia/gpus"):
            cap.has_nvidia = True

        # leds
        cap.has_kbd_backlight = os.path.exists("/sys/class/leds/platform::kbd_backlight")
        if cap.has_kbd_backlight:
            cap.kbd_backlight_max = (
                utils.read_int("/sys/class/leds/platform::kbd_backlight/max_brightness") or 0
            )
        cap.has_fnlock_led = os.path.exists("/sys/class/leds/platform::fnlock")

        # cpu
        govs = utils.read_str("/sys/devices/system/cpu/cpufreq/policy0/scaling_available_governors")
        if govs:
            cap.governors = govs.split()
        epps = utils.read_str(
            "/sys/devices/system/cpu/cpufreq/policy0/energy_performance_available_preferences"
        )
        if epps:
            cap.epp_prefs = epps.split()
        cap.scaling_driver = (
            utils.read_str("/sys/devices/system/cpu/cpufreq/policy0/scaling_driver") or ""
        )
        cap.has_boost = os.path.exists("/sys/devices/system/cpu/cpufreq/boost")

        # battery (multi-battery: BAT0 + BAT1 ...)
        cap.batteries = sorted(
            d for d in utils.list_dir(POWER_SUPPLY) if d.startswith("BAT")
        )
        cap.has_battery = len(cap.batteries) > 0
        bat0 = cap.batteries[0] if cap.batteries else "BAT0"
        ct = utils.read_str(f"{POWER_SUPPLY}/{bat0}/charge_types")
        if ct:
            # "[Long_Life]" marks active; strip brackets for list
            cap.charge_types = [t.strip("[]") for t in ct.split()]

        # display backlight
        cap.backlights = utils.list_dir(BACKLIGHT)

        # rfkill (ideapad_wlan / ideapad_bluetooth symlinks or rfkill list)
        for rf in glob.glob("/sys/class/rfkill/rfkill*"):
            name = utils.read_str(f"{rf}/name") or ""
            if "wlan" in name or "phy" in name:
                cap.has_wifi_rfkill = True
            if "bluetooth" in name or "hci" in name:
                cap.has_bt_rfkill = True
    else:
        # mock tree for tests: mirror same logic under sys_root
        def j(*parts: str) -> str:
            return os.path.join(sys_root.lstrip("/"), *parts) if sys_root != "/" else os.path.join(*parts)

        cap.vendor = utils.read_str(os.path.join(sys_root, "dmi/sys_vendor")) or ""
        cap.product_name = utils.read_str(os.path.join(sys_root, "dmi/product_name")) or ""
        cap.bios_version = utils.read_str(os.path.join(sys_root, "dmi/bios_version")) or ""
        ide = os.path.join(sys_root, "VPC2004:00")
        if os.path.exists(os.path.join(ide, "conservation_mode")):
            cap.has_ideapad = True
            cap.ideapad_path = ide
        pp = os.path.join(sys_root, "platform-profile")
        if os.path.isdir(pp):
            cap.platform_profiles = sorted(os.listdir(pp))
            cap.has_firmware_profile = os.path.exists(os.path.join(pp, "profile"))
    return cap
