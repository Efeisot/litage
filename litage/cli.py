"""litage CLI — LLT'nin `llt feature get/set` modelinin Linux karşılığı.

Read commands work as user; write commands need root (sudo litage set ...).
Exit codes: 0 ok, 1 usage/error, 2 hardware not supported, 3 write failed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from . import capabilities as capmod
from . import privileged as priv
from .backends import (
    audio,
    backlight,
    battery,
    cpufreq,
    ideapad,
    legion,
    optional,
    platform_profile,
    rfkill,
    sensors,
    thinklmi,
    thinkpad,
    tlp,
)


def _cap() -> capmod.Capability:
    return capmod.detect()


WRITABLE = {
    "platform_profile": "platform_profile low-power|balanced|performance",
    "conservation": "ideapad conservation on/off",
    "fan_mode": "ideapad fan_mode <int>",
    "fn_lock": "ideapad fn_lock on/off",
    "camera_power": "ideapad camera on/off",
    "usb_charging": "ideapad usb_charging on/off",
    "kbd_backlight": "ideapad kbd_backlight 0..max",
    "governor": "cpu governor (powersave/performance)",
    "epp": "cpu energy_performance_preference",
    "boost": "cpu boost on/off",
    "brightness": "display brightness <backlight> <value|50%>",
    "wifi": "rfkill wifi on/off",
    "bluetooth": "rfkill bluetooth on/off",
    "airplane": "rfkill all on/off",
    "mic": "audio mic mute/unmute",
    "speaker": "audio speaker mute/unmute",
    "kbd_auto": "klavye oto-parlaklik on/off (ALS, daemon)",
    "lux": "ortam isigi (lux, salt-okunur)",
    # legion (sadece legion_laptop modülü varsa)
    "rapidcharge": "legion rapidcharge on/off (conservation'ı kapatır)",
    "fan_fullspeed": "legion fan_fullspeed on/off",
    "lockfancontroller": "legion lockfancontroller on/off",
    "fan_unlock": "legion fan_unlock on/off (destekli modelde)",
    "overdrive": "legion overdrive on/off",
    "gsync": "legion gsync on/off",
    "cpu_oc": "legion cpu_oc on/off",
    "gpu_oc": "legion gpu_oc on/off",
    "powerlimit": "legion limit '<node> <watt>' örn: 'cpu_longterm_powerlimit 45'",
    # tlp (tek opsiyonel bağımlılık)
    "tlp_profile": "tlp profile ac|battery (anlık zorla)",
    "tlp_charge": "tlp charge '<alt> <üst> [BAT]' örn: '20 80'",
}


def cmd_status(args: argparse.Namespace) -> int:
    cap = _cap()
    data = {
        "machine": {
            "vendor": cap.vendor,
            "product": cap.product_name,
            "version": cap.product_version,
            "bios": cap.bios_version,
        },
        "platform_profile": platform_profile.get(cap),
        "ideapad": ideapad.get_all(cap),
        "cpu": cpufreq.get(),
        "battery": battery.get(cap),
        "display": backlight.get(cap),
        "rfkill": rfkill.get(),
        "audio": audio.get(),
        "thinklmi": thinklmi.get(cap),
        "sensors": sensors.get(),
        "legion": (
            optional.legion_get(cap) if not cap.has_legion_module
            else legion.get_all()
        ),
        "nvidia": optional.nvidia_get(cap),
        "tlp": {
            "present": cap.has_tlp,
            "system": tlp.system_info() if cap.has_tlp else {},
            "config": (
                {k: v for k, v in tlp.config_values().items()
                 if k in tlp.WRITABLE_KEYS} if cap.has_tlp else {}
            ),
        },
        "thinkpad": thinkpad.get() if cap.has_thinkpad else {"present": False},
    }
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    # human-readable, script-friendly key=value
    print(f"# {cap.vendor} {cap.product_version} (BIOS {cap.bios_version})")
    pp = data["platform_profile"]
    print(f"platform_profile={pp.get('active')} choices={' '.join(pp.get('choices', []))}")
    for prov, p in pp.get("providers", {}).items():
        print(f"  provider[{prov}] driver={p['driver']} profile={p['profile']}")
    for k, v in data["ideapad"].items():
        print(f"ideapad.{k}={v}")
    for k, v in data["cpu"].items():
        print(f"cpu.{k}={v}")
    bat = data["battery"]
    for k in ("status", "capacity", "charge_type_active", "charge_types_raw"):
        if k in bat:
            print(f"battery.{k}={bat[k]}")
    for bl, b in data["display"].get("backlights", {}).items():
        print(f"backlight.{bl}={b['brightness']}/{b['max']} actual={b['actual']}")
    for d in data["rfkill"].get("devices", []):
        print(f"rfkill.{d['name']} type={d['type']} soft={d['soft']} hard={d['hard']}")
    if not cap.show_dgpu_page:
        print("# dgpu: not present — page hidden (by design)")
    if not cap.show_legion_page:
        print("# legion: module/WMI absent — Legion pages hidden (by design)")
    else:
        lg = data["legion"]
        for k, v in lg.get("bools", {}).items():
            print(f"legion.{k}={v}")
        for k, v in lg.get("ints", {}).items():
            print(f"legion.{k}={v}")
        for k, v in lg.get("strs", {}).items():
            print(f"legion.{k}={v}")
    if cap.has_tlp:
        t = data["tlp"]["system"]
        print(f"tlp.profile={t.get('tlp_profile')} power={t.get('power_source')}")
        for k, v in data["tlp"]["config"].items():
            print(f"tlp.{k}={v}")
    else:
        print("# tlp: not installed — TLP section hidden")
    if cap.has_thinkpad:
        for k, v in data["thinkpad"].items():
            if k != "present":
                print(f"thinkpad.{k}={v}")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    cap = _cap()
    print("writable features on THIS machine:")
    for name, desc in WRITABLE.items():
        # capability filter
        if name in ("conservation", "fan_mode", "fn_lock", "camera_power",
                    "usb_charging", "kbd_backlight") and not cap.has_ideapad:
            continue
        if name in ("rapidcharge", "fan_fullspeed", "lockfancontroller",
                    "fan_unlock", "overdrive", "gsync", "cpu_oc", "gpu_oc",
                    "powerlimit") and not cap.has_legion_module:
            continue
        if name in ("tlp_profile", "tlp_charge") and not cap.has_tlp:
            continue
        if name in ("kbd_auto", "lux"):
            try:
                from .backends import als as _als
                if _als.find_als() is None and not cap.has_ideapad:
                    continue
            except ImportError:
                continue
        if name in ("governor", "epp", "boost") and not cap.governors and not cap.epp_prefs:
            continue
        if name == "brightness" and not cap.backlights:
            continue
        if name in ("wifi", "bluetooth", "airplane") and not (
            cap.has_wifi_rfkill or cap.has_bt_rfkill
        ):
            continue
        print(f"  {name:16s} {desc}")
    print("read-only: status, monitor, sensors, thinklmi")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    cap = _cap()
    name = args.feature
    if name == "platform_profile":
        print(platform_profile.get(cap).get("active"))
        return 0
    ide = ideapad.get_all(cap)
    if name in ide:
        print(ide[name])
        return 0
    if name == "kbd_auto":
        print(get_daemon_kbd_auto() or "off")
        return 0
    if name == "lux":
        try:
            from .backends import als as _als
            v = _als.lux()
            print(f"{v:.0f}" if v is not None else "yok")
        except ImportError:
            print("yok")
        return 0
    cpu = cpufreq.get()
    if name in ("governor", "epp", "boost", "driver"):
        print(cpu.get(name))
        return 0
    if cap.has_legion_module:
        lg = legion.get_all()
        for section in ("bools", "ints", "strs"):
            if name in lg.get(section, {}):
                print(lg[section][name])
                return 0
        if name == "fancurve":
            import json as _j
            print(_j.dumps(lg.get("fancurve", {}), indent=2))
            return 0
    if cap.has_tlp and name.startswith("tlp"):
        cfg = tlp.config_values()
        key = name[4:].upper() if name != "tlp" else ""
        if name == "tlp":
            import json as _j
            print(_j.dumps(tlp.system_info(), indent=2))
            return 0
        if key in cfg:
            print(cfg[key])
            return 0
    print(f"unknown feature {name!r}; try: litage list", file=sys.stderr)
    return 1


def _apply_one(cap, feature: str, value: str) -> tuple[bool, str, int]:
    """Tek ozelligi uygula. Donus: (ok, mesaj, exit-kod)."""
    f, v = feature, value
    if f == "platform_profile":
        ok, msg = platform_profile.set_profile(v)
    elif f in ("conservation", "fan_mode", "fn_lock", "camera_power",
               "usb_charging", "kbd_backlight"):
        if not cap.has_ideapad:
            return False, "not supported on this machine (no ideapad-laptop)", 2
        ok, msg = ideapad.set_feature(cap, f, v)
    elif f == "governor":
        ok, msg = cpufreq.set_governor(v)
    elif f == "epp":
        ok, msg = cpufreq.set_epp(v)
    elif f == "boost":
        ok, msg = cpufreq.set_boost(v)
    elif f == "brightness":
        parts = v.split()
        if len(parts) != 2:
            return False, "usage: brightness '<backlight> <value>'", 1
        ok, msg = backlight.set_brightness(parts[0], parts[1])
    elif f in ("wifi", "bluetooth", "airplane"):
        on = v.lower() in ("on", "unblock", "0", "false")
        ok, msg = rfkill.set_block(f, block=not on)
    elif f in ("mic", "speaker"):
        target = "sink" if f == "speaker" else "source"
        mute = v.lower() in ("mute", "muted", "off", "1", "true")
        ok, msg = audio.set_mute(target, mute)
    elif f in ("rapidcharge", "fan_fullspeed", "lockfancontroller", "fan_unlock",
               "overdrive", "gsync", "cpu_oc", "gpu_oc", "minifancurve",
               "winkey", "instant_boot_ac", "instant_boot_usb_pd"):
        if not cap.has_legion_module:
            return False, "not supported (legion_laptop module not loaded)", 2
        ok, msg = legion.set_bool(f, v)
    elif f == "powerlimit":
        if not cap.has_legion_module:
            return False, "not supported (legion_laptop module not loaded)", 2
        parts = v.split()
        if len(parts) != 2:
            return False, "usage: powerlimit '<node> <watt>'", 1
        ok, msg = legion.set_int(parts[0], parts[1])
    elif f == "tlp_profile":
        if not cap.has_tlp:
            return False, "not supported (tlp not installed)", 2
        ok, msg = tlp.force_profile(v)
    elif f == "kbd_auto":
        ok, msg = set_daemon_kbd_auto(v)
        return ok, msg, (0 if ok else 3)
    elif f == "tlp_charge":
        if not cap.has_tlp:
            return False, "not supported (tlp not installed)", 2
        parts = v.split()
        if len(parts) not in (2, 3):
            return False, "usage: tlp_charge '<lo> <hi> [BAT]'", 1
        try:
            lo, hi = int(parts[0]), int(parts[1])
        except ValueError:
            return False, "tlp_charge needs integers", 1
        ok, msg = tlp.setcharge(lo, hi, parts[2] if len(parts) == 3 else "BAT0")
    else:
        return False, f"unknown feature {f!r}; try: litage list", 1
    return ok, msg, (0 if ok else 3)


DAEMON_CONF = "/etc/litage/litaged.conf"


def set_daemon_kbd_auto(value: str) -> tuple[bool, str]:
    import configparser
    v = {"on": "true", "off": "false", "true": "true", "false": "false",
         "1": "true", "0": "false"}.get(value.lower())
    if v is None:
        return False, "kbd_auto on/off ister"
    cfg = configparser.ConfigParser()
    try:
        if __import__("os").path.exists(DAEMON_CONF):
            cfg.read(DAEMON_CONF)
        if not cfg.has_section("keyboard"):
            cfg.add_section("keyboard")
        cfg.set("keyboard", "auto", v)
        with open(DAEMON_CONF, "w", encoding="utf-8") as f:
            cfg.write(f)
        return True, f"klavye oto: {v}"
    except OSError as e:
        return False, f"yazılamadı ({DAEMON_CONF}): {e}"


def get_daemon_kbd_auto() -> str | None:
    import configparser
    cfg = configparser.ConfigParser()
    try:
        if not __import__("os").path.exists(DAEMON_CONF):
            return None
        cfg.read(DAEMON_CONF)
        return cfg.get("keyboard", "auto", fallback=None)
    except (OSError, configparser.Error):
        return None

def cmd_set(args: argparse.Namespace) -> int:
    cap = _cap()
    ok, msg, code = _apply_one(cap, args.feature, args.value)
    print(msg)
    return code


def cmd_apply(args: argparse.Namespace) -> int:
    """Toplu uygula: tek pkexec sifresiyle birden cok ayar.

    Kullanim: litage apply platform_profile=balanced fn_lock=on
    """
    cap = _cap()
    worst = 0
    for pair in args.pairs:
        if "=" not in pair:
            print(f"atlandi (bicim feature=value olmali): {pair}")
            worst = max(worst, 1)
            continue
        feat, val = pair.split("=", 1)
        ok, msg, code = _apply_one(cap, feat.strip(), val.strip())
        print(f"{feat}={val}: {msg}")
        worst = max(worst, code)
    return worst


def cmd_monitor(args: argparse.Namespace) -> int:
    n = args.count
    i = 0
    try:
        while n == 0 or i < n:
            cpu = cpufreq.get()
            sen = sensors.get()
            line = f"cpu_mhz={cpu.get('cpu_mhz_avg')} gov={cpu.get('governor')} epp={cpu.get('epp')}"
            for k, vals in sen["hwmon"].items():
                for nk, nv in vals.items():
                    line += f" {k}.{nk}={nv}"
            print(line, flush=True)
            i += 1
            if n == 0 or i < n:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    print(priv.doctor_text())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="litage", description="Lenovo Vantage alternative for Linux")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status", help="dump all features")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)
    li = sub.add_parser("list", help="list writable features on this machine")
    li.set_defaults(func=cmd_list)
    g = sub.add_parser("get", help="get one feature")
    g.add_argument("feature")
    g.set_defaults(func=cmd_get)
    st = sub.add_parser("set", help="set one feature (needs root)")
    st.add_argument("feature")
    st.add_argument("value")
    st.set_defaults(func=cmd_set)
    ap = sub.add_parser("apply", help="toplu uygula: feature=value ... (tek sifre)")
    ap.add_argument("pairs", nargs="+")
    ap.set_defaults(func=cmd_apply)
    m = sub.add_parser("monitor", help="1s sensor dump")
    m.add_argument("-n", "--count", type=int, default=0, help="0 = infinite")
    m.add_argument("-i", "--interval", type=float, default=1.0)
    m.set_defaults(func=cmd_monitor)
    d = sub.add_parser("doctor", help="kurulum teşhisi (neden yazma çalışmıyor?)")
    d.set_defaults(func=cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
