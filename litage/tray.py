"""litage-tray — GTK3 + Ayatana tepsi yardımcısı (ayrı süreç).

Neden ayrı süreç? AyatanaAppIndicator3 GTK 3.0 ister, ana arayüz GTK4
kullanır; ikisi aynı proseste yüklenemez. Bu yardımcı arka planda çalışır,
tepsi menüsünü gösterir, pencereyi açar, profil değiştirir.

Tekil çalışır: lockfile'daki pid yaşıyorsa hemen çıkar.
Kullanım: litage-tray [--no-fork]
"""
from __future__ import annotations

import os
import subprocess
import sys


def lock_path() -> str:
    try:
        uid = os.getuid()
    except AttributeError:
        uid = 0
    base = f"/run/user/{uid}"
    if not os.path.isdir(base):
        base = "/tmp"
    return os.path.join(base, "litage-tray.lock")


def already_running() -> bool:
    try:
        with open(lock_path(), encoding="utf-8") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def write_lock() -> None:
    try:
        with open(lock_path(), "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass


def remove_lock() -> None:
    try:
        os.remove(lock_path())
    except OSError:
        pass


def gui_command() -> list[str]:
    import shutil
    found = shutil.which("litage-gui")
    if found:
        return [found]
    app = os.environ.get("APPIMAGE")
    if app and os.path.exists(app):
        return [app]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.exists(os.path.join(here, "litage", "gui.py")):
        code = ("import sys; sys.path.insert(0, %r); "
                "from litage.gui import main; sys.exit(main())" % here)
        return [sys.executable, "-c", code]
    return []


def main(argv: list[str] | None = None) -> int:
    from litage.i18n import t
    if already_running():
        print(t("t.already"))
        return 0
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, GLib  # noqa: E402
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AI  # noqa: E402
    except (ImportError, ValueError) as e:
        print(t("t.no_ayatana", e=e), file=sys.stderr)
        return 1

    from litage import capabilities as capmod  # noqa: E402
    from litage import privileged as priv  # noqa: E402
    from litage.backends import ideapad, platform_profile  # noqa: E402

    cap = capmod.detect()
    write_lock()

    # paket içi ikonları kullanıcı dizinine kur (AppImage dahil), yoksa pil ikonu
    try:
        from litage import icons_pkg as _icons
        _icon = _icons.ensure_user_icons() or "battery-good"
    except Exception:
        _icon = "battery-good"

    ind = AI.Indicator.new("litage", _icon, AI.IndicatorCategory.HARDWARE)
    ind.set_status(AI.IndicatorStatus.ACTIVE)
    ind.set_title("Litage")

    def detail_line() -> str:
        parts = []
        pp = platform_profile.get(cap)
        if pp.get("active"):
            parts.append(f"{pp['active']}")
        try:
            from litage import utils as _u
            import glob as _g
            for hw in _g.glob("/sys/class/hwmon/hwmon*"):
                if _u.read_str(f"{hw}/name") == "k10temp":
                    tv = _u.read_str(f"{hw}/temp1_input")
                    if tv:
                        parts.append(f"{float(tv) / 1000:.0f}°C")
                    break
            b = _u.read_str("/sys/class/power_supply/BAT0/capacity")
            s = _u.read_str("/sys/class/power_supply/BAT0/status")
            if b:
                parts.append(f"%{b} {s or ''}".strip())
            pw = _u.read_str("/sys/class/power_supply/BAT0/power_now")
            try:
                if pw:
                    parts.append(f"{float(pw) / 1000000:.1f}W")
            except (ValueError, TypeError):
                pass
            try:
                mhz = _u.read_str(
                    "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq")
                if mhz:
                    parts.append(f"{int(mhz) // 1000}MHz")
            except (ValueError, TypeError):
                pass
        except (ValueError, TypeError, OSError):
            pass
        return " · ".join(parts) if parts else "Litage"

    menu = Gtk.Menu()
    header = Gtk.MenuItem(label=detail_line())
    header.set_sensitive(False)
    menu.append(header)
    menu.append(Gtk.SeparatorMenuItem())

    def _menu_show(_m):
        # menü her açılışta güncel durumu yaz
        header.set_label(detail_line())

    menu.connect("show", _menu_show)

    pp = platform_profile.get(cap)
    cur = pp.get("active")
    ready = {"v": False}
    first = None
    for prof in (pp.get("choices") or ["low-power", "balanced", "performance"]):
        if first is None:
            mi = Gtk.RadioMenuItem(label=t("t.power", prof=prof))
            first = mi
        else:
            mi = Gtk.RadioMenuItem(label=t("t.power", prof=prof), group=first)

        def _set(_m, prof=prof):
            if not ready["v"]:  # kurulumdaki set_active tetiklemesin
                return
            ok, msg = priv.run_set("platform_profile", prof)
            print(f"[tray] {msg}")

        mi.connect("activate", _set)
        if prof == cur:
            mi.set_active(True)
        menu.append(mi)
    GLib.timeout_add_seconds(1, lambda: ready.update(v=True) or False)

    if cap.has_ideapad:
        menu.append(Gtk.SeparatorMenuItem())
        ide = ideapad.get_all(cap)
        mi_cons = Gtk.CheckMenuItem(label=t("t.conservation"))
        mi_cons.set_active(ide.get("conservation") == "1")

        def _cons(m):
            if not ready["v"]:
                return
            ok, msg = priv.run_set("conservation", "on" if m.get_active() else "off")
            print(f"[tray] {msg}")

        mi_cons.connect("toggled", _cons)
        menu.append(mi_cons)

    menu.append(Gtk.SeparatorMenuItem())
    mi_open = Gtk.MenuItem(label=t("t.open"))

    def _open(_m):
        cmd = gui_command()
        if cmd:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             start_new_session=True)
        else:
            print(t("t.no_gui"), file=sys.stderr)

    mi_open.connect("activate", _open)
    menu.append(mi_open)
    mi_quit = Gtk.MenuItem(label=t("t.quit"))

    def _quit(_m):
        remove_lock()
        Gtk.main_quit()

    mi_quit.connect("activate", _quit)
    menu.append(mi_quit)
    menu.show_all()
    ind.set_menu(menu)
    print(t("t.running"))
    try:
        Gtk.main()
    finally:
        remove_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
