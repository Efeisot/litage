"""Legion backend — LenovoLegionLinux (LLL) `legion.py` referanslı port.

Kapsam: SADECE `legion_laptop` çekirdek modülü yüklüyse aktiftir
(cap.has_legion_module). Yoga/IdeaPad'de modül yoktur -> tüm fonksiyonlar
`{"present": False}` döner, GUI sayfası gizlenir.

Referans: LenovoLegionLinux/python/legion_linux/legion_linux/legion.py
  - LEGION_SYS_BASEPATH: kernel >= 7.0 ise .../platform:legion/legion,
    değilse .../platform:legion/PNP0C09:00 (legion.py:31-39)
  - IDEAPAD_SYS_BASEPATH: /sys/bus/platform/drivers/ideapad_acpi/VPC2004:00
  - Tüm node adları + mutual-exclusion (conservation<->rapidcharge) LLL ile aynı.
  - Fan curve: hwmon pwm1/2_auto_point{N}_pwm/temp/temp_hyst + minifancurve +
    fancurve_speed_unit (level/rpm/percent) + seviye->RPM tabloları.
  - Preset dizini: /etc/legion_linux (LLL) ve /etc/litage/profiles (Litage);
    LLL presetleri okunabilir (aynı FanCurve YAML şeması).

Güvenlik: ham EC yazımı yok; sadece çekirdeğin açtığı sysfs dosyaları.
Yazmalar root ister; okumalar kullanıcı olarak çalışır.
"""
from __future__ import annotations

import glob
import os

from .. import utils

# --- base path resolution (LLL legion.py:31-39) ---
LEGION_CANDIDATES = [
    "/sys/module/legion_laptop/drivers/platform:legion/legion",  # kernel >= 7.0
    "/sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00",  # kernel < 7.0
]
IDEAPAD_BASE = "/sys/bus/platform/drivers/ideapad_acpi/VPC2004:00"

# LLL legion.py'deki feature -> node eşlemesi
BOOL_NODES = {
    # legion base
    "lockfancontroller": "lockfancontroller",
    "fan_unlock": "fan_unlock",
    "rapidcharge": "rapidcharge",
    "winkey": "winkey",
    "touchpad_legion": "touchpad",
    "overdrive": "overdrive",
    "gsync": "gsync",
    "instant_boot_ac": "instant_boot_ac",
    "instant_boot_usb_pd": "instant_boot_usb_pd",
    "fan_fullspeed": "fan_fullspeed",
    "cpu_oc": "cpu_oc",
    "gpu_oc": "gpu_oc",
    "minifancurve": "minifancurve",  # hwmon altında da olabilir, aşağıda çözülür
}
INT_NODES = {
    "cpu_shortterm_powerlimit": (5, 200),
    "cpu_longterm_powerlimit": (5, 200),
    "cpu_peak_powerlimit": (0, 200),
    "cpu_apu_sppt_powerlimit": (0, 100),
    "cpu_cross_loading_powerlimit": (0, 100),
    "gpu_ctgp_powerlimit": (0, 200),
    "gpu_ppab_powerlimit": (0, 200),
    "gpu_temperature_limit": (0, 120),
    "cpu_temperature_limit": (0, 120),
}
STR_NODES = {
    "powermode": "powermode",
    "fancurve_speed_unit": "fancurve_speed_unit",
}

LEGION_PRESET_DIRS = ["/etc/litage/profiles", "/etc/legion_linux"]


def base_path() -> str | None:
    for c in LEGION_CANDIDATES:
        if os.path.exists(c):
            return c
    # legiond tarzı glob fallback (powerlimit.h:12-16)
    for dev in glob.glob("/sys/bus/platform/drivers/legion/*"):
        if os.path.isdir(dev) and os.path.exists(os.path.join(dev, "powermode")):
            return dev
    return None


def exists() -> bool:
    return base_path() is not None


def _node(name: str) -> str | None:
    base = base_path()
    if not base:
        return None
    p = os.path.join(base, name)
    return p if os.path.exists(p) else None


def hwmon_path() -> str | None:
    base = base_path()
    if not base:
        return None
    hits = sorted(glob.glob(os.path.join(base, "hwmon/hwmon*")))
    return hits[0] if hits else None


def get_all() -> dict:
    """Tüm Legion node'larını oku (var olanlar)."""
    if not exists():
        return {"present": False}
    base = base_path() or ""
    out: dict = {"present": True, "path": base, "bools": {}, "ints": {}, "strs": {}}
    for feat, node in BOOL_NODES.items():
        p = os.path.join(base, node)
        if not os.path.exists(p):
            # minifancurve hwmon altında da olabilir
            hw = hwmon_path()
            if feat == "minifancurve" and hw:
                p2 = os.path.join(hw, "minifancurve")
                if os.path.exists(p2):
                    out["bools"][feat] = utils.read_str(p2)
                    continue
            continue
        out["bools"][feat] = utils.read_str(p)
    for feat, (_lo, _hi) in INT_NODES.items():
        p = os.path.join(base, feat)
        if os.path.exists(p):
            out["ints"][feat] = utils.read_str(p)
    for feat, node in STR_NODES.items():
        p = os.path.join(base, node)
        if os.path.exists(p):
            out["strs"][feat] = utils.read_str(p)
    # ideapad tarafı (conservation LLL'de ideapad_acpi altındadır)
    for node in ("conservation_mode", "fn_lock", "camera_power", "touchpad"):
        p = os.path.join(IDEAPAD_BASE, node)
        alt = f"/sys/bus/platform/devices/VPC2004:00/{node}"
        q = p if os.path.exists(p) else (alt if os.path.exists(alt) else None)
        if q:
            out["bools"][f"ideapad_{node}"] = utils.read_str(q)
    # platform profile (LLL: $LEGION/platform-profile/platform-profile-*/profile)
    for pp in sorted(glob.glob(os.path.join(base, "platform-profile/platform-profile-*"))):
        out.setdefault("platform_profiles", {})[os.path.basename(pp)] = {
            "profile": utils.read_str(os.path.join(pp, "profile")),
            "choices": (utils.read_str(os.path.join(pp, "choices")) or "").split(),
        }
    # seviye tabloları
    for fan in ("fan1_level_rpm_table", "fan2_level_rpm_table"):
        p = os.path.join(base, fan)
        if os.path.exists(p):
            out["strs"][fan] = utils.read_str(p)
    out["fancurve"] = fancurve_summary()
    return out


# --- fan curve (okuma; yazma LLL'deki snapshot+rollback ile aynı prensip) ---
POINTS = range(1, 11)


def fancurve_summary() -> dict:
    hw = hwmon_path()
    if not hw:
        return {"present": False}
    p1 = os.path.join(hw, "pwm1_auto_point1_pwm")
    if not os.path.exists(p1):
        return {"present": False}
    pts = []
    for n in POINTS:
        pt = {"id": n}
        for key in ("pwm1_auto_point%d_pwm", "pwm2_auto_point%d_pwm",
                    "pwm1_auto_point%d_temp", "pwm1_auto_point%d_temp_hyst",
                    "pwm2_auto_point%d_temp", "pwm2_auto_point%d_temp_hyst"):
            node = key % n
            v = utils.read_str(os.path.join(hw, node))
            if v is not None:
                pt[node] = v
        pts.append(pt)
    return {
        "present": True,
        "hwmon": hw,
        "speed_unit": utils.read_str(os.path.join(base_path() or "", "fancurve_speed_unit")),
        "minifancurve": utils.read_str(os.path.join(hw, "minifancurve")),
        "points": pts,
    }


def set_bool(feature: str, value: str) -> tuple[bool, str]:
    """LLL mutual-exclusion ile: conservation<->rapidcharge birbirini kapatır."""
    v = {"on": "1", "off": "0", "true": "1", "false": "0"}.get(value.lower(), value)
    if v not in ("0", "1"):
        return False, f"{feature} on/off ister"
    base = base_path()
    if not base:
        return False, "legion_laptop modülü yüklü değil"
    # conservation ideapad tarafında, rapidcharge legion tarafında (LLL:487-516)
    if feature == "conservation":
        idea = utils.first_existing(
            [f"{IDEAPAD_BASE}/conservation_mode",
             "/sys/bus/platform/devices/VPC2004:00/conservation_mode"]
        )
        if not idea:
            return False, "conservation_mode bulunamadı"
        if v == "1":  # rapidcharge'ı kapat (LLL:505-516 tersi de geçerli)
            rp = os.path.join(base, "rapidcharge")
            if os.path.exists(rp):
                utils.write_str(rp, "0")
        return utils.write_str(idea, v)
    if feature == "rapidcharge":
        if v == "1":
            idea = utils.first_existing(
                [f"{IDEAPAD_BASE}/conservation_mode",
                 "/sys/bus/platform/devices/VPC2004:00/conservation_mode"]
            )
            if idea:
                utils.write_str(idea, "0")
        p = os.path.join(base, "rapidcharge")
        if not os.path.exists(p):
            return False, "rapidcharge bulunamadı"
        return utils.write_str(p, v)
    if feature not in BOOL_NODES:
        return False, f"bilinmeyen legion özelliği: {feature}"
    p = os.path.join(base, BOOL_NODES[feature])
    hw = hwmon_path()
    if not os.path.exists(p) and feature == "minifancurve" and hw:
        p = os.path.join(hw, "minifancurve")
    if not os.path.exists(p):
        return False, f"{feature} bu modelde yok"
    return utils.write_str(p, v)


def set_int(feature: str, value: str) -> tuple[bool, str]:
    base = base_path()
    if not base:
        return False, "legion_laptop modülü yüklü değil"
    if feature not in INT_NODES:
        return False, f"bilinmeyen limit: {feature}"
    lo, hi = INT_NODES[feature]
    try:
        iv = int(value)
    except ValueError:
        return False, f"{feature} tamsayı ister ({lo}-{hi}W)"
    if not lo <= iv <= hi:
        return False, f"aralık dışı: {lo}-{hi}"
    p = os.path.join(base, feature)
    if not os.path.exists(p):
        return False, f"{feature} bu modelde yok"
    return utils.write_str(p, str(iv))
