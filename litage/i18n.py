"""Basit iki dilli arayüz metinleri (Türkçe / English).

Kullanım: `t("nav.dashboard")` — dil `~/.config/litage/settings.ini`
`[ui] lang` anahtarından okunur (yoksa sistem yerel ayarından algılanır).
Dil değişikliği yeniden başlatınca etkili olur.
"""
from __future__ import annotations

import locale
import os

LANGS = ("tr", "en")
LANG_LABELS = {"tr": "Türkçe", "en": "English"}

STR: dict[str, dict[str, str]] = {
    # --- gezinme ---
    "nav.dashboard": {"tr": "Genel Bakış", "en": "Dashboard"},
    "nav.battery": {"tr": "Pil", "en": "Battery"},
    "nav.keyboard": {"tr": "Klavye", "en": "Keyboard"},
    "nav.fan": {"tr": "Fan Eğrisi", "en": "Fan Curve"},
    "nav.legion": {"tr": "Legion", "en": "Legion"},
    "nav.dgpu": {"tr": "Harici GPU", "en": "Discrete GPU"},
    "nav.automation": {"tr": "Otomasyon", "en": "Automation"},
    "nav.settings": {"tr": "Ayarlar", "en": "Settings"},
    "nav.system": {"tr": "Sistem", "en": "System"},
    "nav.about": {"tr": "Hakkında", "en": "About"},
    "nav.content": {"tr": "İçerik", "en": "Content"},
    "nav.locked_why": {"tr": "{label}: {reason} — destekli donanımda açılır",
                       "en": "{label}: {reason} — available on supported hardware"},
    "nav.badge_missing": {"tr": "YOK", "en": "N/A"},
    "f.locked_reason_short": {"tr": "bu cihazda yok", "en": "not on this device"},
    "l.locked_reason_short": {"tr": "modül yok", "en": "no module"},
    "g.locked_reason_short": {"tr": "donanım yok", "en": "no hardware"},
    # --- ortak ---
    "c.ctx_goto": {"tr": "Sayfaya git", "en": "Go to page"},
    "c.ctx_copy_name": {"tr": "Adı kopyala", "en": "Copy name"},
    "c.ctx_copy_value": {"tr": "Değeri kopyala", "en": "Copy value"},
    "c.ctx_refresh": {"tr": "Yenile", "en": "Refresh"},
    "c.ctx_apply_term": {"tr": "Terminalde uygula", "en": "Copy terminal command"},
    "c.toast_copied": {"tr": "kopyalandı", "en": "copied"},
    "c.toast_copy_fail": {"tr": "kopyalanamadı: {e}", "en": "copy failed: {e}"},
    "c.toast_refresh_hint": {"tr": "Yenile", "en": "Refresh"},
    "c.toast_minimized": {"tr": "tepsiye küçültüldü", "en": "minimized to tray"},
    "d.provider": {"tr": "sağlayıcı: {driver}", "en": "provider: {driver}"},
    "y.tray_failed": {"tr": "tepsi başlatılamadı", "en": "tray failed to start"},
    "c.save": {"tr": "Kaydet", "en": "Save"},
    "c.cancel": {"tr": "Vazgeç", "en": "Discard"},
    "c.save_tip": {"tr": "Bekleyenleri tek şifreyle uygula",
                   "en": "Apply pending changes with a single password"},
    "c.cancel_tip": {"tr": "Bekleyen değişiklikleri geri al",
                     "en": "Discard pending changes"},
    "c.staged": {"tr": "bekliyor: {item} (Kaydet'e bas)",
                 "en": "pending: {item} (press Save)"},
    # --- dashboard ---
    "d.sensors": {"tr": "Sensörler", "en": "Sensors"},
    "d.graphs": {"tr": "Grafikler", "en": "Graphs"},
    "d.graphs_desc": {"tr": "canlı · 2 sn aralık · sağ tık menüsü var",
                      "en": "live · 2 s interval · right-click menu available"},
    "d.cpu_temp": {"tr": "CPU sıcaklığı", "en": "CPU temperature"},
    "d.gpu_temp": {"tr": "GPU sıcaklığı", "en": "GPU temperature"},
    "d.cpu_freq": {"tr": "CPU frekansı", "en": "CPU frequency"},
    "d.collecting": {"tr": "veri toplanıyor…", "en": "collecting data…"},
    "d.power": {"tr": "Güç", "en": "Power"},
    "d.power_desc": {"tr": "Fn+Q ile aynı profil", "en": "Same profile as Fn+Q"},
    "d.power_mode": {"tr": "Güç modu", "en": "Power mode"},
    "d.governor": {"tr": "CPU governor", "en": "CPU governor"},
    "d.governor_sub": {"tr": "powersave = tutumlu, performance = tam güç",
                       "en": "powersave = efficient, performance = full power"},
    "d.epp": {"tr": "Enerji tercihi (EPP)", "en": "Energy preference (EPP)"},
    "d.epp_sub": {"tr": "performance → power: hızlıdan tutumluya",
                  "en": "performance → power: from fast to efficient"},
    "d.boost": {"tr": "CPU Boost", "en": "CPU Boost"},
    "d.boost_sub": {"tr": "kısa süreli hız aşırtma (ısı artar)",
                    "en": "short-term turbo (more heat)"},
    "d.lenovo": {"tr": "Lenovo", "en": "Lenovo"},
    "d.conservation": {"tr": "Pil koruma", "en": "Battery conservation"},
    "d.conservation_sub": {"tr": "şarjı %80'de durdurur (pil ömrü için)",
                           "en": "stops charging at 80% (battery health)"},
    "d.fnlock": {"tr": "Fn-Lock", "en": "Fn-Lock"},
    "d.fnlock_sub": {"tr": "F1–F12 doğrudan işlev görür (medya tuşu değil)",
                     "en": "F1–F12 act as function keys (not media keys)"},
    "d.camera": {"tr": "Kamera", "en": "Camera"},
    "d.camera_sub": {"tr": "kamerayı donanımsal aç/kapat",
                     "en": "hardware camera on/off"},
    "d.usb": {"tr": "Kapalıyken USB şarj", "en": "USB charging when off"},
    "d.usb_sub": {"tr": "bilgisayar kapalıyken telefon şarj eder",
                  "en": "charge phones while the laptop is off"},
    "d.fanmode": {"tr": "Fan modu", "en": "Fan mode"},
    "d.fanmode_sub": {"tr": "0=sessiz · 1=dengeli · 2=performans (modele göre değişir)",
                      "en": "0=quiet · 1=balanced · 2=performance (model-dependent)"},
    "d.kbd": {"tr": "Klavye ışığı", "en": "Keyboard backlight"},
    "d.kbd_sub": {"tr": "0=kapalı · 1=kısık · 2=parlak",
                  "en": "0=off · 1=dim · 2=bright"},
    "d.tlp": {"tr": "TLP", "en": "TLP"},
    "d.tlp_desc": {"tr": "Tek opsiyonel bağımlılık",
                   "en": "The single optional dependency"},
    "d.tlp_profile": {"tr": "TLP profili", "en": "TLP profile"},
    "d.tlp_threshold": {"tr": "Şarj eşiği", "en": "Charge thresholds"},
    "d.tlp_boost_bat": {"tr": "Boost (pilde, TLP)", "en": "Boost (on battery, TLP)"},
    "d.tlp_boost_off": {"tr": "kapalı", "en": "off"},
    "d.tlp_boost_on": {"tr": "açık", "en": "on"},
    "d.conn": {"tr": "Bağlantı", "en": "Connectivity"},
    "d.wifi": {"tr": "Wi-Fi", "en": "Wi-Fi"},
    "d.bt": {"tr": "Bluetooth", "en": "Bluetooth"},
    "d.battery_line": {"tr": "Pil %{cap} · {st}", "en": "Battery %{cap} · {st}"},
    # --- pil sayfası ---
    "b.stats": {"tr": "İstatistik", "en": "Statistics"},
    "b.status": {"tr": "Durum", "en": "Status"},
    "b.capacity": {"tr": "Kapasite (%)", "en": "Capacity (%)"},
    "b.level": {"tr": "Seviye", "en": "Level"},
    "b.ctype": {"tr": "Şarj tipi", "en": "Charge type"},
    "b.ctypes": {"tr": "Tipler", "en": "Types"},
    "b.cycle": {"tr": "Çevrim", "en": "Cycle count"},
    "b.full": {"tr": "Dolu (µWh)", "en": "Full (µWh)"},
    "b.design": {"tr": "Tasarım (µWh)", "en": "Design (µWh)"},
    "b.now": {"tr": "Anlık (µWh)", "en": "Current (µWh)"},
    "b.power": {"tr": "Güç (µW)", "en": "Power (µW)"},
    "b.voltage": {"tr": "Voltaj (µV)", "en": "Voltage (µV)"},
    "b.tech": {"tr": "Teknoloji", "en": "Technology"},
    "b.vendor": {"tr": "Üretici", "en": "Manufacturer"},
    "b.model": {"tr": "Model", "en": "Model"},
    "b.health": {"tr": "Pil sağlığı", "en": "Battery health"},
    "b.health_sub": {"tr": "dolu / tasarım", "en": "full / design"},
    "b.tlp_group": {"tr": "TLP şarj eşiği", "en": "TLP charge thresholds"},
    "b.tlp_change": {"tr": "Eşik değiştir (polkit)", "en": "Change thresholds (polkit)"},
    "b.tlp_apply": {"tr": "Uygula: 20–80", "en": "Apply: 20–80"},
    "b.tlp_hint": {"tr": "Örn: 20–80 için tıklayıp şifrenizi girin",
                   "en": "E.g. click for 20–80, then enter your password"},
    # --- klavye ---
    "k.title": {"tr": "Klavye", "en": "Keyboard"},
    "k.desc": {"tr": "ideapad VPC", "en": "ideapad VPC"},
    "k.auto": {"tr": "Otomatik parlaklık", "en": "Auto brightness"},
    "k.auto_sub": {"tr": "ortam ışığına göre 0/1/2 (şu an: {lux} lux)",
                   "en": "0/1/2 by ambient light (now: {lux} lux)"},
    "k.auto_sub_nolux": {"tr": "ALS bulundu", "en": "Ambient sensor found"},
    "k.backlight": {"tr": "Arka ışık", "en": "Backlight"},
    "k.backlight_sub": {"tr": "kaydır, bırakınca beklemeye alınır — Kaydet'e bas",
                        "en": "drag, release to stage — then press Save"},
    "k.fnlock": {"tr": "Fn-Lock", "en": "Fn-Lock"},
    "k.fnlock_sub": {"tr": "Fn tuş kilidi (Kaydet ile uygulanır)",
                     "en": "Fn key lock (applied with Save)"},
    "k.no_vpc": {"tr": "Klavye", "en": "Keyboard"},
    "k.no_vpc_sub": {"tr": "ideapad VPC yok", "en": "no ideapad VPC"},
    "k.auto_off": {"tr": "oto kapatıldı (manuel ayar)",
                   "en": "auto disabled (manual setting)"},
    # --- fan ---
    "f.title": {"tr": "Fan Eğrisi", "en": "Fan Curve"},
    "f.desc": {"tr": "10 nokta · sıcaklık → hız", "en": "10 points · temperature → speed"},
    "f.locked": {"tr": "Fan eğrisi düzenleyici", "en": "Fan curve editor"},
    "f.locked_reason": {"tr": "bu cihazda EC fan eğrisi yok — Legion/LOQ'da açılır",
                        "en": "no EC fan curve on this device — available on Legion/LOQ"},
    "f.why": {"tr": "Neden kapalı?", "en": "Why disabled?"},
    "f.why_sub": {"tr": "Yoga/IdeaPad'de fan eğrisi firmware'de sabit. "
                         "Sadece fan modu (sessiz/normal) değiştirilebilir.",
                  "en": "On Yoga/IdeaPad the fan curve is fixed in firmware. "
                        "Only the fan mode (quiet/normal) can be changed."},
    "f.mode_working": {"tr": "Fan modu (bu cihazda çalışan)",
                       "en": "Fan mode (works on this device)"},
    "f.unit": {"tr": "Hız birimi", "en": "Speed unit"},
    "f.axis": {"tr": "sıcaklık (°C) → hız", "en": "temperature (°C) → speed"},
    "f.no_points": {"tr": "nokta yok", "en": "no points"},
    "f.max": {"tr": "max", "en": "max"},
    # --- legion / dgpu ---
    "l.title": {"tr": "Legion", "en": "Legion"},
    "l.desc": {"tr": "LLL uyumlu · legion_laptop modülü",
               "en": "LLL-compatible · legion_laptop module"},
    "l.locked": {"tr": "Legion kontrolleri", "en": "Legion controls"},
    "l.locked_reason": {"tr": "modül yüklü değil — Legion/LOQ'da açılır",
                        "en": "module not loaded — available on Legion/LOQ"},
    "l.info": {"tr": "Bilgi", "en": "Info"},
    "l.info_sub": {"tr": "GameZone WMI + legion-laptop modülü yok. Destekli Legion'da "
                         "güç limitleri ve fan burada olur.",
                   "en": "No GameZone WMI + legion-laptop module. Power limits and "
                         "fan controls appear here on a supported Legion."},
    "l.watt": {"tr": "{feat} (W)", "en": "{feat} (W)"},
    "l.fancurve": {"tr": "Fan curve", "en": "Fan curve"},
    "l.fancurve_none": {"tr": "bu modelde yok", "en": "not on this model"},
    "g.title": {"tr": "Harici GPU", "en": "Discrete GPU"},
    "g.locked": {"tr": "dGPU kontrolleri", "en": "dGPU controls"},
    "g.locked_reason": {"tr": "NVIDIA yok (iGPU-only cihaz) — dGPU'lu modelde açılır",
                        "en": "No NVIDIA (iGPU-only device) — available with a dGPU"},
    "g.status": {"tr": "Durum", "en": "Status"},
    "g.present": {"tr": "NVIDIA mevcut", "en": "NVIDIA present"},
    # --- otomasyon ---
    "a.presets": {"tr": "litaged presetleri", "en": "litaged presets"},
    "a.presets_desc": {"tr": "/etc/litage/profiles/*.yaml — AC/pil × profil",
                       "en": "/etc/litage/profiles/*.yaml — AC/battery × profile"},
    "a.preset": {"tr": "Preset", "en": "Preset"},
    "a.not_found": {"tr": "bulunamadı (henüz kurulmadı)",
                    "en": "none found (not installed yet)"},
    "a.ready": {"tr": "hazır", "en": "ready"},
    "a.copy_path": {"tr": "Yolu kopyala", "en": "Copy path"},
    "a.apply_now": {"tr": "Şimdi uygula (daemon --once)",
                    "en": "Apply now (daemon --once)"},
    "a.apply_hint": {"tr": "terminal: sudo litaged --once",
                     "en": "terminal: sudo litaged --once"},
    "a.tlp_title": {"tr": "TLP ile birlikte kullanım", "en": "Using it with TLP"},
    "a.tlp_sub": {"tr": "governor/epp preset BOŞ bırakılırsa TLP yönetir, doluysa litaged yönetir.",
                  "en": "Leave governor/epp EMPTY in presets for TLP to manage them, "
                        "otherwise litaged does."},
    # --- ayarlar ---
    "s.appearance": {"tr": "Görünüm", "en": "Appearance"},
    "s.theme": {"tr": "Tema", "en": "Theme"},
    "th.saf-siyah": {"tr": "Saf siyah (#000)", "en": "Pure black (#000)"},
    "th.koyu": {"tr": "Koyu (Adwaita)", "en": "Dark (Adwaita)"},
    "th.gri": {"tr": "Gri", "en": "Gray"},
    "th.beyaz": {"tr": "Beyaz", "en": "White"},
    "s.language": {"tr": "Dil", "en": "Language"},
    "s.language_sub": {"tr": "değişiklik yeniden başlatınca etkili olur",
                       "en": "takes effect after restart"},
    "s.language_saved": {"tr": "dil kaydedildi, yeniden başlatın",
                         "en": "language saved, please restart"},
    "s.app": {"tr": "Uygulama", "en": "Application"},
    "s.autostart": {"tr": "Açılışta başlat", "en": "Start on login"},
    "s.autostart_sub": {"tr": "~/.config/autostart (tepsiye küçültülmüş)",
                        "en": "~/.config/autostart (minimized to tray)"},
    "s.config": {"tr": "Yapılandırma", "en": "Configuration"},
    "s.window": {"tr": "Pencere", "en": "Window"},
    "s.close_btn": {"tr": "Kapat düğmesi", "en": "Close button"},
    "s.close_saved": {"tr": "kapatma davranışı kaydedildi",
                      "en": "close behavior saved"},
    "s.close_tray": {"tr": "Tepsiye küçült (arka planda çalışır)",
                     "en": "Minimize to tray (keeps running)"},
    "s.close_quit": {"tr": "Tümden çık (tray de kapanır)",
                     "en": "Quit entirely (tray closes too)"},
    "s.theme_saved": {"tr": "tema: {label}", "en": "theme: {label}"},
    # --- sistem ---
    "y.diag": {"tr": "Kurulum durumu", "en": "Installation status"},
    "y.diag_desc": {"tr": "Yazmalar için hepsi yeşil olmalı",
                    "en": "All green for writes to work"},
    "y.cli": {"tr": "CLI", "en": "CLI"},
    "y.cli_missing": {"tr": "bulunamadı", "en": "not found"},
    "y.pkexec": {"tr": "pkexec", "en": "pkexec"},
    "y.pkexec_missing": {"tr": "yok", "en": "missing"},
    "y.policy": {"tr": "Polkit policy", "en": "Polkit policy"},
    "y.policy_missing": {"tr": "kurulu değil — ./install.sh",
                         "en": "not installed — run ./install.sh"},
    "y.udev": {"tr": "udev kuralı", "en": "udev rule"},
    "y.udev_missing": {"tr": "kurulu değil — ./install.sh",
                       "en": "not installed — run ./install.sh"},
    "y.agent_bin": {"tr": "Polkit agent (kurulu)", "en": "Polkit agent (installed)"},
    "y.agent_bin_missing": {"tr": "yok — şifre penceresi çıkmaz",
                            "en": "missing — no password dialog"},
    "y.agent_run": {"tr": "Polkit agent (çalışıyor)", "en": "Polkit agent (running)"},
    "y.agent_running": {"tr": "çalışıyor", "en": "running"},
    "y.agent_down": {"tr": "ÇALIŞMIYOR", "en": "NOT RUNNING"},
    "y.copy": {"tr": "Kopyala", "en": "Copy"},
    "y.appimage": {"tr": "AppImage", "en": "AppImage"},
    "y.fix": {"tr": "Tek komutla kur", "en": "Install with one command"},
    "y.fix_sub": {"tr": "sudo ./install.sh --autostart (policy+udev+agent+menü)",
                  "en": "sudo ./install.sh --autostart (policy+udev+agent+menu)"},
    "y.fix_copy": {"tr": "Komutu kopyala", "en": "Copy command"},
    "y.tray": {"tr": "Tepsi simgesi", "en": "Tray icon"},
    "y.tray_running": {"tr": "çalışıyor", "en": "running"},
    "y.tray_missing": {"tr": "yok — panelde görünmüyorsa başlatın",
                       "en": "missing — start it if not visible in panel"},
    "y.tray_start": {"tr": "Tepsiyi başlat", "en": "Start tray"},
    "y.tray_started": {"tr": "tepsi başlatıldı", "en": "tray started"},
    "y.applet": {"tr": "Cinnamon tepsi applet'i", "en": "Cinnamon tray applet"},
    "y.direct": {"tr": "Şifresiz yazma: {ok}/{total}",
                 "en": "Passwordless writes: {ok}/{total}"},
    "y.direct_ok": {"tr": "tamamı OK ise şifre sorulmaz",
                    "en": "no password asked when all OK"},
    "y.direct_bad": {"tr": "sudo ./install.sh + yeniden başlatma gerekir",
                     "en": "needs sudo ./install.sh + reboot"},
    "y.tlp": {"tr": "TLP", "en": "TLP"},
    "y.audio": {"tr": "Ses", "en": "Audio"},
    "y.audio_tool": {"tr": "Ses aracı", "en": "Audio tool"},
    "y.thinklmi": {"tr": "think-lmi (root ile okunur)", "en": "think-lmi (root to read)"},
    "y.thinklmi_attrs": {"tr": "{n} öznitelik", "en": "{n} attributes"},
    # --- hakkında ---
    "h.machine": {"tr": "Bu makine", "en": "This machine"},
    "h.model": {"tr": "Model", "en": "Model"},
    "h.bios": {"tr": "BIOS", "en": "BIOS"},
    # --- tepsi ---
    "t.open": {"tr": "Pencereyi aç", "en": "Open window"},
    "t.quit": {"tr": "Çık", "en": "Quit"},
    "t.power": {"tr": "Güç: {prof}", "en": "Power: {prof}"},
    "t.conservation": {"tr": "Pil koruma", "en": "Battery conservation"},
    "t.running": {"tr": "litage-tray çalışıyor (tepsi)", "en": "litage-tray running (tray)"},
    "t.already": {"tr": "litage-tray zaten çalışıyor", "en": "litage-tray already running"},
    "t.no_ayatana": {"tr": "tepsi kullanılamıyor (Ayatana yok): {e}",
                     "en": "tray unavailable (no Ayatana): {e}"},
    "t.no_gui": {"tr": "GUI bulunamadı", "en": "GUI not found"},
    # --- pkexec/toast mesajları ---
    "p.cli_missing": {"tr": "CLI bulunamadı — önce ./install.sh çalıştırın (veya AppImage kullanın)",
                      "en": "CLI not found — run ./install.sh first (or use the AppImage)"},
    "p.no_pkexec": {"tr": "pkexec yok — polkit kurulu değil",
                    "en": "no pkexec — polkit is not installed"},
    "p.timeout": {"tr": "zaman aşımı (şifre diyaloğu açılmadı mı?)",
                  "en": "timeout (did the password dialog open?)"},
    "p.exec_err": {"tr": "çalıştırma hatası: {e}", "en": "execution error: {e}"},
    "p.no_agent": {"tr": "yetkilendirme aracısı yok — polkit agent kurun (Sistem sayfası)",
                   "en": "no authentication agent — install a polkit agent (System page)"},
    "p.canceled": {"tr": "iptal edildi", "en": "cancelled"},
    "p.invalid": {"tr": "geçersiz değer {v!r}: {hint}", "en": "invalid value {v!r}: {hint}"},
}


def _settings_path() -> str:
    import os
    return os.path.expanduser("~/.config/litage/settings.ini")


def get_lang() -> str:
    import configparser
    try:
        cfg = configparser.ConfigParser()
        cfg.read(_settings_path(), encoding="utf-8")
        v = cfg.get("ui", "lang", fallback="").strip().lower()
        if v in LANGS:
            return v
    except (OSError, configparser.Error):
        pass
    try:
        loc = (locale.getlocale()[0] or "")
        if loc.lower().startswith("tr"):
            return "tr"
    except Exception:
        pass
    return "en" if (os.environ.get("LANG", "").lower().startswith("en")) else "tr"


def set_lang(lang: str) -> None:
    import configparser
    import os
    if lang not in LANGS:
        return
    cfg = configparser.ConfigParser()
    try:
        cfg.read(_settings_path(), encoding="utf-8")
        if not cfg.has_section("ui"):
            cfg.add_section("ui")
        cfg.set("ui", "lang", lang)
        os.makedirs(os.path.dirname(_settings_path()), exist_ok=True)
        with open(_settings_path(), "w", encoding="utf-8") as f:
            cfg.write(f)
    except OSError:
        pass


def t(key: str, **kwargs) -> str:
    lang = get_lang()
    table = STR.get(key)
    if not table:
        return key
    s = table.get(lang) or table.get("tr") or key
    try:
        return s.format(**kwargs) if kwargs else s
    except (KeyError, IndexError, ValueError):
        return s


def check_parity() -> list[str]:
    """TR/EN anahtar eşleşme denetimi (testler kullanır)."""
    problems = []
    for key, table in STR.items():
        for lang in LANGS:
            if not table.get(lang):
                problems.append(f"{key}: {lang} eksik")
    return problems
