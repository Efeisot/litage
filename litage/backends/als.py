"""Ortam ışığı sensörü (ALS) backend — klavye oto-parlaklık için.

Yoga 14AKP10: iio:device2 (als), in_illuminance_raw × scale = lux.
"""
from __future__ import annotations

import glob

from .. import utils


def find_als() -> str | None:
    for dev in sorted(glob.glob("/sys/bus/iio/devices/iio:device*")):
        name = (utils.read_str(f"{dev}/name") or "").lower()
        if "als" in name or "light" in name or "illuminance" in name:
            if utils.read_str(f"{dev}/in_illuminance_raw") is not None:
                return dev
        # ada bakmadan ham dosyası olan ilk aday
        if utils.read_str(f"{dev}/in_illuminance_raw") is not None:
            return dev
    return None


def lux(dev: str | None = None) -> float | None:
    dev = dev or find_als()
    if not dev:
        return None
    raw = utils.read_str(f"{dev}/in_illuminance_raw")
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    scale = utils.read_str(f"{dev}/in_illuminance_scale")
    try:
        value *= float(scale) if scale else 1.0
    except ValueError:
        pass
    return value


def kbd_level_for_lux(lux_value: float, dark_below: float = 30.0,
                      bright_above: float = 150.0) -> int:
    """Karanlıkta parlak (2), aydınlıkta kapalı (0), arada kısık (1)."""
    if lux_value < dark_below:
        return 2
    if lux_value > bright_above:
        return 0
    return 1
