"""litage-gui — LLT (LenovoLegionToolkit WPF) tarzı kapsamlı arayüz.

LLT kabuğu: ikonlu sol sidebar + sağ içerik + toast + tepsi.
- Desteklenmeyen bölümler GİZLENMEZ, kilitli gösterilir (kullanıcı isteği):
  Fan Eğrisi / Legion / Harici GPU bu Yoga'da gri + "bu cihazda yok" rozetiyle
  durur, tıklanmaz. Legion/NVIDIA donanımda otomatik açılır.
- Yazmalar pkexec + çözümlenmiş CLI (litage/privileged.py) üzerinden; polkit
  agent yoksa Sistem sayfası kurulumu yönlendirir.
- Sağ tık: kart/satırlarda bağlam menüsü (kopyala/yenile/terminalde uygula).
- Temalar: saf siyah (#000) / koyu / gri / beyaz (Ayarlar'dan, kalıcı).

Kullanım: litage-gui [--minimized] [--page NAME]
"""
from __future__ import annotations

import os
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    minimized = "--minimized" in argv
    start_page = None
    if "--page" in argv:
        try:
            start_page = argv[argv.index("--page") + 1]
        except IndexError:
            pass

    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_version("Pango", "1.0")
    from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

    from litage import capabilities as capmod  # noqa: E402
    from litage import privileged as priv  # noqa: E402
    from litage import themes as theme_mod  # noqa: E402
    from litage.backends import (  # noqa: E402
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

    cap = capmod.detect()
    display = Gdk.Display.get_default()
    icon_theme = Gtk.IconTheme.get_for_display(display)
    # geliştirme ağacındaki özel ikonlar (kurulu sistemde hicolor'dan gelir)
    _dev_icons = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "packaging", "icons")
    if os.path.isdir(_dev_icons):
        icon_theme.add_search_path(_dev_icons)

    def pick(*names: str, fallback: str = "computer-symbolic") -> str:
        for n in names:
            try:
                if icon_theme.has_icon(n):
                    return n
            except Exception:
                continue
        return fallback

    ICONS = {
        "dashboard": pick("emblem-system-symbolic", "computer-symbolic"),
        "battery": pick("battery-good-symbolic", "battery-symbolic"),
        "keyboard": pick("litage-keyboard-symbolic", "input-keyboard-symbolic"),
        "fan": pick("litage-fan-symbolic", "emblem-system-symbolic"),
        "cpu": pick("litage-cpu-symbolic", "computer-symbolic"),
        "temp": pick("litage-thermometer-symbolic", "emblem-system-symbolic"),
        "power": pick("power-profile-performance-symbolic", "ac-adapter-symbolic"),
        "network": pick("network-wireless-symbolic", "emblem-system-symbolic"),
        "display": pick("video-display-symbolic", "computer-symbolic"),
        "settings": pick("preferences-system-symbolic", "emblem-system-symbolic"),
        "about": pick("help-about-symbolic", "dialog-information-symbolic"),
        "automation": pick("appointment-soon-symbolic", "emblem-system-symbolic"),
        "system": pick("computer-symbolic", "emblem-system-symbolic"),
        "legion": pick("litage-cpu-symbolic", "computer-symbolic"),
        "dgpu": pick("video-card-symbolic", "computer-symbolic"),
        "mic": pick("audio-input-microphone-symbolic"),
        "camera": pick("camera-web-symbolic"),
        "bt": pick("bluetooth-symbolic"),
        "lock": pick("dialog-error-symbolic"),
        "copy": pick("edit-copy-symbolic"),
        "refresh": pick("view-refresh-symbolic"),
    }

    css_providers: dict = {}
    theme_mod.apply(theme_mod.load(), css_providers=css_providers)

    toast_overlay: Adw.ToastOverlay | None = None

    def toast(text: str):
        print(f"[litage-gui] {text}")
        if toast_overlay is not None:
            toast_overlay.add_toast(Adw.Toast(title=text[:220]))

    # ---------------- sağ tık menüsü ----------------
    def attach_menu(widget: Gtk.Widget, items: list[tuple[str, callable]]):
        """Sağ tık -> Gtk.PopoverMenu. items: [(etiket, callback)]."""
        menu = Gio.Menu()
        actions: dict[str, callable] = {}
        for i, (label, cb) in enumerate(items):
            act_name = f"ctx{i}_{abs(id(widget)) % 100000}"
            menu.append(label, f"win.{act_name}")
            actions[act_name] = cb

        def _add_actions(w: Gtk.Widget):
            for name, cb in actions.items():
                act = Gio.SimpleAction(name=name)

                def _on(_a, _p, cb=cb):
                    cb()

                act.connect("activate", _on)
                w.add_action(act)

        pop = Gtk.PopoverMenu(menu_model=menu)
        pop.set_parent(widget)
        gesture = Gtk.GestureClick(button=3)

        def _pressed(_g, _n, _x, _y):
            # aksiyonları pencereye ekle (tek sefer)
            win = widget.get_root()
            if win is not None and hasattr(win, "add_action"):
                try:
                    _add_actions(win)
                except Exception:
                    pass
            pop.set_pointing_to(None)
            pop.popup()

        gesture.connect("pressed", _pressed)
        widget.add_controller(gesture)
        return pop

    def copy_text(text: str):
        try:
            d = Gdk.Display.get_default()
            if d is not None:
                d.get_clipboard().set(text)
                toast("kopyalandı")
        except Exception as e:
            toast(f"kopyalanamadı: {e}")

    # ---------------- ayrıcalıklı yazma (toplu: tek şifre) ----------------
    # Kontroller değişikliği beklemeye alır (ui["pending"]), Kaydet çubuğu
    # tek pkexec ile hepsini uygular. Böylece 10 ayar = 1 şifre.
    ui_state = {"pending": {}, "btn_save": None, "btn_cancel": None,
                "save_count": None}

    def savebar_update():
        n = len(ui_state["pending"])
        if ui_state["save_count"] is not None:
            ui_state["save_count"].set_label(str(n) if n else "")
            ui_state["save_count"].set_visible(n > 0)
        for key in ("btn_save", "btn_cancel"):
            btn = ui_state[key]
            if btn is not None:
                btn.set_sensitive(n > 0)
                btn.set_opacity(1.0 if n > 0 else 0.45)

    def stage(feature: str, value: str):
        ui_state["pending"][feature] = value
        savebar_update()
        toast(f"bekliyor: {feature}={value} (Kaydet'e bas)")

    def save_discard():
        ui_state["pending"].clear()
        savebar_update()
        refresh_current()

    def save_apply():
        pairs = list(ui_state["pending"].items())
        if not pairs:
            return
        ok, msg = priv.run_many(pairs)
        toast(msg)
        ui_state["pending"].clear()
        savebar_update()
        if ok:
            GLib.timeout_add_seconds(1, refresh_current)

    def privileged_set(feature: str, value: str):
        ok, msg = priv.run_set(feature, value)
        toast(msg)
        if ok:
            GLib.timeout_add_seconds(1, refresh_current)

    # (refresh_current aşağıda, sayfa kayıtlarıyla birlikte tanımlı)

    # ---------------- satır/kart yardımcıları ----------------
    def row(title: str, widget, subtitle: str = "",
            icon: str | None = None) -> Adw.ActionRow:
        r = Adw.ActionRow(title=title, subtitle=subtitle)
        if icon:
            img = Gtk.Image.new_from_icon_name(icon)
            r.add_prefix(img)
        r.add_suffix(widget)
        return r

    def switch_row(title: str, active: bool, feature: str, subtitle: str = "",
                   icon: str | None = None,
                   terminal_hint: str | None = None) -> Adw.SwitchRow:
        sr = Adw.SwitchRow(title=title, subtitle=subtitle, active=bool(active))
        if icon:
            sr.add_prefix(Gtk.Image.new_from_icon_name(icon))
        batch_ready = {"ready": False}

        def _on(_r, _pspec):
            if not batch_ready["ready"]:
                return
            stage(feature, "on" if sr.get_active() else "off")

        sr.connect("notify::active", _on)
        GLib.idle_add(lambda: batch_ready.update(ready=True) or False)
        hint = terminal_hint or f"sudo litage set {feature} on|off"
        attach_menu(sr, [
            ("Değeri kopyala", lambda: copy_text(f"{feature}={'on' if sr.get_active() else 'off'}")),
            ("Terminalde uygula", lambda: copy_text(hint)),
            ("Yenile", lambda: refresh_current()),
        ])
        return sr

    def combo_row(title: str, current: str | None, options: list[str],
                  feature: str, subtitle: str = "",
                  icon: str | None = None) -> Adw.ComboRow:
        cr = Adw.ComboRow(title=title, subtitle=subtitle,
                          model=Gtk.StringList.new(options or ["-"]))
        if icon:
            cr.add_prefix(Gtk.Image.new_from_icon_name(icon))
        state_flag = {"ready": False}
        if current in (options or []):
            cr.set_selected(options.index(current))

        def _on(_r, _pspec):
            # kurulum anındaki programatik seçimde tetiklenme engellenir
            if not state_flag["ready"]:
                return
            sel = cr.get_selected()
            if options:
                stage(feature, options[sel])

        cr.connect("notify::selected", _on)
        # hazır bayrağını event-loop sonrasına bırak ki init set_selected işlemesin
        GLib.idle_add(lambda: state_flag.update(ready=True) or False)
        attach_menu(cr, [
            ("Değeri kopyala", lambda: copy_text(f"{feature}={options[cr.get_selected()]}" if options else "")),
            ("Yenile", lambda: refresh_current()),
        ])
        return cr

    def sensor_card(icon: str, value: str, label: str,
                    frac: float | None = None,
                    level_class: str | None = None) -> Gtk.Widget:
        # sabit iskelet: çubuk yoksa bile yeri korunur -> kutular eşit boylanır
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3,
                      halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_size_request(-1, 118)
        img = Gtk.Image.new_from_icon_name(icon)
        img.set_pixel_size(22)
        box.append(img)
        big = Gtk.Label(label=value)
        big.add_css_class("title-3")
        big.set_ellipsize(Pango.EllipsizeMode.END)
        if level_class:
            big.add_css_class(level_class)
        box.append(big)
        bar = Gtk.LevelBar(min_value=0, max_value=1,
                           value=max(0.0, min(1.0, frac)) if frac is not None else 0)
        bar.set_size_request(104, -1)
        if frac is None:
            bar.set_opacity(0)
        box.append(bar)
        sub = Gtk.Label(label=label)
        sub.add_css_class("dim-label")
        sub.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(sub)
        box.add_css_class("card")
        attach_menu(box, [
            ("Değeri kopyala", lambda: copy_text(f"{label}: {value}")),
        ])
        return box

    def temp_class(celsius: float | None) -> tuple[str | None, float | None]:
        """Sıcaklık -> (css sınıfı, levelbar oranı)."""
        if celsius is None:
            return None, None
        frac = max(0.0, min(1.0, (celsius - 20) / 80))
        if celsius < 55:
            return "success", frac
        if celsius < 75:
            return None, frac
        if celsius < 90:
            return "warning", frac
        return "error", frac

    PROFILE_DOT = {
        "low-power": "success",
        "balanced": "accent",
        "performance": "warning",
        "balanced-performance": "accent",
        "custom": "accent",
    }

    class HistoryChart(Gtk.DrawingArea):
        """Canlı çizgi grafiği: halka tampon + ızgara + dolgu + min/max."""
        def __init__(self, title: str, unit: str,
                     color: tuple[float, float, float] = (0.3, 0.77, 0.54),
                     capacity: int = 90):
            super().__init__()
            self._title = title
            self._unit = unit
            self._color = color
            self._cap = capacity
            self._samples: list[float] = []
            self.set_content_height(132)
            self.set_draw_func(self._draw)

        def push(self, v) -> None:
            try:
                f = float(v)
            except (ValueError, TypeError):
                return
            self._samples.append(f)
            self._samples = self._samples[-self._cap:]
            self.queue_draw()

        def _draw(self, _area, cr, w: int, h: int) -> None:
            pad_l, pad_r, pad_t, pad_b = 8, 8, 24, 18
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.22)
            cr.set_line_width(1)
            for i in range(4):
                y = pad_t + (h - pad_t - pad_b) * i / 3
                cr.move_to(pad_l, y)
                cr.line_to(w - pad_r, y)
                cr.stroke()
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(11)
            cr.set_source_rgba(0.75, 0.75, 0.75, 1)
            cr.move_to(pad_l, 15)
            cr.show_text(self._title)
            cur = self._samples[-1] if self._samples else None
            if cur is not None:
                txt = f"{cur:.0f}{self._unit}"
                adv = cr.text_extents(txt).x_advance
                cr.move_to(w - pad_r - adv, 15)
                cr.show_text(txt)
            if len(self._samples) < 2:
                cr.set_font_size(10)
                cr.set_source_rgba(0.6, 0.6, 0.6, 1)
                cr.move_to(pad_l, pad_t + 20)
                cr.show_text("veri toplanıyor…")
                return
            lo, hi = min(self._samples), max(self._samples)
            if hi - lo < 1e-6:
                hi = lo + 1

            def X(i: int) -> float:
                return pad_l + (w - pad_l - pad_r) * i / max(1, len(self._samples) - 1)

            def Y(v: float) -> float:
                return pad_t + (1 - (v - lo) / (hi - lo)) * (h - pad_t - pad_b)

            n = len(self._samples)
            cr.set_source_rgba(*self._color, 0.20)
            cr.move_to(X(0), h - pad_b)
            for i, v in enumerate(self._samples):
                cr.line_to(X(i), Y(v))
            cr.line_to(X(n - 1), h - pad_b)
            cr.close_path()
            cr.fill()
            cr.set_source_rgb(*self._color)
            cr.set_line_width(2)
            cr.set_line_join(1)
            cr.move_to(X(0), Y(self._samples[0]))
            for i, v in enumerate(self._samples[1:], 1):
                cr.line_to(X(i), Y(v))
            cr.stroke()
            cr.arc(X(n - 1), Y(self._samples[-1]), 3.2, 0, 6.2832)
            cr.fill()
            cr.set_font_size(9)
            cr.set_source_rgba(0.62, 0.62, 0.62, 1)
            cr.move_to(pad_l, h - 4)
            cr.show_text(f"min {lo:.0f}  max {hi:.0f}{self._unit}")

    def start_sampler() -> None:
        """2 sn'de bir hwmon okuyup açık grafikleri besler (tek örnekleyici)."""
        if ui.get("sampling"):
            return
        ui["sampling"] = True
        from litage import utils as _u
        import glob as _g

        def temp_by_name(want: str):
            for hw in _g.glob("/sys/class/hwmon/hwmon*"):
                if _u.read_str(f"{hw}/name") == want:
                    try:
                        return float(_u.read_str(f"{hw}/temp1_input")) / 1000
                    except (ValueError, TypeError):
                        return None
            return None

        def tick():
            ch = ui.get("charts", {})
            if not ch:
                return True
            v = temp_by_name("k10temp")
            if v is not None and "cpu" in ch:
                ch["cpu"].push(v)
            v = temp_by_name("amdgpu")
            if v is not None and "gpu" in ch:
                ch["gpu"].push(v)
            try:
                mhz = int(_u.read_str(
                    "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq") or 0) // 1000
            except (ValueError, TypeError):
                mhz = 0
            if mhz and "mhz" in ch:
                ch["mhz"].push(mhz)
            return True

        tick()
        GLib.timeout_add_seconds(2, tick)

    def locked_row(title: str, reason: str, icon: str) -> Adw.ActionRow:
        r = Adw.ActionRow(title=title, subtitle=reason)
        r.add_prefix(Gtk.Image.new_from_icon_name(icon))
        badge = Gtk.Label(label="YOK")
        badge.add_css_class("dim-label")
        r.add_suffix(badge)
        r.set_sensitive(False)
        return r

    # ---------------- sayfa içerikleri ----------------
    state = {"current": "dashboard"}

    def page_scroll(child: Gtk.Widget) -> Gtk.Widget:
        sc = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        sc.set_child(child)
        return sc

    def build_dashboard() -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        cpu = cpufreq.get()
        sen = sensors.get()
        # hero kart: makine + profil rozeti + pil (LLT Dashboard başlığı gibi)
        pp0 = platform_profile.get(cap)
        bat0 = battery.get(cap)
        hero = Gtk.Box(spacing=14)
        hero.set_margin_top(2)
        hero.set_margin_bottom(6)
        hero.set_margin_start(4)
        hero.set_margin_end(4)
        micon = Gtk.Image.new_from_icon_name(pick("computer-symbolic"))
        micon.set_pixel_size(44)
        hero.append(micon)
        mbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        mtitle = Gtk.Label(label=cap.product_version or cap.product_name or "Lenovo",
                           xalign=0)
        mtitle.add_css_class("title-3")
        mbox.append(mtitle)
        msub = Gtk.Label(label=f"{cap.vendor} · BIOS {cap.bios_version}", xalign=0)
        msub.add_css_class("dim-label")
        mbox.append(msub)
        hero.append(mbox)
        hero.append(Gtk.Box(hexpand=True))
        prof = pp0.get("active") or "?"
        dot = Gtk.Label(label="●")
        dot.add_css_class(PROFILE_DOT.get(prof, "accent"))
        hero.append(dot)
        pbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        plab = Gtk.Label(label=prof, xalign=1)
        plab.add_css_class("title-4")
        pbox.append(plab)
        blab = Gtk.Label(
            label=f"Pil %{bat0.get('capacity', '?')} · {bat0.get('status', '')}",
            xalign=1)
        blab.add_css_class("dim-label")
        pbox.append(blab)
        hero.append(pbox)
        hero.add_css_class("card")
        box.append(hero)

        # sensör kartları: CPU + ilk 4 sıcaklık = tam 5 kutu, yan yana, eşit
        flow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                       homogeneous=True)
        from litage import utils as _u
        import glob as _g
        shown = 0
        for hw in sorted(_g.glob("/sys/class/hwmon/hwmon*")):
            name = _u.read_str(f"{hw}/name") or "?"
            t = _u.read_str(f"{hw}/temp1_input")
            if t and shown < 4:
                try:
                    c = float(t) / 1000
                except ValueError:
                    continue
                cls, frac = temp_class(c)
                flow.append(sensor_card(ICONS["temp"], f"{c:.0f}°C", name,
                                        frac=frac, level_class=cls))
                shown += 1
        if cpu.get("cpu_mhz_avg"):
            flow.prepend(sensor_card(ICONS["cpu"], f"{cpu['cpu_mhz_avg']} MHz", "CPU"))
        grp_s = Adw.PreferencesGroup(title="Sensörler")
        grp_s.add(flow)
        box.append(grp_s)

        # grafikler (canlı çizgi grafikler — YAN YANA)
        grp_g = Adw.PreferencesGroup(title="Grafikler",
                                     description="canlı · 2 sn aralık · sağ tık menüsü var")
        chbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                        homogeneous=True)
        ch_cpu = HistoryChart("CPU sıcaklığı", "°C", (0.30, 0.77, 0.54))
        ch_gpu = HistoryChart("GPU sıcaklığı", "°C", (0.47, 0.68, 0.93))
        ch_mhz = HistoryChart("CPU frekansı", " MHz", (0.95, 0.65, 0.20))
        for _ch in (ch_cpu, ch_gpu, ch_mhz):
            attach_menu(_ch, [("Yenile", lambda: refresh_current())])
            chbox.append(_ch)
        grp_g.add(chbox)
        ui["charts"] = {"cpu": ch_cpu, "gpu": ch_gpu, "mhz": ch_mhz}
        box.append(grp_g)

        # güç grubu — segmentli güç modu (LLT PowerModeControl tarzı)
        grp = Adw.PreferencesGroup(title="Güç", description="Fn+Q ile aynı profil")
        pp = platform_profile.get(cap)
        choices = pp.get("choices") or ["low-power", "balanced", "performance"]
        if pp.get("choices") or cap.platform_profiles:
            # segmentli güç modu (bağlantılı toggle butonlar — sürüm bağımsız)
            segbox = Gtk.Box(spacing=0)
            segbox.add_css_class("linked")
            seg_btns: list[Gtk.ToggleButton] = []
            for _c in choices:
                tb = Gtk.ToggleButton(label=_c)
                seg_btns.append(tb)
                segbox.append(tb)

            seg_ready = {"ready": False}

            def _seg_on(toggled, _all=seg_btns):
                if not seg_ready["ready"] or not toggled.get_active():
                    return
                for b in _all:
                    if b is not toggled:
                        b.set_active(False)
                stage("platform_profile", toggled.get_label())

            for tb in seg_btns:
                tb.connect("toggled", _seg_on)
            try:
                seg_btns[choices.index(pp.get("active"))].set_active(True)
            except (ValueError, IndexError):
                pass
            GLib.idle_add(lambda: seg_ready.update(ready=True) or False)
            r = Adw.ActionRow(title="Güç modu", subtitle="Fn+Q ile aynı profil")
            r.add_prefix(Gtk.Image.new_from_icon_name(ICONS["power"]))
            r.add_suffix(segbox)
            grp.add(r)
            for prov, p in pp.get("providers", {}).items():
                rr = Adw.ActionRow(title=f"sağlayıcı: {p.get('driver')}",
                                   subtitle=f"{p.get('profile')}")
                rr.add_prefix(Gtk.Image.new_from_icon_name(ICONS["power"]))
                grp.add(rr)
        if cpu.get("governors"):
            grp.add(combo_row("CPU governor", cpu.get("governor"), cpu["governors"],
                              "governor", icon=ICONS["cpu"]))
        if cpu.get("epp_available"):
            grp.add(combo_row("Enerji tercihi (EPP)", cpu.get("epp"),
                              cpu["epp_available"], "epp", icon=ICONS["power"]))
        if cpu.get("boost") is not None:
            grp.add(switch_row("CPU Boost", cpu.get("boost") == "1", "boost",
                               icon=ICONS["power"]))
        box.append(grp)

        # Lenovo grubu
        if cap.has_ideapad:
            ide = ideapad.get_all(cap)
            g = Adw.PreferencesGroup(title="Lenovo")
            g.add(switch_row("Pil koruma", ide.get("conservation") == "1",
                             "conservation", "Şarjı %60/%80'de sınırla",
                             icon=ICONS["battery"]))
            g.add(switch_row("Fn-Lock", ide.get("fn_lock") == "1", "fn_lock",
                             "Fn tuş kilidi", icon=ICONS["keyboard"]))
            g.add(switch_row("Kamera", ide.get("camera_power") == "1", "camera_power",
                             icon=ICONS["camera"]))
            g.add(switch_row("Kapalıyken USB şarj", ide.get("usb_charging") == "1",
                             "usb_charging", icon=ICONS["power"]))
            g.add(combo_row("Fan modu", str(ide.get("fan_mode")), ["0", "1", "2"],
                            "fan_mode", icon=ICONS["fan"]))
            maxb = cap.kbd_backlight_max or 2
            g.add(combo_row("Klavye ışığı", str(ide.get("kbd_backlight")),
                            [str(i) for i in range(maxb + 1)], "kbd_backlight",
                            icon=ICONS["keyboard"]))
            box.append(g)

        # TLP grubu
        if cap.has_tlp:
            g = Adw.PreferencesGroup(title="TLP",
                                     description="Tek opsiyonel bağımlılık")
            sys_info = tlp.system_info()
            g.add(row("TLP profili",
                      Gtk.Label(label=f"{sys_info.get('tlp_profile', '?')} / "
                                      f"{sys_info.get('power_source', '?')}"),
                      icon=ICONS["power"]))
            bat = tlp.battery_info()
            if bat.get("threshold_start") is not None:
                g.add(row("Şarj eşiği",
                          Gtk.Label(label=f"{bat['threshold_start']}–{bat.get('threshold_end')}%"),
                          icon=ICONS["battery"]))
            box.append(g)

        # kablosuz
        rf = rfkill.get()
        if rf.get("devices"):
            g = Adw.PreferencesGroup(title="Bağlantı")
            if cap.has_wifi_rfkill:
                g.add(switch_row("Wi-Fi", True, "wifi", icon=ICONS["network"]))
            if cap.has_bt_rfkill:
                g.add(switch_row("Bluetooth", True, "bluetooth", icon=ICONS["bt"]))
            box.append(g)
        return page_scroll(box)

    def build_battery() -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(16)
        outer.set_margin_start(16)
        outer.set_margin_end(16)
        bat = battery.get(cap)
        pct = bat.get("capacity", "?")
        st = bat.get("status", "")
        header = Gtk.Box(spacing=16)
        icon = Gtk.Image.new_from_icon_name(ICONS["battery"])
        icon.set_pixel_size(64)
        header.append(icon)
        tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        big = Gtk.Label(label=f"%{pct}")
        big.add_css_class("title-2")
        try:
            pf = float(pct)
            big.add_css_class("success" if pf >= 50 else ("warning" if pf >= 20 else "error"))
        except (ValueError, TypeError):
            pass
        tbox.append(big)
        sub = Gtk.Label(label=str(st))
        sub.add_css_class("dim-label")
        tbox.append(sub)
        try:
            lvl = Gtk.LevelBar(min_value=0, max_value=100, value=float(pct))
            lvl.set_size_request(220, -1)
            tbox.append(lvl)
        except (ValueError, TypeError):
            pass
        header.append(tbox)
        header.set_halign(Gtk.Align.CENTER)
        outer.append(header)

        grp = Adw.PreferencesGroup(title="İstatistik")
        labels = {
            "status": ("Durum", None), "capacity": ("Kapasite (%)", None),
            "capacity_level": ("Seviye", None),
            "charge_type_active": ("Şarj tipi", ICONS["power"]),
            "charge_types_raw": ("Tipler", None), "cycle_count": ("Çevrim", None),
            "energy_full": ("Dolu (µWh)", None),
            "energy_full_design": ("Tasarım (µWh)", None),
            "energy_now": ("Anlık (µWh)", None), "power_now": ("Güç (µW)", None),
            "voltage_now": ("Voltaj (µV)", None), "technology": ("Teknoloji", None),
            "manufacturer": ("Üretici", None), "model_name": ("Model", None),
        }
        for k, (label, ic) in labels.items():
            if bat.get(k) is not None:
                r = row(label, Gtk.Label(label=str(bat[k])), icon=ic)
                attach_menu(r, [("Değeri kopyala",
                                 lambda v=str(bat[k]): copy_text(v))])
                grp.add(r)
        up = bat.get("upower", {})
        for k in ("percentage", "state", "capacity", "energy-rate"):
            if up.get(k):
                grp.add(row(f"upower {k}", Gtk.Label(label=str(up[k])),
                            icon=ICONS["battery"]))
        # sağlık
        try:
            full = float(bat.get("energy_full") or 0)
            design = float(bat.get("energy_full_design") or 0)
            if full > 0 and design > 0:
                grp.add(row("Pil sağlığı",
                            Gtk.Label(label=f"%{full / design * 100:.1f}"),
                            subtitle="dolu / tasarım",
                            icon=ICONS["battery"]))
        except (ValueError, TypeError):
            pass
        outer.append(grp)
        if cap.has_tlp:
            g2 = Adw.PreferencesGroup(title="TLP şarj eşiği")
            info = tlp.battery_info()
            for line in (info.get("lines") or [])[:8]:
                g2.add(Adw.ActionRow(title=line))
            hint = Adw.ActionRow(title="Eşik değiştir (polkit)",
                                 subtitle="Örn: 20–80 için tıklayıp şifrenizi girin")
            btn = Gtk.Button(label="Uygula: 20–80")
            btn.connect("clicked", lambda _b: privileged_set("tlp_charge", "20 80"))
            hint.add_suffix(btn)
            g2.add(hint)
            outer.append(g2)
        return page_scroll(outer)

    def build_keyboard() -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        grp = Adw.PreferencesGroup(title="Klavye", description="ideapad VPC")
        if cap.has_ideapad:
            from litage import cli as _cli
            auto_now = (_cli.get_daemon_kbd_auto() or "off").lower() in ("true", "on", "1")
            try:
                from litage.backends import als as _als
                als_lux = _als.lux()
                has_als = _als.find_als() is not None
            except ImportError:
                als_lux, has_als = None, False
            if has_als:
                grp.add(switch_row(
                    "Otomatik parlaklık", auto_now, "kbd_auto",
                    f"ortam ışığına göre 0/1/2 (şu an: "
                    f"{als_lux:.0f} lux)" if als_lux is not None else "ALS bulundu",
                    icon=ICONS["keyboard"]))
            ide = ideapad.get_all(cap)
            maxb = cap.kbd_backlight_max or 2
            try:
                cur = int(ide.get("kbd_backlight") or 0)
            except ValueError:
                cur = 0
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, maxb, 1)
            scale.set_value(cur)
            scale.set_draw_value(True)
            scale.set_hexpand(True)
            scale.set_size_request(300, -1)
            scale.set_margin_start(12)
            scale.set_margin_end(12)
            state = {"t": None}

            def _apply():
                stage("kbd_backlight", str(int(scale.get_value())))
                try:
                    from litage import cli as _cli2
                    if ((_cli2.get_daemon_kbd_auto() or "off").lower()
                            in ("true", "on", "1")):
                        stage("kbd_auto", "off")
                        toast("oto kapatıldı (manuel ayar)")
                except Exception:
                    pass
                state["t"] = None
                return False

            def _chg(_s):
                if state["t"] is not None:
                    GLib.source_remove(state["t"])
                state["t"] = GLib.timeout_add(600, _apply)

            scale.connect("value-changed", _chg)
            lab = Adw.ActionRow(title="Arka ışık",
                                subtitle="kaydır, bırakınca beklemeye alınır — Kaydet'e bas")
            lab.add_prefix(Gtk.Image.new_from_icon_name(ICONS["keyboard"]))
            grp.add(lab)
            grp.add(scale)
            grp.add(switch_row("Fn-Lock", ide.get("fn_lock") == "1", "fn_lock",
                               "Fn tuş kilidi (polkit ile)", icon=ICONS["keyboard"]))
        else:
            grp.add(locked_row("Klavye", "ideapad VPC yok", ICONS["keyboard"]))
        outer.append(grp)
        return page_scroll(outer)

    def build_fan() -> Gtk.Widget:
        """Fan eğrisi — Legion'da canlı grafik, bu cihazda kilitli panel."""
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        fc = legion.fancurve_summary() if cap.has_legion_module else {"present": False}
        grp = Adw.PreferencesGroup(title="Fan Eğrisi",
                                   description="10 nokta · sıcaklık → hız")
        if not fc.get("present"):
            grp.add(locked_row("Fan eğrisi düzenleyici",
                               "bu cihazda EC fan eğrisi yok — Legion/LOQ'da açılır",
                               ICONS["fan"]))
            info = Adw.ActionRow(
                title="Neden kapalı?",
                subtitle="Yoga/IdeaPad'de fan eğrisi firmware'de sabit. "
                         "Sadece fan modu (sessiz/normal) değiştirilebilir.")
            grp.add(info)
            if cap.has_ideapad:
                ide = ideapad.get_all(cap)
                grp.add(combo_row("Fan modu (bu cihazda çalışan)", str(ide.get("fan_mode")),
                                  ["0", "1", "2"], "fan_mode", icon=ICONS["fan"]))
        else:
            area = Gtk.DrawingArea()
            area.set_content_height(220)

            def _draw(_a, cr, w, h):
                pad_l, pad_r, pad_t, pad_b = 34, 10, 24, 24
                cr.select_font_face("Sans", 0, 0)
                cr.set_font_size(10)
                cr.set_source_rgba(0.5, 0.5, 0.5, 0.25)
                cr.set_line_width(1)
                for i in range(5):
                    y = pad_t + (h - pad_t - pad_b) * i / 4
                    cr.move_to(pad_l, y)
                    cr.line_to(w - pad_r, y)
                    cr.stroke()
                cr.set_source_rgba(0.7, 0.7, 0.7, 1)
                cr.move_to(pad_l, 15)
                cr.show_text("sıcaklık (°C) → hız")
                pts = fc.get("points", [])
                if not pts:
                    cr.move_to(pad_l, pad_t + 24)
                    cr.show_text("nokta yok")
                    return
                xs = [float(p.get("pwm1_auto_point%d_temp" % p["id"], 40)) for p in pts]
                ys = [float(str(p.get("pwm1_auto_point%d_pwm" % p["id"], 0))) for p in pts]
                x0, x1 = min(xs + [30]), max(xs + [100])
                span = max(1, x1 - x0)

                def PX(x):
                    return pad_l + (x - x0) / span * (w - pad_l - pad_r)

                def PY(y):
                    return pad_t + (1 - y / 255) * (h - pad_t - pad_b)

                cr.set_source_rgba(0.3, 0.77, 0.54, 0.20)
                cr.move_to(PX(xs[0]), h - pad_b)
                for x, y in zip(xs, ys):
                    cr.line_to(PX(x), PY(y))
                cr.line_to(PX(xs[-1]), h - pad_b)
                cr.close_path()
                cr.fill()
                cr.set_source_rgb(0.3, 0.77, 0.54)
                cr.set_line_width(2)
                cr.set_line_join(1)
                cr.move_to(PX(xs[0]), PY(ys[0]))
                for x, y in zip(xs[1:], ys[1:]):
                    cr.line_to(PX(x), PY(y))
                cr.stroke()
                for x, y in zip(xs, ys):
                    cr.arc(PX(x), PY(y), 3, 0, 6.2832)
                    cr.fill()
                cr.set_source_rgba(0.62, 0.62, 0.62, 1)
                cr.set_font_size(9)
                cr.move_to(4, h - 8)
                cr.show_text(f"{x0:.0f}°")
                cr.move_to(4, pad_t + 4)
                cr.show_text("max")

            area.set_draw_func(_draw)
            grp.add(area)
            grp.add(row("Hız birimi", Gtk.Label(label=str(fc.get("speed_unit"))),
                        icon=ICONS["fan"]))
        outer.append(grp)
        return page_scroll(outer)

    def build_legion() -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        grp = Adw.PreferencesGroup(title="Legion",
                                   description="LLL uyumlu · legion_laptop modülü")
        if not cap.has_legion_module:
            grp.add(locked_row("Legion kontrolleri",
                               "modül yüklü değil — Legion/LOQ'da açılır",
                               ICONS["legion"]))
            grp.add(Adw.ActionRow(
                title="Bilgi",
                subtitle="GameZone WMI + legion-laptop modülü yok. "
                         "Destekli Legion'da güç limitleri ve fan burada olur."))
        else:
            lg = legion.get_all()
            for feat, val in lg.get("bools", {}).items():
                grp.add(switch_row(feat, str(val) == "1", feat, icon=ICONS["legion"]))
            for feat, val in lg.get("ints", {}).items():
                lo, hi = legion.INT_NODES.get(feat, (0, 200))
                sp = Gtk.SpinButton.new_with_range(lo, hi, 1)
                try:
                    sp.set_value(float(val or lo))
                except ValueError:
                    pass

                def _ap(_s, feat=feat):
                    privileged_set(feat, str(int(_s.get_value())))

                sp.connect("value-changed", _ap)
                grp.add(row(f"{feat} (W)", sp, icon=ICONS["legion"]))
        outer.append(grp)
        return page_scroll(outer)

    def build_dgpu() -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        grp = Adw.PreferencesGroup(title="Harici GPU")
        if not cap.show_dgpu_page:
            grp.add(locked_row("dGPU kontrolleri",
                               "NVIDIA yok (iGPU-only cihaz) — dGPU'lu modelde açılır",
                               ICONS["dgpu"]))
        else:
            nv = optional.nvidia_get(cap)
            grp.add(row("Durum", Gtk.Label(label=str(nv.get("smi", "NVIDIA mevcut"))),
                        icon=ICONS["dgpu"]))
        outer.append(grp)
        return page_scroll(outer)

    def build_automation() -> Gtk.Widget:
        import glob as _g
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        grp = Adw.PreferencesGroup(title="litaged presetleri",
                                   description="/etc/litage/profiles/*.yaml — AC/pil × profil")
        profs = sorted(_g.glob("/etc/litage/profiles/*.yaml") or _g.glob("daemon/profiles/*.yaml"))
        if not profs:
            grp.add(row("Preset", Gtk.Label(label="bulunamadı (henüz kurulmadı)")))
        for p in profs:
            name = os.path.basename(p)
            r = row(name, Gtk.Label(label="hazır"), subtitle=p, icon=ICONS["automation"])
            attach_menu(r, [
                ("Yolu kopyala", lambda p=p: copy_text(p)),
                ("Şimdi uygula (daemon --once)",
                 lambda p=p: toast("terminal: sudo litaged --once")),
            ])
            grp.add(r)
        grp.add(Adw.ActionRow(
            title="TLP ile birlikte kullanım",
            subtitle="governor/epp preset BOŞ bırakılırsa TLP yönetir, doluysa litaged yönetir."))
        outer.append(grp)
        return page_scroll(outer)

    def build_settings(app) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        # görünüm
        gv = Adw.PreferencesGroup(title="Görünüm")
        cur = theme_mod.load()
        theme_ready = {"ready": False}
        cr = Adw.ComboRow(title="Tema", model=Gtk.StringList.new(
            [theme_mod.THEME_LABELS[t] for t in theme_mod.THEMES]))
        cr.add_prefix(Gtk.Image.new_from_icon_name(ICONS["display"]))
        try:
            cr.set_selected(theme_mod.THEMES.index(cur))
        except ValueError:
            pass

        def _theme(_r, _p):
            if not theme_ready["ready"]:
                return
            name = theme_mod.THEMES[cr.get_selected()]
            theme_mod.save(name)
            theme_mod.apply(name, css_providers=css_providers)
            toast(f"tema: {theme_mod.THEME_LABELS[name]}")

        cr.connect("notify::selected", _theme)
        GLib.idle_add(lambda: theme_ready.update(ready=True) or False)
        gv.add(cr)
        outer.append(gv)
        # uygulama
        grp = Adw.PreferencesGroup(title="Uygulama")
        ad_path = os.path.expanduser("~/.config/autostart/litage-gui.desktop")
        sr = Adw.SwitchRow(title="Açılışta başlat",
                           subtitle="~/.config/autostart (tepsiye küçültülmüş)",
                           active=os.path.exists(ad_path))

        def _autostart(_r, _p):
            from litage import autostart as _a
            if sr.get_active():
                _ok, msg = _a.enable(minimized=True)
            else:
                _ok, msg = _a.disable()
            toast(msg)

        sr.connect("notify::active", _autostart)
        grp.add(sr)
        grp.add(row("Yapılandırma", Gtk.Label(label="/etc/litage/litaged.conf"),
                    icon=ICONS["settings"]))
        outer.append(grp)
        try:
            from litage import prefs as _prefs
            gclose = Adw.PreferencesGroup(title="Pencere")
            cur_close = _prefs.get_close_action()
            labels = [_prefs.CLOSE_LABELS["tray"], _prefs.CLOSE_LABELS["quit"]]
            ccr = Adw.ComboRow(title="Kapat düğmesi",
                                model=Gtk.StringList.new(labels))
            ccr.add_prefix(Gtk.Image.new_from_icon_name(ICONS["settings"]))
            ccr.set_selected(1 if cur_close == "quit" else 0)

            def _cc(_r, _p):
                _prefs.set_close_action(
                    "quit" if ccr.get_selected() == 1 else "tray")
                toast("kapatma davranışı kaydedildi")

            ccr.connect("notify::selected", _cc)
            gclose.add(ccr)
            outer.append(gclose)
        except Exception:
            pass
        return page_scroll(outer)

    def build_system() -> Gtk.Widget:
        """Kurulum teşhisi — eksikleri kapatma sayfası."""
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        d = priv.diagnose()
        grp = Adw.PreferencesGroup(title="Kurulum durumu",
                                   description="Yazmalar için hepsi yeşil olmalı")
        checks = [
            ("CLI", " ".join(d["cli"]) if d["cli"] else "bulunamadı",
             bool(d["cli"]), ICONS["cpu"]),
            ("pkexec", d["pkexec"] or "yok", bool(d["pkexec"]), ICONS["lock"]),
            ("Polkit policy", d["policy"] or "kurulu değil — ./install.sh",
             bool(d["policy"]), ICONS["lock"]),
            ("udev kuralı", d["udev"] or "kurulu değil — ./install.sh",
             bool(d["udev"]), ICONS["settings"]),
            ("Polkit agent (kurulu)", d["agent_bin"] or "yok — şifre penceresi çıkmaz",
             bool(d["agent_bin"]), ICONS["system"]),
            ("Polkit agent (çalışıyor)", "çalışıyor" if d["agent_running"] else "ÇALIŞMIYOR",
             d["agent_running"], ICONS["system"]),
        ]
        for title, sub, okk, ic in checks:
            r = Adw.ActionRow(title=title, subtitle=sub)
            r.add_prefix(Gtk.Image.new_from_icon_name(ic))
            dot = Gtk.Label(label="●")
            dot.add_css_class("success" if okk else "error")
            r.add_suffix(dot)
            attach_menu(r, [("Kopyala", lambda sub=sub: copy_text(sub))])
            grp.add(r)
        if d["appimage"]:
            grp.add(row("AppImage", Gtk.Label(label=d["appimage"]), icon=ICONS["system"]))
        fix = Adw.ActionRow(
            title="Tek komutla kur",
            subtitle="sudo ./install.sh --autostart (policy+udev+agent+menü)")
        btn = Gtk.Button(label="Komutu kopyala")
        btn.add_css_class("suggested-action")
        btn.connect("clicked",
                    lambda _b: copy_text("sudo ./install.sh --autostart"))
        fix.add_suffix(btn)
        grp.add(fix)
        # tepsi durumu
        tray_ok = tray_running()
        tray_row = Adw.ActionRow(
            title="Tepsi simgesi",
            subtitle="çalışıyor" if tray_ok else "yok — panelde görünmüyorsa başlatın")
        tray_row.add_prefix(Gtk.Image.new_from_icon_name(ICONS["battery"]))
        tbtn = Gtk.Button(label="Tepsiyi başlat")
        tbtn.connect("clicked", lambda _b: (ensure_tray(), toast("tepsi başlatıldı")))
        tray_row.add_suffix(tbtn)
        grp.add(tray_row)
        applet_ok, applet_msg = priv.cinnamon_tray_applet()
        if not applet_ok:
            grp.add(Adw.ActionRow(title="Cinnamon tepsi applet'i", subtitle=applet_msg))
        # şifresiz yazma durumu (udev kuralı işlemiş mi?)
        dw = priv.direct_writable()
        if dw:
            n_ok = sum(1 for v in dw.values() if v)
            dw_row = Adw.ActionRow(
                title=f"Şifresiz yazma: {n_ok}/{len(dw)}",
                subtitle="tamamı OK ise şifre sorulmaz" if n_ok == len(dw)
                         else "sudo ./install.sh + yeniden başlatma gerekir")
            dw_row.add_prefix(Gtk.Image.new_from_icon_name(
                ICONS["lock"] if n_ok < len(dw) else ICONS["settings"]))
            dot = Gtk.Label(label="●")
            dot.add_css_class("success" if n_ok == len(dw) else "error")
            dw_row.add_suffix(dot)
            attach_menu(dw_row, [("Kopyala",
                                  lambda: copy_text("\n".join(
                                      f"{p}: {'OK' if o else 'root'}"
                                      for p, o in dw.items())))])
            grp.add(dw_row)
        outer.append(grp)
        # TLP + thinklmi özet
        if cap.has_tlp:
            g2 = Adw.PreferencesGroup(title="TLP")
            cfg = tlp.config_values()
            for k in sorted(cfg):
                if k in tlp.WRITABLE_KEYS:
                    g2.add(row(k, Gtk.Label(label=str(cfg[k])), icon=ICONS["power"]))
            outer.append(g2)
        au = audio.get()
        if au.get("tool"):
            g3 = Adw.PreferencesGroup(title="Ses")
            g3.add(row("Ses aracı", Gtk.Label(label=str(au["tool"])), icon=ICONS["mic"]))
            outer.append(g3)
        tl = thinklmi.get(cap)
        if tl:
            g4 = Adw.PreferencesGroup(title="think-lmi (root ile okunur)")
            for k in sorted(tl)[:12]:
                v = tl[k]
                cur = v.get("current") if isinstance(v, dict) else v
                g4.add(row(k, Gtk.Label(label=str(cur))))
            outer.append(g4)
        return page_scroll(outer)

    def build_about() -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(16)
        outer.set_margin_start(16)
        outer.set_margin_end(16)
        grp = Adw.PreferencesGroup(title="Bu makine")
        grp.add(row("Model", Gtk.Label(label=f"{cap.vendor} {cap.product_version}"),
                    icon=ICONS["system"]))
        grp.add(row("BIOS", Gtk.Label(label=cap.bios_version), icon=ICONS["settings"]))
        grp.add(row("Litage", Gtk.Label(label="0.2.0 · GPL-3.0"), icon=ICONS["about"]))
        outer.append(grp)
        return page_scroll(outer)

    # ---------------- pencere ----------------
    # sayfa kayıtları Win dışında tutulur ki yenileme/sağ tık erişebilsin
    ui = {"stack": None, "content": None, "rows": {}, "built": {}, "items": []}
    ui["items"] = [
        ("dashboard", "Genel Bakış", ICONS["dashboard"], build_dashboard, None),
        ("battery", "Pil", ICONS["battery"], build_battery, None),
        ("keyboard", "Klavye", ICONS["keyboard"], build_keyboard, None),
        ("fan", "Fan Eğrisi",
         ICONS["fan"], build_fan,
         None if cap.has_legion_module else "bu cihazda yok"),
        ("legion", "Legion",
         ICONS["legion"], build_legion,
         None if cap.has_legion_module else "modül yok"),
        ("dgpu", "Harici GPU",
         ICONS["dgpu"], build_dgpu,
         None if cap.show_dgpu_page else "donanım yok"),
        ("automation", "Otomasyon", ICONS["automation"], build_automation, None),
        ("settings", "Ayarlar", ICONS["settings"], None, None),
        ("system", "Sistem", ICONS["system"], build_system, None),
        ("about", "Hakkında", ICONS["about"], build_about, None),
    ]

    def show_page(key: str, rebuild: bool = False):
        items = ui["items"]
        stack = ui["stack"]
        if stack is None:
            state["current"] = key
            return
        state["current"] = key
        for k, label, _ic, fn, _locked in items:
            if k != key:
                continue
            if k in ui["built"] and rebuild:
                old = ui["built"].pop(k)
                stack.remove(old)
            if k not in ui["built"]:
                w = build_settings(app_ref["app"]) if k == "settings" else fn()
                ui["built"][k] = w
                stack.add_named(w, k)
            stack.set_visible_child_name(k)
            if ui["content"] is not None:
                ui["content"].set_title(label)
            break

    def refresh_current():
        show_page(state["current"], rebuild=True)
        return False

    app_ref: dict = {}

    class Win(Adw.ApplicationWindow):
        def __init__(self, application):
            super().__init__(application=application)
            self.set_title(f"Litage — {cap.product_version or cap.product_name or 'Lenovo'}")
            self.set_default_size(1120, 700)
            def _on_close(_w):
                try:
                    from litage import prefs as _prefs
                    action = _prefs.get_close_action()
                except Exception:
                    action = "tray"
                if action == "quit":
                    for _lp in (f"/run/user/{os.getuid()}/litage-tray.lock",
                                "/tmp/litage-tray.lock"):
                        try:
                            with open(_lp, encoding="utf-8") as _f:
                                os.kill(int(_f.read().strip()), 15)
                        except (OSError, ValueError):
                            pass
                        try:
                            os.remove(_lp)
                        except OSError:
                            pass
                    ui.pop("win", None)
                    return False
                _w.set_visible(False)
                print("[litage-gui] tepsiye küçültüldü")
                return True

            self.connect("close-request", _on_close)

            global toast_overlay
            toast_overlay = Adw.ToastOverlay()
            # NOT: Adw.NavigationSplitView sidebar genişliğini kendi yönettiği
            # için hover-genişleme çalışmıyordu (sadece yazılar beliriyordu).
            # Bu yüzden gövde düz Gtk.Box: [ray] + [içerik].
            shell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            toast_overlay.set_child(shell)
            self.set_content(toast_overlay)

            # --- statik yan panel: ikon + etiket, her zaman tam boy ---
            sbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            sbox.set_size_request(196, -1)
            header = Adw.HeaderBar()
            # pencere düğmeleri içerik başlığında; burada tekrarlanmasın
            header.set_show_start_title_buttons(False)
            header.set_show_end_title_buttons(False)
            title = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
            logo = Gtk.Image.new_from_icon_name(ICONS["power"])
            logo.set_pixel_size(22)
            title.append(logo)
            title.append(Gtk.Label(label="Litage"))
            header.set_title_widget(title)
            sbox.append(header)
            nav = Gtk.ListBox()
            nav.add_css_class("navigation-sidebar")
            nav.set_selection_mode(Gtk.SelectionMode.SINGLE)
            sbox.append(nav)

            content_page = Adw.NavigationPage(title="İçerik")
            cbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
            cheader = Adw.HeaderBar()
            refresh_btn = Gtk.Button.new_from_icon_name(ICONS["refresh"])
            refresh_btn.set_tooltip_text("Yenile")
            refresh_btn.connect("clicked", lambda _b: refresh_current())
            cheader.pack_end(refresh_btn)
            cbox.append(cheader)
            stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE,
                              hexpand=True, vexpand=True)
            cbox.append(stack)
            # Kaydet: başlıkta kompakt (ekran kaplamaz) — bekleyen varsa aktif
            btn_cancel = Gtk.Button(label="Vazgeç")
            btn_cancel.set_tooltip_text("Bekleyen değişiklikleri geri al")
            btn_cancel.connect("clicked", lambda _b: save_discard())
            btn_cancel.set_sensitive(False)
            btn_cancel.set_opacity(0.45)
            cheader.pack_end(btn_cancel)
            save_count = Gtk.Label(label="")
            save_count.add_css_class("accent")
            save_count.set_visible(False)
            cheader.pack_end(save_count)
            btn_save = Gtk.Button(label="Kaydet")
            btn_save.set_tooltip_text("Bekleyenleri tek şifreyle uygula")
            btn_save.add_css_class("suggested-action")
            btn_save.connect("clicked", lambda _b: save_apply())
            btn_save.set_sensitive(False)
            btn_save.set_opacity(0.45)
            cheader.pack_end(btn_save)
            ui_state["btn_save"] = btn_save
            ui_state["btn_cancel"] = btn_cancel
            ui_state["save_count"] = save_count
            content_page.set_child(cbox)
            shell.append(sbox)
            shell.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
            shell.append(content_page)
            ui["stack"] = stack
            ui["content"] = content_page

            for key, label, ic, _fn, locked in ui["items"]:
                r = Gtk.ListBoxRow()
                # kilitli satır bilerek hassas bırakılır: tıklayınca sayfa
                # açılmaz ama neden kapalı olduğu söylenir.
                r.set_tooltip_text(
                    label if not locked
                    else f"{label}: {locked} — destekli donanımda açılır")
                box = Gtk.Box(spacing=10)
                box.set_margin_top(7)
                box.set_margin_bottom(7)
                box.set_margin_start(10)
                box.set_margin_end(8)
                img = Gtk.Image.new_from_icon_name(ic)
                img.set_pixel_size(20)
                box.append(img)
                box.append(Gtk.Label(label=label, xalign=0, hexpand=True))
                if locked:
                    badge = Gtk.Label(label="YOK")
                    badge.add_css_class("dim-label")
                    box.append(badge)
                r.set_child(box)
                attach_menu(r, [
                    ("Sayfaya git", lambda key=key: show_page(key)),
                    ("Adı kopyala", lambda label=label: copy_text(label)),
                ])
                nav.append(r)
                ui["rows"][key] = r

            def _nav_changed(_lb, r):
                for k, rr in ui["rows"].items():
                    if rr == r:
                        for kk, _lab, _ic, _fn, locked in ui["items"]:
                            if kk == k and locked:
                                toast(f"{_lab}: {locked}")
                                nav.select_row(ui["rows"][state["current"]])
                                return
                        show_page(k)
                        break

            nav.connect("row-selected", _nav_changed)
            nav.select_row(ui["rows"].get(start_page) or ui["rows"]["dashboard"])

    # ---------------- tepsi (ayrı GTK3 süreç — GTK4'e gömülemez) ----------------
    def ensure_tray():
        """litage-tray yardımcısını başlat (tekil; lockfile ile korunur)."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = dict(os.environ)
        env["PYTHONPATH"] = base + ":" + env.get("PYTHONPATH", "")
        for cmd in (["litage-tray"], [sys.executable, "-m", "litage.tray"]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True, cwd=base, env=env)
                return
            except OSError:
                continue
        toast("tepsi başlatılamadı")

    def tray_running() -> bool:
        for path in (f"/run/user/{os.getuid()}/litage-tray.lock",
                     "/tmp/litage-tray.lock"):
            try:
                with open(path, encoding="utf-8") as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                return True
            except (OSError, ValueError):
                continue
        return False

    app = Adw.Application(application_id="dev.litage.app",
                          flags=Gio.ApplicationFlags.FLAGS_NONE)

    def _activate(a):
        app_ref["app"] = a
        # tekil örnek: pencere varsa yenisini açma, mevcutu öne getir
        if ui.get("win") is not None:
            try:
                ui["win"].present()
                return
            except Exception:
                pass
        w = Win(a)
        ui["win"] = w
        ensure_tray()
        start_sampler()
        if not minimized:
            w.present()

    app.connect("activate", _activate)
    return app.run([sys.argv[0]])


if __name__ == "__main__":
    raise SystemExit(main())
