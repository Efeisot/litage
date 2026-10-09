"""Kullanıcı tercihleri — ~/.config/litage/settings.ini (ini, GSettings yok).

[ui]
close_action = tray | quit   # kapat düğmesi: tepsiye küçült / tümden çık
"""
from __future__ import annotations

import configparser
import os

PATH = os.path.expanduser("~/.config/litage/settings.ini")
CLOSE_LABELS = {
    "tray": "Tepsiye küçült (arka planda çalışır)",
    "quit": "Tümden çık (tray de kapanır)",
}


def _load() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    try:
        cfg.read(PATH, encoding="utf-8")
    except OSError:
        pass
    return cfg


def get_close_action() -> str:
    try:
        v = _load().get("ui", "close_action", fallback="tray").strip()
    except (configparser.Error, OSError):
        v = "tray"
    return v if v in CLOSE_LABELS else "tray"


def set_close_action(value: str) -> None:
    if value not in CLOSE_LABELS:
        return
    cfg = _load()
    if not cfg.has_section("ui"):
        cfg.add_section("ui")
    cfg.set("ui", "close_action", value)
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH, "w", encoding="utf-8") as f:
            cfg.write(f)
    except OSError:
        pass
