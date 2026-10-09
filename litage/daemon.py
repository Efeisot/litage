"""litaged — init-agnostic automation daemon (pure Python, stdlib only).

Watches AC state + platform profile (polling; inotify if available, no hard
dependency) and applies YAML presets from /etc/litage/profiles/:

  <profile>-ac.yaml / <profile>-battery.yaml

plus [cpu]/[gpu] sections of /etc/litage/litaged.conf. Safe by design:
only writes values the kernel already allows via sysfs.

TLP ile birlikte kullanım: TLP kuruluysa ve aktifse, preset'te governor/epp
anahtarlarını BOŞ bırakın -> TLP yönetir. Doluysa litaged yönetir. İkisi aynı
anda yazarsa son yazan kazanır; kavga etmemesi için tek yönetici seçin
(öneri: CPU için TLP, ideapad/fan/kbd için litaged).

Usage:
  litaged [--once] [--config PATH] [--profiles DIR] [--interval SEC] [--daemon]
"""
from __future__ import annotations

import argparse
import configparser
import glob
import os
import sys
import time

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from litage import capabilities as capmod  # noqa: E402
from litage.backends import cpufreq, ideapad, platform_profile  # noqa: E402
from litage import utils  # noqa: E402

DEFAULT_CONFIG = "/etc/litage/litaged.conf"
DEFAULT_PROFILES = "/etc/litage/profiles"

CONF_TEMPLATE = """\
[daemon]
# polling interval in seconds (inotify used when available, this is fallback)
interval = 5
# preset base names per platform profile
# e.g. platform_profile=balanced + AC -> profiles/balanced-ac.yaml
profiles_dir = /etc/litage/profiles

[cpu]
# optional fixed overrides applied after preset (empty = preset wins)
# governor =
# epp =
"""


def on_ac() -> bool | None:
    for ps in sorted(glob.glob("/sys/class/power_supply/AC*")) + sorted(
        glob.glob("/sys/class/power_supply/ADP*")
    ):
        v = utils.read_int(os.path.join(ps, "online"))
        if v is not None:
            return v == 1
    # fallback: BAT0 discharging => on battery
    st = utils.read_str("/sys/class/power_supply/BAT0/status")
    if st:
        return st.lower() != "discharging"
    return None


def current_profile() -> str:
    return utils.read_str("/sys/firmware/acpi/platform_profile") or "balanced"


def load_preset(profiles_dir: str, profile: str, ac: bool | None) -> dict:
    if yaml is None:
        return {}
    suffix = "ac" if ac else "battery" if ac is False else "unknown"
    for cand in (
        os.path.join(profiles_dir, f"{profile}-{suffix}.yaml"),
        os.path.join(profiles_dir, f"{profile}.yaml"),
    ):
        if os.path.exists(cand):
            try:
                with open(cand, encoding="utf-8") as f:
                    return dict(yaml.safe_load(f) or {})
            except OSError:
                return {}
    return {}


def apply_preset(preset: dict, cap: capmod.Capability) -> list[str]:
    log: list[str] = []
    if "platform_profile" in preset:
        ok, msg = platform_profile.set_profile(str(preset["platform_profile"]))
        log.append(f"platform_profile: {msg}")
    if "governor" in preset:
        ok, msg = cpufreq.set_governor(str(preset["governor"]))
        log.append(f"governor: {msg}")
    if "epp" in preset:
        ok, msg = cpufreq.set_epp(str(preset["epp"]))
        log.append(f"epp: {msg}")
    for k in ("conservation", "fan_mode", "fn_lock", "kbd_backlight"):
        if k in preset and cap.has_ideapad:
            ok, msg = ideapad.set_feature(cap, k, str(preset[k]))
            log.append(f"{k}: {msg}")
    return log


def kbd_auto_tick(cfg: configparser.ConfigParser, cap: capmod.Capability,
                  state: dict) -> None:
    """Oto klavye ışığı: ALS lux -> 0/1/2 (sadece değişince yazar)."""
    try:
        auto = cfg.getboolean("keyboard", "auto", fallback=False)
    except (configparser.Error, ValueError):
        auto = False
    if not auto or not cap.has_ideapad:
        return
    try:
        from litage.backends import als as _als
    except ImportError:
        return
    lux = _als.lux()
    if lux is None:
        return
    dark = cfg.getfloat("keyboard", "lux_dark_below", fallback=30.0)
    bright = cfg.getfloat("keyboard", "lux_bright_above", fallback=150.0)
    level = _als.kbd_level_for_lux(lux, dark, bright)
    if state.get("kbd_auto_level") == level:
        return
    ok, msg = ideapad.set_feature(cap, "kbd_backlight", str(level))
    state["kbd_auto_level"] = level
    print(f"litaged [kbd-auto lux={lux:.0f}]: level={level} {msg}", flush=True)


def tick(profiles_dir: str, cap: capmod.Capability, last: tuple,
         cfg: configparser.ConfigParser | None = None,
         kbd_state: dict | None = None) -> tuple:
    ac = on_ac()
    prof = current_profile()
    key = (prof, ac)
    if cfg is not None:
        kbd_auto_tick(cfg, cap, kbd_state if kbd_state is not None else {})
    if key == last:
        return last
    preset = load_preset(profiles_dir, prof, ac)
    if preset:
        for line in apply_preset(preset, cap):
            print(f"litaged [{prof}/{'ac' if ac else 'bat'}]: {line}", flush=True)
    else:
        print(f"litaged [{prof}/{'ac' if ac else 'bat'}]: no preset, skipping", flush=True)
    return key


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="litaged")
    ap.add_argument("--once", action="store_true", help="apply once and exit")
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--profiles", default=None)
    ap.add_argument("--interval", type=float, default=None)
    ap.add_argument("--daemon", action="store_true", help="fork to background")
    args = ap.parse_args(argv)

    cfg = configparser.ConfigParser()
    if os.path.exists(args.config):
        cfg.read(args.config)
    profiles_dir = args.profiles or cfg.get("daemon", "profiles_dir", fallback=DEFAULT_PROFILES)
    interval = args.interval or cfg.getfloat("daemon", "interval", fallback=5.0)

    if args.daemon and os.fork() != 0:
        return 0

    cap = capmod.detect()
    if args.once:
        ac, prof = on_ac(), current_profile()
        preset = load_preset(profiles_dir, prof, ac)
        print(f"profile={prof} ac={ac} preset={preset or '{}'}")
        for line in apply_preset(preset, cap):
            print(line)
        return 0

    print(f"litaged: watching (interval={interval}s profiles={profiles_dir})", flush=True)
    last: tuple = (None, None)
    kbd_state: dict = {}
    try:
        while True:
            last = tick(profiles_dir, cap, last, cfg, kbd_state)
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
