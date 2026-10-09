"""TLP backend — tek opsiyonel bağımlılık olarak TLP entegrasyonu.

TLP zaten kurulu ve aktif (tlp-stat ile doğrulandı). Litage TLP'yi
rakip olarak değil tamamlayıcı olarak kullanır:

- Okuma: `tlp-stat` çıktısı (pil, CPU, grafik) + /etc/tlp.conf değerleri
  (PLATFORM_PROFILE_ON_AC/BAT, CPU_ENERGY_PERF_POLICY_*, CPU_BOOST_*,
  charge thresholds). Root'suz temel okuma; detay root ister.
- Yazma: `tlp setcharge` (şarj eşikleri), `tlp ac/battery` (profil zorlama),
  config anahtarları için güvenli aralık kontrolü.
- Çakışma notu: TLP + litaged aynı anda CPU governor yazarsa son yazan
  kazanır. Öneri: litaged presetlerinde governor/epp BOŞ bırakılırsa TLP
  yönetir; doluysa litaged yönetir (daemon.py'de belgeli).

Referans: tlp-stat(8), tlp(8), /etc/tlp.conf + /etc/tlp.d/*.conf
"""
from __future__ import annotations

import re
import shutil
import subprocess

from .. import utils

CONF_FILES = ["/etc/tlp.conf", "/etc/tlp.d/00-template.conf"] + [
    f"/etc/tlp.d/{n}" for n in (utils.list_dir("/etc/tlp.d/") or [])
]

# Litage'in yönettiği güvenli TLP anahtarları (değer aralıklarıyla)
WRITABLE_KEYS = {
    "PLATFORM_PROFILE_ON_AC": ("low-power", "balanced", "performance"),
    "PLATFORM_PROFILE_ON_BAT": ("low-power", "balanced", "performance"),
    "CPU_ENERGY_PERF_POLICY_ON_AC": (
        "performance", "balance_performance", "balance_power", "power", "default"),
    "CPU_ENERGY_PERF_POLICY_ON_BAT": (
        "performance", "balance_performance", "balance_power", "power", "default"),
    "CPU_BOOST_ON_AC": ("0", "1"),
    "CPU_BOOST_ON_BAT": ("0", "1"),
    "CPU_SCALING_GOVERNOR_ON_AC": ("powersave", "performance"),
    "CPU_SCALING_GOVERNOR_ON_BAT": ("powersave", "performance"),
}


def available() -> bool:
    return shutil.which("tlp") is not None


def _run(*args: str, timeout: int = 10) -> tuple[bool, str]:
    try:
        p = subprocess.run(
            ["tlp-stat", *args] if args[0].startswith("-") else list(args),
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return (True, p.stdout) if p.returncode == 0 else (False, p.stderr.strip())


def system_info() -> dict:
    """`tlp-stat -s` — root'suz çalışır."""
    ok, out = _run("-s")
    if not ok:
        return {"present": available(), "error": out}
    info: dict = {"present": True}
    for line in out.splitlines():
        m = re.match(r"\s*(\w[\w ]+?)\s*=\s*(.+)", line)
        if m:
            k = m.group(1).strip().lower().replace(" ", "_")
            if k in ("tlp_profile", "power_source", "tlp"):
                info[k] = m.group(2).strip()
    return info


def battery_info() -> dict:
    """`tlp-stat -b` — eşikler dahil; root'suz kısıtlı olabilir."""
    ok, out = _run("-b")
    if not ok:
        return {"error": out}
    info: dict = {}
    for line in out.splitlines():
        if "charge_control" in line or "threshold" in line.lower() or "capacity" in line.lower():
            info.setdefault("lines", []).append(line.strip())
        m = re.match(r"\s*charge_control_(start|end)_threshold\s*=\s*(\d+)", line)
        if m:
            info[f"threshold_{m.group(1)}"] = int(m.group(2))
    info["raw_preview"] = "\n".join(out.splitlines()[:25])
    return info


def config_values() -> dict:
    """tlp.conf + tlp.d'den etkin değerler (yorumsuz, son kazanan)."""
    vals: dict = {}
    seen = set()
    for path in ["/etc/tlp.conf"] + [f"/etc/tlp.d/{f}" for f in utils.list_dir("/etc/tlp.d")]:
        text = utils.read_str(path)
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"')
            seen.add(path)
    return vals


def setcharge(low: int, high: int, bat: str = "BAT0") -> tuple[bool, str]:
    """`tlp setcharge lo hi [BAT]` — ThinkPad/Lenovo şarj eşikleri."""
    if not available():
        return False, "tlp kurulu değil"
    if not 20 <= low < high <= 100:
        return False, "aralık geçersiz: 20 <= alt < üst <= 100 olmalı"
    try:
        p = subprocess.run(
            ["tlp", "setcharge", str(low), str(high), bat],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    ok = p.returncode == 0
    return ok, (p.stdout.strip() or p.stderr.strip() or "ok")


def force_profile(where: str) -> tuple[bool, str]:
    """`tlp ac` / `tlp battery` — profili anlık zorla."""
    if where not in ("ac", "battery"):
        return False, "ac|battery ister"
    if not available():
        return False, "tlp kurulu değil"
    try:
        p = subprocess.run(["tlp", where], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    ok = p.returncode == 0
    return ok, (p.stdout.strip().splitlines()[-1] if p.stdout else (p.stderr.strip() or "ok"))
