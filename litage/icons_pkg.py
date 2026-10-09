"""Uygulama ikonları — paket içi SVG'ler, ilk çalışta kullanıcı dizinine kurulur.

Neden? AppImage / kurumsuz repo çalıştırmada /usr/share'a yazılamaz; tepsi
(Ayatana, ayrı GTK3 süreç) ve .desktop dosyası ikonu bulamaz ve çark gösterir.
Bu modül `litage/icons/*.svg` dosyalarını
`~/.local/share/icons/hicolor/scalable/apps/` altına kopyalar (yoksa/farklıysa).
"""
from __future__ import annotations

import os
import shutil

APP_ICON = "dev.litage.app"
USER_DIR = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")


def _pkg_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


def _same(a: str, b: str) -> bool:
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


def ensure_user_icons() -> str | None:
    """İkonları kur, uygulama ikon adını döndür (olmazsa None)."""
    src_dir = _pkg_dir()
    if not os.path.isdir(src_dir):
        return None
    try:
        os.makedirs(USER_DIR, exist_ok=True)
    except OSError:
        return None
    ok = False
    for name in os.listdir(src_dir):
        if not name.endswith(".svg"):
            continue
        src = os.path.join(src_dir, name)
        dst = os.path.join(USER_DIR, name)
        try:
            if not os.path.exists(dst) or not _same(src, dst):
                shutil.copyfile(src, dst)
            if name == f"{APP_ICON}.svg":
                ok = True
        except OSError:
            continue
    return APP_ICON if ok else None
