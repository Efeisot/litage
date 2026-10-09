#!/bin/sh
# litage-udev-fix — sysfs yazma izinlerini power/video gruplarına açar.
# udev GROUP=/MODE= anahtarları /dev düğümü olmayan sysfs özniteliklerine
# İŞLEMEZ; bu yüzden RUN ile bu yardımcı çağrılır (root olarak çalışır).
# Idempotent: dosya yoksa atlanır. install.sh kurar, udev tetikler.
fix() {
  # $1=dosya $2=grup
  [ -e "$1" ] || return 0
  chgrp "$2" "$1" 2>/dev/null || return 0
  chmod g+w "$1" 2>/dev/null || true
}
VPC="/sys/bus/platform/devices/VPC2004:00"
if [ -d "$VPC" ]; then
  for n in conservation_mode fan_mode fn_lock camera_power usb_charging touchpad; do
    fix "$VPC/$n" power
  done
fi
for f in /sys/class/leds/platform::*; do
  [ -e "$f" ] || continue
  fix "$f/brightness" power
done
for f in /sys/class/backlight/*; do
  [ -e "$f" ] || continue
  fix "$f/brightness" video
done
for f in /sys/class/platform-profile/*; do
  [ -e "$f" ] || continue
  fix "$f/profile" power
done
for f in /sys/devices/system/cpu/cpufreq/policy*/scaling_governor \
         /sys/devices/system/cpu/cpufreq/policy*/energy_performance_preference \
         /sys/devices/system/cpu/cpufreq/boost; do
  [ -e "$f" ] || continue
  fix "$f" power
done
# think-lmi okuma (root ister; gruba okuma izni yeterli)
for f in /sys/class/firmware-attributes/thinklmi/attributes/*/current_value; do
  [ -e "$f" ] || continue
  chgrp power "$f" 2>/dev/null || true
  chmod g+r "$f" 2>/dev/null || true
done
exit 0
