"""Autostart yönetimi — XDG autostart (Cinnamon/GNOME/KDE hepsi okur).

~/.config/autostart/litage-gui.desktop dosyasını yazar/siler.
Sistem geneli istenirse /etc/xdg/autostart/litage-gui.desktop kullanılır
(install.sh --autostart-system ile).
"""
from __future__ import annotations

import os

DESKTOP_NAME = "litage-gui.desktop"
USER_DIR = os.path.expanduser("~/.config/autostart")
SYSTEM_DIR = "/etc/xdg/autostart"


def desktop_content(minimized: bool = True) -> str:
    args = " --minimized" if minimized else ""
    return (
        "[Desktop Entry]\n"
        "Name=Litage\n"
        "Comment=Lenovo power manager (tray)\n"
        f"Exec=litage-gui{args}\n"
        "Icon=computer-laptop\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=System;Settings;\n"
        "X-GNOME-Autostart-enabled=true\n"
        "X-Cinnamon-Autostart-enabled=true\n"
        "NoDisplay=false\n"
    )


def enable(minimized: bool = True, system: bool = False) -> tuple[bool, str]:
    d = SYSTEM_DIR if system else USER_DIR
    try:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, DESKTOP_NAME), "w", encoding="utf-8") as f:
            f.write(desktop_content(minimized))
        return True, f"autostart açıldı: {d}/{DESKTOP_NAME}"
    except OSError as e:
        return False, str(e)


def disable(system: bool = False) -> tuple[bool, str]:
    p = os.path.join(SYSTEM_DIR if system else USER_DIR, DESKTOP_NAME)
    try:
        os.remove(p)
        return True, f"autostart kapatıldı ({p})"
    except FileNotFoundError:
        return True, "autostart zaten kapalı"
    except OSError as e:
        return False, str(e)


def is_enabled() -> bool:
    return os.path.exists(os.path.join(USER_DIR, DESKTOP_NAME)) or os.path.exists(
        os.path.join(SYSTEM_DIR, DESKTOP_NAME))
