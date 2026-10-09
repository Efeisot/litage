#!/bin/sh
# litage-polkit-agent — distro agnostic polkit agent başlatıcı.
# Cinnamon/Artix'te oturumda agent çalışmadığı için pkexec diyaloğu hiç
# çıkmıyordu. Bu sarmalayıcı kurulu olan ilk agent'ı çalıştırır.
# XDG autostart (.desktop) ile oturum başında başlatılır.
for b in \
  /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 \
  /usr/lib/mate-polkit/polkit-mate-authentication-agent-1 \
  /usr/lib/x86_64-linux-gnu/libexec/polkit-kde-authentication-agent-1 \
  /usr/lib64/libexec/polkit-kde-authentication-agent-1 \
  polkit-gnome-authentication-agent-1 \
  mate-polkit \
  lxpolkit \
  polkit-kde-authentication-agent-1
do
  case "$b" in
    /*) [ -x "$b" ] && exec "$b" ;;
    *) command -v "$b" >/dev/null 2>&1 && exec "$b" ;;
  esac
done
echo "litage-polkit-agent: agent bulunamadı (polkit-gnome veya mate-polkit kurun)" >&2
exit 1
