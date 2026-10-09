"""Tema yöneticisi — siyah (saf #000) / koyu / gri / beyaz.

LibAdwaita renkleri seçicilerle değil, palet değişkenleriyle ezilir
(Gradience yöntemi): `@define-color window_bg_color ...` gibi tanımlar
APPLICATION öncelikli Gtk.CssProvider ile yüklenir ve pencere+kart+satır+
sidebar+popover dahil HER yeri boyar. Önceki sürümdeki `window { ... }`
seçiciler bu yüzden sadece üst kısımları değiştiriyordu.

Seçim `~/.config/litage/theme` dosyasında saklanır (GSettings'e bağımlı
değil — distro agnostic).
"""
from __future__ import annotations

import os

THEMES = ("saf-siyah", "koyu", "gri", "beyaz")
THEME_LABELS = {
    "saf-siyah": "Saf siyah (#000)",
    "koyu": "Koyu (Adwaita)",
    "gri": "Gri",
    "beyaz": "Beyaz",
}

# LibAdwaita paleti (adw 1.x stillerinde kullanılan adlar birebir)
PURE_BLACK_CSS = """
@define-color window_bg_color #000000;
@define-color window_fg_color #f2f2f2;
@define-color view_bg_color #000000;
@define-color view_fg_color #f2f2f2;
@define-color headerbar_bg_color #000000;
@define-color headerbar_fg_color #f2f2f2;
@define-color headerbar_backdrop_color #000000;
@define-color headerbar_shade_color rgba(255, 255, 255, 0.12);
@define-color card_bg_color #0e0e0e;
@define-color card_fg_color #f2f2f2;
@define-color card_shade_color rgba(255, 255, 255, 0.08);
@define-color dialog_bg_color #000000;
@define-color dialog_fg_color #f2f2f2;
@define-color popover_bg_color #141414;
@define-color popover_fg_color #f2f2f2;
@define-color popover_shade_color rgba(255, 255, 255, 0.08);
@define-color shade_color rgba(255, 255, 255, 0.08);
@define-color scrollbar_outline_color rgba(255, 255, 255, 0.25);
@define-color sidebar_bg_color #000000;
@define-color sidebar_fg_color #f2f2f2;
@define-color sidebar_backdrop_color #000000;
@define-color sidebar_shade_color rgba(255, 255, 255, 0.12);
@define-color secondary_sidebar_bg_color #050505;
@define-color secondary_sidebar_fg_color #f2f2f2;
@define-color secondary_sidebar_backdrop_color #050505;
@define-color secondary_sidebar_shade_color rgba(255, 255, 255, 0.12);
@define-color thumbnail_bg_color #0e0e0e;
@define-color thumbnail_fg_color #f2f2f2;
@define-color borders rgba(255, 255, 255, 0.14);
@define-color borders_backdrop rgba(255, 255, 255, 0.08);
"""

GRAY_CSS = """
@define-color window_bg_color #353537;
@define-color window_fg_color #f2f2f2;
@define-color view_bg_color #353537;
@define-color view_fg_color #f2f2f2;
@define-color headerbar_bg_color #2e2e30;
@define-color headerbar_fg_color #f2f2f2;
@define-color headerbar_backdrop_color #2e2e30;
@define-color headerbar_shade_color rgba(0, 0, 0, 0.25);
@define-color card_bg_color #424244;
@define-color card_fg_color #f2f2f2;
@define-color card_shade_color rgba(0, 0, 0, 0.15);
@define-color dialog_bg_color #353537;
@define-color dialog_fg_color #f2f2f2;
@define-color popover_bg_color #48484a;
@define-color popover_fg_color #f2f2f2;
@define-color popover_shade_color rgba(0, 0, 0, 0.15);
@define-color shade_color rgba(0, 0, 0, 0.18);
@define-color scrollbar_outline_color rgba(255, 255, 255, 0.3);
@define-color sidebar_bg_color #2b2b2d;
@define-color sidebar_fg_color #f2f2f2;
@define-color sidebar_backdrop_color #2b2b2d;
@define-color sidebar_shade_color rgba(0, 0, 0, 0.25);
@define-color secondary_sidebar_bg_color #323234;
@define-color secondary_sidebar_fg_color #f2f2f2;
@define-color secondary_sidebar_backdrop_color #323234;
@define-color secondary_sidebar_shade_color rgba(0, 0, 0, 0.25);
@define-color thumbnail_bg_color #424244;
@define-color thumbnail_fg_color #f2f2f2;
@define-color borders rgba(0, 0, 0, 0.35);
@define-color borders_backdrop rgba(0, 0, 0, 0.2);
"""

# "koyu" = saf Adwaita dark (override yok), "beyaz" = force-light + beyaz zemin
WHITE_CSS = """
@define-color window_bg_color #ffffff;
@define-color window_fg_color #1a1a1a;
@define-color view_bg_color #ffffff;
@define-color view_fg_color #1a1a1a;
@define-color headerbar_bg_color #f6f5f4;
@define-color headerbar_fg_color #1a1a1a;
@define-color card_bg_color #ffffff;
@define-color card_fg_color #1a1a1a;
@define-color sidebar_bg_color #f1f0ee;
@define-color sidebar_fg_color #1a1a1a;
@define-color popover_bg_color #ffffff;
@define-color popover_fg_color #1a1a1a;
"""


def config_path() -> str:
    return os.path.expanduser("~/.config/litage/theme")


def load() -> str:
    try:
        with open(config_path(), encoding="utf-8") as f:
            name = f.read().strip()
            if name in THEMES:
                return name
    except OSError:
        pass
    return "saf-siyah"


def save(name: str) -> None:
    if name not in THEMES:
        return
    try:
        os.makedirs(os.path.dirname(config_path()), exist_ok=True)
        with open(config_path(), "w", encoding="utf-8") as f:
            f.write(name)
    except OSError:
        pass


def css_for(name: str) -> str:
    if name == "saf-siyah":
        return PURE_BLACK_CSS
    if name == "gri":
        return GRAY_CSS
    if name == "beyaz":
        return WHITE_CSS
    return ""


def apply(name: str, style_manager=None, css_providers: dict | None = None) -> None:
    """Adw.StyleManager + Gtk.CssProvider uygula. GUI importları çağıran yapar."""
    from gi.repository import Adw, Gtk  # noqa: E402

    sm = style_manager or Adw.StyleManager.get_default()
    if name == "beyaz":
        sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    else:
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
    display = None
    try:
        from gi.repository import Gdk  # noqa: E402
        display = Gdk.Display.get_default()
    except Exception:
        display = None
    if display is None or css_providers is None:
        return
    for prov in css_providers.values():
        try:
            Gtk.StyleContext.remove_provider_for_display(display, prov)
        except Exception:
            pass
    css_providers.clear()
    css = css_for(name)
    if css:
        prov = Gtk.CssProvider()
        prov.load_from_string(css)
        # USER önceliği şart: ~/.config/gtk-4.0/gtk.css (Gradience vb.)
        # aynı öncelikte yüklenir, son eklenen kazanır = bizimki.
        # Sadece bu proses etkilenir, başka uygulamaya dokunmaz.
        Gtk.StyleContext.add_provider_for_display(
            display, prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        css_providers["theme"] = prov
