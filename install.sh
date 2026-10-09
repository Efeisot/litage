#!/bin/sh
# Litage distro+init agnostic installer. No build, no kernel module.
# Supports: pacman(arch/artix) apt(debian/ubuntu) dnf(fedora) zypper(suse)
#           xbps(void) apk(alpine) emerge(gentoo) nix
# Inits: systemd openrc runit dinit s6 sysvinit (auto-detected, or --init NAME)
set -eu
PREFIX="${PREFIX:-/usr/local}"
INIT="auto"
UNINSTALL=0
WITH_TLP=1
AUTOSTART=0
APPIMAGE_MENU=0
for a in "$@"; do
  case "$a" in
    --init=*) INIT="${a#--init=}" ;;
    --uninstall) UNINSTALL=1 ;;
    --prefix=*) PREFIX="${a#--prefix=}" ;;
    --no-tlp) WITH_TLP=0 ;;
    --autostart) AUTOSTART=1 ;;
    --appimage-menu) APPIMAGE_MENU=1 ;;
    --help|-h) echo "Usage: install.sh [--init=...] [--prefix=DIR] [--no-tlp] [--autostart] [--appimage-menu] [--uninstall]"; exit 0 ;;
  esac
done
HERE="$(cd "$(dirname "$0")" && pwd)"

detect_pm() {
  command -v pacman >/dev/null && { echo pacman; return; }
  command -v apt-get >/dev/null && { echo apt; return; }
  command -v dnf >/dev/null && { echo dnf; return; }
  command -v zypper >/dev/null && { echo zypper; return; }
  command -v xbps-install >/dev/null && { echo xbps; return; }
  command -v apk >/dev/null && { echo apk; return; }
  command -v emerge >/dev/null && { echo emerge; return; }
  echo unknown
}
detect_init() {
  [ "$INIT" != auto ] && { echo "$INIT"; return; }
  [ -d /run/systemd/system ] && command -v systemctl >/dev/null && { echo systemd; return; }
  command -v rc-service >/dev/null && { echo openrc; return; }
  [ -d /run/runit ] && { echo runit; return; }
  command -v dinitctl >/dev/null && { echo dinit; return; }
  command -v s6-svscan >/dev/null && { echo s6; return; }
  [ -d /etc/init.d ] && { echo sysvinit; return; }
  echo none
}

if [ "$UNINSTALL" = 1 ]; then
  rm -f "$PREFIX/bin/litage" "$PREFIX/bin/litage-gui" "$PREFIX/bin/litaged"
  rm -rf "$PREFIX/lib/litage"
  echo "uninstalled binaries (config in /etc/litage kept)"
  exit 0
fi

PM="$(detect_pm)"
echo "== package manager: $PM"
TLP_PKG=""
[ "$WITH_TLP" = 1 ] && TLP_PKG="tlp"
# polkit agent: Cinnamon/Artix'te oturumda agent yoksa pkexec diyaloğu çıkmaz.
# GNOME/Cinnamon uyumlu ilk agent paketlenir (distro agnostic).
case "$PM" in
  pacman) AGENT_PKG="polkit-gnome" ;;
  apt) AGENT_PKG="policykit-1-gnome" ;;
  dnf) AGENT_PKG="mate-polkit" ;;
  zypper) AGENT_PKG="polkit-gnome" ;;
  xbps) AGENT_PKG="mate-polkit" ;;
  apk) AGENT_PKG="mate-polkit" ;;
  emerge) AGENT_PKG="mate-polkit" ;;
  *) AGENT_PKG="" ;;
esac
case "$PM" in
  pacman) sudo pacman -S --needed python python-gobject python-yaml gtk4 libadwaita upower rfkill libayatana-appindicator $TLP_PKG $AGENT_PKG ;;
  apt) sudo apt-get install -y python3 python3-gi python3-yaml gir1.2-gtk-4.0 gir1.2-adw-1 upower rfkill gir1.2-ayatanaappindicator3-0.1 $TLP_PKG $AGENT_PKG ;;
  dnf) sudo dnf install -y python3 python3-gobject python3-yaml gtk4 libadwaita upower rfkill libayatana-appindicator-gtk3 $TLP_PKG $AGENT_PKG ;;
  zypper) sudo zypper install -y python3 python3-gobject python3-PyYAML gtk4 libadwaita upower rfkill typelib-1_0-AyatanaAppIndicator3-0_1 $TLP_PKG $AGENT_PKG ;;
  xbps) sudo xbps-install -Sy python3 python3-gobject python3-yaml gtk4 libadwaita upower rfkill libayatana-appindicator $TLP_PKG $AGENT_PKG ;;
  apk) sudo apk add python3 py3-gobject py3-yaml gtk4.0 libadwaita upower rfkill libayatana-appindicator $TLP_PKG $AGENT_PKG ;;
  emerge) sudo emerge -av dev-python/pygobject dev-python/pyyaml gui-libs/gtk gui-libs/libadwaita sys-apps/upower sys-apps/rfkill dev-libs/libayatana-appindicator sys-power/tlp mate-polkit ;;
  *) echo "unknown package manager — install manually: python3, pygobject, pyyaml, gtk4, libadwaita (+tlp +polkit agent)";;
esac

echo "== installing python package to $PREFIX/lib/litage"
sudo mkdir -p "$PREFIX/lib/litage" "$PREFIX/bin" /etc/litage/profiles
sudo cp -r "$HERE/litage" "$PREFIX/lib/litage/"
# NOT: paket $PREFIX/lib/litage/litage/ altina kopyalanir, o yuzden
# PYTHONPATH paketin bir ustu ($PREFIX/lib/litage) olmalidir.
printf '#!/bin/sh\nexec env PYTHONPATH=%s/litage python3 -m litage.cli "$@"\n' "$PREFIX" | sudo tee "$PREFIX/bin/litage" >/dev/null
printf '#!/bin/sh\nexec env PYTHONPATH=%s/litage python3 -m litage.gui "$@"\n' "$PREFIX" | sudo tee "$PREFIX/bin/litage-gui" >/dev/null
printf '#!/bin/sh\nexec env PYTHONPATH=%s/litage python3 -m litage.daemon "$@"\n' "$PREFIX" | sudo tee "$PREFIX/bin/litaged" >/dev/null
printf '#!/bin/sh\nexec env PYTHONPATH=%s/litage python3 -m litage.tray "$@"\n' "$PREFIX" | sudo tee "$PREFIX/bin/litage-tray" >/dev/null
echo "export PYTHONPATH=$PREFIX/lib/litage:\$PYTHONPATH" | sudo tee /etc/profile.d/litage.sh >/dev/null || true
sudo chmod +x "$PREFIX/bin/litage" "$PREFIX/bin/litage-gui" "$PREFIX/bin/litaged" "$PREFIX/bin/litage-tray"

[ -f /etc/litage/litaged.conf ] || sudo cp "$HERE/daemon/litaged.conf" /etc/litage/litaged.conf
sudo cp "$HERE"/daemon/profiles/*.yaml /etc/litage/profiles/
sudo cp "$HERE/packaging/99-litage.rules" /etc/udev/rules.d/ 2>/dev/null || true
sudo cp "$HERE/packaging/litage-udev-fix.sh" "$PREFIX/bin/litage-udev-fix" 2>/dev/null || true
sudo chmod +x "$PREFIX/bin/litage-udev-fix" 2>/dev/null || true
# RUN yolu PREFIX'e göre düzeltilir
sudo sed -i "s|/usr/local/bin/litage-udev-fix|$PREFIX/bin/litage-udev-fix|" /etc/udev/rules.d/99-litage.rules 2>/dev/null || true
sudo udevadm control --reload-rules 2>/dev/null || true
sudo udevadm trigger --subsystem-match=platform --subsystem-match=power_supply --subsystem-match=leds --subsystem-match=backlight --subsystem-match=platform-profile --subsystem-match=firmware-attributes --subsystem-match=cpu 2>/dev/null || true
# policy: PREFIX'e göre exec yolunu düzelt (/usr/local/bin/litage varsayılan)
sed "s|/usr/local/bin/litage|$PREFIX/bin/litage|" "$HERE/packaging/dev.litage.policy" \
  | sudo tee /usr/share/polkit-1/actions/dev.litage.policy >/dev/null 2>&1 || true
# özel ikonlar (fan/klavye/cpu/termometre) — hicolor scalable/apps
for ic in "$HERE"/packaging/icons/*.svg; do
  sudo cp "$ic" /usr/share/icons/hicolor/scalable/apps/ 2>/dev/null || true
done
# polkit agent sarmalayıcı + oturum autostart'ı (şifre diyaloğu için şart)
sudo cp "$HERE/packaging/litage-polkit-agent.sh" "$PREFIX/bin/litage-polkit-agent" 2>/dev/null || true
sudo chmod +x "$PREFIX/bin/litage-polkit-agent" 2>/dev/null || true
sudo cp "$HERE/packaging/litage-polkit-agent.desktop" /etc/xdg/autostart/ 2>/dev/null || true
# DİKKAT: agent OTURUM SAHİBİ olarak çalışmalı (root olarak değil!).
if [ -n "${SUDO_USER:-}" ]; then
  sudo -u "$SUDO_USER" "$PREFIX/bin/litage-polkit-agent" >/dev/null 2>&1 &
  echo "polkit agent $SUDO_USER olarak başlatıldı (/etc/xdg/autostart kalıcı)"
else
  "$PREFIX/bin/litage-polkit-agent" >/dev/null 2>&1 &
  echo "polkit agent başlatıldı (/etc/xdg/autostart kalıcı)"
fi
# menü girişi (yeni ad + geriye uyumlu eski ad)
sudo cp "$HERE/packaging/dev.litage.app.desktop" /usr/share/applications/ 2>/dev/null || true
sudo cp "$HERE/packaging/dev.litage.app.svg" /usr/share/icons/hicolor/scalable/apps/ 2>/dev/null || true
sudo gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true
# AppImage menü entegrasyonu (appimage --appimage-menü sonrası)
if [ "$APPIMAGE_MENU" = 1 ] && [ -f "$HERE/Litage-x86_64.AppImage" ]; then
  mkdir -p "$HOME/.local/share/applications" "$HOME/.local/bin"
  cp "$HERE/Litage-x86_64.AppImage" "$HOME/.local/bin/" 2>/dev/null || true
  sed "s|^Exec=.*|Exec=$HOME/.local/bin/Litage-x86_64.AppImage|" \
    "$HERE/packaging/dev.litage.app.desktop" > "$HOME/.local/share/applications/dev.litage.app.desktop"
  update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
  echo "AppImage menüye eklendi."
fi
# autostart (kullanıcı oturumu — Cinnamon dahil tüm XDG masaüstleri)
if [ "$AUTOSTART" = 1 ]; then
  mkdir -p "$HOME/.config/autostart"
  cp "$HERE/packaging/litage-gui-autostart.desktop" "$HOME/.config/autostart/litage-gui.desktop"
  echo "autostart açıldı (~/.config/autostart/litage-gui.desktop)"
fi

INIT_SYS="$(detect_init)"
echo "== init system: $INIT_SYS"
case "$INIT_SYS" in
  systemd) sudo cp "$HERE/daemon/init/systemd/litaged.service" /etc/systemd/system/; sudo systemctl daemon-reload || true; echo "enable with: sudo systemctl enable --now litaged" ;;
  openrc) sudo cp "$HERE/daemon/init/openrc/litaged" /etc/init.d/litaged; sudo chmod +x /etc/init.d/litaged; echo "enable with: sudo rc-update add litaged default && sudo rc-service litaged start" ;;
  runit) sudo mkdir -p /etc/sv/litaged; sudo cp "$HERE/daemon/init/runit/litaged/run" /etc/sv/litaged/run; sudo chmod +x /etc/sv/litaged/run; echo "enable with: sudo ln -s /etc/sv/litaged /var/service/" ;;
  dinit) sudo cp "$HERE/daemon/init/dinit/litaged" /etc/dinit.d/litaged; echo "enable with: sudo dinitctl enable litaged" ;;
  s6) sudo mkdir -p /etc/s6/sv/litaged; sudo cp "$HERE/daemon/init/s6/litaged/run" /etc/s6/sv/litaged/run; sudo cp "$HERE/daemon/init/s6/litaged/type" /etc/s6/sv/litaged/type; sudo chmod +x /etc/s6/sv/litaged/run ;;
  sysvinit) sudo cp "$HERE/daemon/init/sysvinit/litaged" /etc/init.d/litaged; sudo chmod +x /etc/init.d/litaged; echo "enable with: sudo update-rc.d litaged defaults" ;;
  none) echo "no init detected — run manually: sudo litaged" ;;
esac
echo "done. try: litage status"
