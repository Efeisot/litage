"""privileged (CLI çözümleme + teşhis) ve themes testleri — donanımsız."""
from __future__ import annotations

import os

from litage import privileged as priv
from litage import themes as theme_mod


def test_cli_command_resolves():
    # kurulu litage | AppImage kendisi | repo fallback (mutlak yollu -c)
    cmd = priv.cli_command()
    assert cmd is not None and len(cmd) >= 1
    assert (len(cmd) == 1 and cmd[0].endswith("litage")) or cmd[1:] == ["cli"] or cmd[1] == "-c"


def test_diagnose_keys():
    d = priv.diagnose()
    for k in ("cli", "pkexec", "policy", "udev", "agent_bin", "agent_running"):
        assert k in d, k
    assert isinstance(d["agent_running"], bool)


def test_doctor_text_safe():
    t = priv.doctor_text()
    assert "CLI" in t and "agent" in t


def test_run_set_rejects_garbage_safely():
    # pkexec'e gitmeden önce CLI yoksa kullanıcı mesajı; varsa polkit sorar.
    # Burada sadece dönüş tipi kontratı test edilir (yazma YOK).
    import shutil
    if shutil.which("litage") is None and priv._is_appimage() is None:
        # repo fallback var -> komut kurulur ama pkexec headless'te soramaz;
        # yine de tuple dönmeli
        ok, msg = priv.run_set("platform_profile", "bogus-value-xyz", timeout=3)
        assert isinstance(ok, bool) and isinstance(msg, str)


def test_themes_roundtrip(tmp_path=None):
    assert set(theme_mod.THEMES) == {"saf-siyah", "koyu", "gri", "beyaz"}
    assert "000" in theme_mod.THEME_LABELS["saf-siyah"]
    assert "#000000" in theme_mod.PURE_BLACK_CSS
    # kayıt/okuma ev dizinine yazar — sadece okuma yolu test edilir
    assert theme_mod.load() in theme_mod.THEMES


def test_theme_css_balanced():
    for css in (theme_mod.PURE_BLACK_CSS, theme_mod.GRAY_CSS, theme_mod.WHITE_CSS):
        assert css.count("{") == css.count("}"), "CSS braces"
        assert "@define-color window_bg_color" in css


def test_theme_covers_all_surfaces():
    # satır/kart/sidebar/popover boyanmazsa kullanıcı "sadece üst değişti" der
    css = theme_mod.PURE_BLACK_CSS
    for var in ("window_bg_color", "card_bg_color", "sidebar_bg_color",
                "popover_bg_color", "view_bg_color", "headerbar_bg_color"):
        assert f"@define-color {var}" in css, var
    assert "#000000" in css  # saf siyah gerçekten siyah


def test_als_and_kbd_levels():
    from litage.backends import als as _als
    dev = _als.find_als()
    assert dev is not None  # bu makinede ALS var
    v = _als.lux()
    assert v is not None and v >= 0
    assert _als.kbd_level_for_lux(5) == 2
    assert _als.kbd_level_for_lux(500) == 0
    assert _als.kbd_level_for_lux(80) == 1


def test_prefs_close_action_roundtrip():
    from litage import prefs as _p
    bak = None
    try:
        with open(_p.PATH, encoding="utf-8") as f:
            bak = f.read()
    except OSError:
        pass
    try:
        assert _p.get_close_action() in ("tray", "quit")
        _p.set_close_action("quit")
        assert _p.get_close_action() == "quit"
        _p.set_close_action("tray")
        assert _p.get_close_action() == "tray"
    finally:
        try:
            if bak is None:
                __import__("os").remove(_p.PATH)
            else:
                with open(_p.PATH, "w", encoding="utf-8") as f:
                    f.write(bak)
        except OSError:
            pass


def test_icons_pkg():
    from litage import icons_pkg as _i
    assert _i.ensure_user_icons() == "dev.litage.app"


def test_i18n_parity():
    from litage import i18n as _i
    problems = _i.check_parity()
    assert not problems, problems[:5]
    assert _i.t("no.such.key") == "no.such.key"
    # format hatası güvenli düşmeli
    assert isinstance(_i.t("d.battery_line", cap=80), str)


def test_no_t_shadow():
    # `t` i18n fonksiyonunu gölgeleyen yerel atama olmamalı (UnboundLocalError verir)
    import re
    for path in ("litage/gui.py", "litage/tray.py"):
        src = open(path, encoding="utf-8").read()
        bad = [ln for ln in src.splitlines()
               if re.search(r"(^|[^_.a-zA-Z])t\s*=(?!=)", ln)]
        assert not bad, f"{path}: {bad[:3]}"
