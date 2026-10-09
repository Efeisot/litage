"""Ayrıcalıklı çalıştırma + kurulum teşhisi.

Sorun: GUI `pkexec litage set ...` diyordu ama `litage` çoğu sistemde PATH'te
yok (kurulum yapılmamış) ve Cinnamon/Artix'te polkit *agent* hiç kurulu değil.
Sonuç: fnlock dahil tüm yazmalar sessizce ölüyordu (RC=127).

Bu modül:
  - CLI'yi bulur: kurulu `litage` -> AppImage kendisi (/proc/self/exe) ->
    repo içi `python3 -m litage.cli` fallback.
  - pkexec'i doğru hedefle çalıştırır, hatayı kullanıcı dilinde açıklar.
  - `diagnose()`: policy/udev/PATH/agent kurulu mu? GUI Sistem sayfası kullanır.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

POLICY_PATHS = [
    "/usr/share/polkit-1/actions/dev.litage.policy",
]
UDEV_PATHS = [
    "/etc/udev/rules.d/99-litage.rules",
    "/usr/lib/udev/rules.d/99-litage.rules",
]

AGENT_BINARIES = [
    "polkit-gnome-authentication-agent-1",
    "mate-polkit",
    "lxpolkit",
    "polkit-kde-authentication-agent-1",
    "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1",
    "/usr/lib/mate-polkit/polkit-mate-authentication-agent-1",
    "/usr/lib/x86_64-linux-gnu/libexec/polkit-kde-authentication-agent-1",
]


def _is_appimage() -> str | None:
    """AppImage içindeysek kendi yolumuzu döndür (fuse mount değil, .AppImage)."""
    exe = os.environ.get("APPIMAGE")
    if exe and os.path.exists(exe):
        return exe
    # /proc/self/exe AppImage runtime'ına işaret eder
    try:
        self_exe = os.readlink("/proc/self/exe")
    except OSError:
        self_exe = ""
    argv0 = sys.argv[0] if sys.argv else ""
    for cand in (argv0, self_exe):
        if cand and cand.endswith(".AppImage") and os.path.exists(cand):
            return cand
    return None


def cli_command() -> list[str] | None:
    """Yazma işlemleri için çalıştırılabilir CLI. None ise kurulum eksik."""
    found = shutil.which("litage")
    if found:
        return [found]
    app = _is_appimage()
    if app:
        return [app, "cli"]
    # repo fallback: mutlak yollu `python3 -c` (root'un cwd'sinden bağımsız;
    # `python3 -m` pkexec altında çalışma dizinine bel bağlardı).
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.exists(os.path.join(here, "litage", "cli.py")):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from litage.cli import main; sys.exit(main())" % here
        )
        return [sys.executable, "-c", code]
    return None


def run_set(feature: str, value: str, timeout: int = 60) -> tuple[bool, str]:
    """`litage set` işlemini pkexec ile çalıştır. (ok, kullanıcıya mesaj)."""
    return run_many([(feature, value)], timeout=timeout)


def run_many(pairs: list[tuple[str, str]], timeout: int = 90) -> tuple[bool, str]:
    """Toplu uygula. Önce şifresiz dener (udev izni varsa), olmazsa pkexec.

    Böylece udev kuralı işlemiş sistemlerde hiç şifre sorulmaz.
    """
    cmd = cli_command()
    if cmd is None:
        return False, "CLI bulunamadı — önce ./install.sh çalıştırın (veya AppImage kullanın)"
    args = [f"{f}={v}" for f, v in pairs]
    # 1) şifresiz deneme (hızlı)
    try:
        p = subprocess.run([*cmd, "apply", *args],
                           capture_output=True, text=True, timeout=15)
        out = (p.stdout.strip() or p.stderr.strip() or "ok")
        if p.returncode == 0:
            return True, out
        if "permission denied" not in out and "need root" not in out:
            return False, out  # kullanım/destek hatası — pkexec de çözmez
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        pass
    # 2) pkexec ile (şifre diyaloğu)
    try:
        p = subprocess.run(
            ["pkexec", *cmd, "apply", *args],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return False, "pkexec yok — polkit kurulu değil"
    except subprocess.TimeoutExpired:
        return False, "zaman aşımı (şifre diyaloğu açılmadı mı?)"
    except OSError as e:
        return False, f"çalıştırma hatası: {e}"
    out = (p.stdout.strip() or p.stderr.strip() or "ok")
    if p.returncode == 127:
        return False, "yetkilendirme aracısı yok — polkit agent kurun (Sistem sayfası)"
    if p.returncode != 0:
        # polkit iptal / auth hatası vs.
        if "dismissed" in out or "canceled" in out or not out:
            return False, "iptal edildi"
        return False, out
    return True, out


def agent_running() -> bool:
    try:
        p = subprocess.run(["ps", "-ef"], capture_output=True, text=True, timeout=5)
    except OSError:
        return False
    low = p.stdout.lower()
    return any(
        key in low
        for key in ("polkit-gnome-authentication-agent",
                    "polkit-mate-authentication-agent",
                    "lxpolkit", "polkit-kde-authentication-agent")
    )


def agent_installed() -> str | None:
    for b in AGENT_BINARIES:
        if os.path.isabs(b):
            if os.path.exists(b):
                return b
        elif shutil.which(b):
            return shutil.which(b)
    return None


def cinnamon_tray_applet() -> tuple[bool, str]:
    """Cinnamon panelinde system-tray/status applet'i var mı? (tepsi görünürlüğü)."""
    try:
        p = subprocess.run(
            ["gsettings", "get", "org.cinnamon", "enabled-applets"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"gsettings okunamadı: {e}"
    if p.returncode != 0:
        return False, "cinnamon değil veya şema yok"
    txt = p.stdout.lower()
    for key in ("systray", "status", "appindicator", "tray"):
        if key in txt:
            return True, f"etkin applet bulundu ({key})"
    return False, "panelde tepsi applet'i yok — Sistem Tepsisi appletini ekleyin"


def diagnose() -> dict:
    """Kurulum teşhisi — GUI Sistem sayfası ve `litage doctor` kullanır."""
    pol = next((p for p in POLICY_PATHS if os.path.exists(p)), None)
    udev = next((p for p in UDEV_PATHS if os.path.exists(p)), None)
    return {
        "cli": cli_command(),
        "cli_on_path": shutil.which("litage"),
        "pkexec": shutil.which("pkexec"),
        "policy": pol,
        "udev": udev,
        "udev_helper": shutil.which("litage-udev-fix"),
        "agent_bin": agent_installed(),
        "agent_running": agent_running(),
        "appimage": _is_appimage(),
        "direct_writable": direct_writable(),
    }


# şifresiz yazılabilen kritik düğümler (udev kuralı işlemişse True)
DIRECT_NODES = [
    "/sys/bus/platform/devices/VPC2004:00/fn_lock",
    "/sys/bus/platform/devices/VPC2004:00/conservation_mode",
    "/sys/bus/platform/devices/VPC2004:00/fan_mode",
    "/sys/class/leds/platform::kbd_backlight/brightness",
    "/sys/firmware/acpi/platform_profile",
]


def direct_writable() -> dict:
    """Her kritik düğüm için W_OK — şifresiz çalışmanın gerçek ölçütü."""
    return {p: os.access(p, os.W_OK) for p in DIRECT_NODES if os.path.exists(p)}


def doctor_text() -> str:
    d = diagnose()
    lines = []
    lines.append(f"CLI: {' '.join(d['cli']) if d['cli'] else 'BULUNAMADI'}")
    lines.append(f"pkexec: {d['pkexec'] or 'YOK'}")
    lines.append(f"polkit policy: {d['policy'] or 'KURULU DEĞİL (./install.sh)'}")
    lines.append(f"udev kuralı: {d['udev'] or 'KURULU DEĞİL (./install.sh)'}")
    lines.append(f"agent binary: {d['agent_bin'] or 'KURULU DEĞİL'}")
    lines.append(f"agent çalışıyor: {'evet' if d['agent_running'] else 'HAYIR — şifre penceresi çıkmaz'}")
    dw = d.get("direct_writable", {})
    if dw:
        n_ok = sum(1 for v in dw.values() if v)
        lines.append(f"şifresiz yazma: {n_ok}/{len(dw)} düğüm")
        for p, ok in dw.items():
            lines.append(f"  [{'OK' if ok else 'KÖK GEREKİR'}] {p}")
        if n_ok < len(dw):
            lines.append("ipucu: sudo ./install.sh (udev tetiklenir) veya yeniden başlatın")
    return "\n".join(lines)
