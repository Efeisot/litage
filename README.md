# Litage

Lenovo Vantage / Legion Zone alternatifi — Linux için, distro ve init agnostic.

> LenovoLegionToolkit (Windows, C# / WPF) ve LenovoLegionLinux (Linux, kernel modülü +
> Python/Qt) projelerinden ilhamla, ama **herhangi bir Lenovo laptop + herhangi bir
> distro + herhangi bir init** ile çalışacak şekilde sıfırdan yazıldı.
> Hedef makine: Lenovo Yoga 7 2-in-1 14AKP10 (83JR, QXCN BIOS, AMD Ryzen AI 7 350,
> iGPU-only) + Artix Linux OpenRC — ama Legion/LOQ/IdeaPad/Slim/ThinkBook'ta da çalışır.

## Neden yeni proje?

| | LenovoLegionToolkit (Win) | LenovoLegionLinux | Litage |
|---|---|---|---|
| Platform | Sadece Windows | Sadece Legion (kernel modülü + allowlist) | Herhangi bir Linux, modülsüz |
| Yoga 14AKP10 | ITS-mode-only, 2. sınıf | Allowlist dışı — yüklenmiyor | Birincil hedef, natif backend |
| Init | N/A | systemd (+deneysel OpenRC) | systemd + OpenRC + runit + dinit + s6 + sysvinit |
| UI | WPF | PyQt6 | GTK4/LibAdwaita, LLT tarzı sol-sidebar + tepsi |
| Fan curve / GodMode / RGB | Var (Legion WMI) | Var (EC/WMI) | Legion'da varsa gösterilir, Yoga'da gizlenir |
| TLP | Yok | Yok (sıfır eşleşme) | Tamamlayıcı entegrasyon (tek opsiyonel bağımlılık) |
| Dağıtım | Installer | DKMS/paket | install.sh + **AppImage** + menü + autostart |

Yoga 14AKP10'da **Legion EC/WMI backend çalışmaz** (canlı doğrulama):
`887B54E3 GAMEZONE`, `14AFD777 CPU`, `DA7547F1 GPU`, `92549549 FAN` GUID'leri
`/sys/bus/wmi/devices/` altında **yok**. Sadece `8FC0DE0C ideapad` +
`8C5B9127 kbd-backlight` + `DC2A8805 other` var. Bu yüzden Litage varsayılan olarak
standart çekirdek arayüzlerini kullanır: `ideapad-laptop (VPC2004)`,
`platform_profile` (`ideapad-laptop` + `amd-pmf`), `think-lmi`, `amd-pstate-epp`,
`amdgpu/k10temp hwmon`, `upower`, `rfkill`.

## Özellikler (yetenek bazlı — desteklenmeyen gizlenir)

- **Güç profili**: `low-power / balanced / performance` (platform_profile, çift sağlayıcı senkronu)
- **CPU**: governor (`powersave/performance`), EPP (`performance/balance_performance/...`),
  boost aç/kapa, frekans okuma
- **ideapad**: `conservation_mode`, `fan_mode`, `fn_lock`, `camera_power`, `usb_charging`,
  klavye arka ışığı (0-2), fn-lock LED
- **think-lmi**: BIOS'tan okunan `HotkeyMode/FoolProofFnCtrl/FlipBoot/AlwaysOnUsb/...` (root ile)
- **Pil**: kapasite/durum/şarj tipi (`Fast/Standard/Long_Life`), upower istatistikleri
- **Ekran**: parlaklık (`amdgpu_bl1`), çözünürlük/yenileme (xrandr, salt-okunur liste)
- **RF**: uçak modu / wifi / bluetooth (rfkill)
- **Ses**: mikrofon/hoparlör mute (amixer/wpctl ile, varsa)
- **Sensörler**: `sensors`/hwmon okuma (CPU/GPU/NVMe/pil)
- **Legion (opsiyonel)**: `legion_laptop` modülü yüklüyse Legion sayfası otomatik açılır —
  LLL `legion.py` referanslı backend: `lockfancontroller/fan_unlock/rapidcharge/winkey/
  overdrive/gsync/instant_boot/fan_fullspeed/cpu_oc/gpu_oc`, güç limitleri
  (`cpu_longterm_powerlimit` vb.), fan curve okuma, LLL preset dizini
  (`/etc/legion_linux`) ile uyumluluk. Conservation↔rapidcharge mutual-exclusion
  LLL ile aynı.
- **ThinkPad (opsiyonel)**: `thinkpad_acpi` varsa fan/LED okuma.
- **TLP (tek opsiyonel bağımlılık)**: `tlp-stat` okuma, `tlp ac/battery` zorlama,
  `tlp setcharge` eşikleri. TLP + litaged çakışmaması için: preset'te governor/epp
  BOŞSA TLP yönetir, DOLUYSA litaged yönetir.
- **dGPU (opsiyonel)**: NVIDIA varsa sayfa açılır, yoksa (bu Yoga gibi) **hiç gösterilmez**
- **Otomasyon (`litaged`)**: AC/pil + güç profiline göre EPP/governor/ideapad preset uygular
- **Arayüz**: LLT tarzı ikon-ray sidebar (58px ikon, hover/pin ile 188px'e animasyonlu
  açılır) + sağ içerik + toast + tepsi. Desteklenmeyen bölüm gizlenmez —
  kilitli gösterilir (YOK rozeti, tıklayınca nedenini söyler).
- **Toplu kaydet**: anahtar/combo değişikliği beklemeye alınır, alttaki
  **Kaydet (tek şifre)** çubuğu `litage apply f=v ...` ile tek pkexec'te uygular.
  Tek tek şifre dönemi bitti. Vazgeç sayfayı eski haline döndürür.
- **Sağ tık**: kart/satır/sidebar'da bağlam menüsü (kopyala/yenile/terminal komutu).
- **Temalar**: saf siyah (#000) / koyu / gri / beyaz — Ayarlar'dan, kalıcı.
- **Teşhis**: `litage doctor` + GUI Sistem sayfası — policy/udev/agent/tepsi-applet
  eksikse söyler, tek komutla kurulum verir (`sudo ./install.sh --autostart`).
  Tepsi ayrı `litage-tray` sürecidir (GTK3+Ayatana; GTK4'e gömülemez).
- **Sağ tık**: kart/satır/sidebar'da bağlam menüsü (kopyala/yenile/terminal komutu).
- **Temalar**: saf siyah (#000) / koyu / gri / beyaz — Ayarlar'dan, kalıcı.
- **Teşhis**: `litage doctor` + GUI Sistem sayfası — policy/udev/agent eksikse
  söyler, tek komutla kurulum verir (`sudo ./install.sh --autostart`).
  Yazmalar pkexec + polkit agent üzerinden (şifre penceresi).

## Kurulum (distro agnostic)

```bash
git clone <repo> && cd Litage
./install.sh                  # pacman/apt/dnf/zypper/xbps/apk algılar, udev+polkit+init kurar
./install.sh --autostart       # + açılışta başlat (tepsiye küçültülmüş, Cinnamon dahil)
./install.sh --no-tlp          # TLP kurmadan (önerilmez — TLP tamamlayıcıdır)
./install.sh --uninstall
```

Bağımlılık: `python3, python-gobject, gtk4, libadwaita` + tek opsiyonel: `tlp`
(+`upower, rfkill`, tepsi için `libayatana-appindicator`).
Derleme gerektirmez, çekirdek modülü yoktur.

## AppImage (taşınabilir, menü + autostart)

```bash
./packaging/build-appimage.sh   # -> Litage-x86_64.AppImage (~1MB, sistem GTK'sını kullanır)
./Litage-x86_64.AppImage status # CLI aynı dosyadan çalışır
./Litage-x86_64.AppImage        # GUI
./install.sh --appimage-menu    # AppImage'ı menüye ekle (~/.local/share/applications)
```

Autostart manuel: `litage-gui` Ayarlar sayfasındaki "Açılışta başlat" anahtarı
`~/.config/autostart/litage-gui.desktop` yazar (XDG — Cinnamon/GNOME/KDE okur).

## Kullanım

```bash
litage status                 # tüm yetenekler + değerler (renksiz, script-friendly)
litage list                   # desteklenen feature'lar (bu makinede geçerli olanlar)
litage get platform_profile   # low-power|balanced|performance
sudo litage set platform_profile performance
sudo litage set conservation on
sudo litage set fn_lock off
sudo litage set fan_mode 1
sudo litage set kbd_backlight 2
sudo litage set epp balance_power
litage monitor                # 1 sn aralıklı sensör dökümü
litage-gui                    # GTK4/LibAdwaita, sadece desteklenen sayfalar
sudo litaged --once           # preset'i bir kez uygula (test)
```

Config: `/etc/litage/litaged.conf`, presetler `/etc/litage/profiles/*.yaml`:

```yaml
# /etc/litage/profiles/balanced-ac.yaml
platform_profile: balanced
governor: powersave
epp: balance_performance
fan_mode: 1
kbd_backlight: 1
```

## Daemon (init agnostic)

`litaged` saf Python'dur, systemd'ye bağımlı değildir. `install.sh --init auto`
şunu kurar:

| init | dosya |
|---|---|
| systemd | `daemon/init/systemd/litaged.service` |
| OpenRC | `daemon/init/openrc/litaged` (`/etc/init.d/litaged`) |
| runit | `daemon/init/runit/litaged/run` (`/etc/sv/litaged`) |
| dinit | `daemon/init/dinit/litaged` (`/etc/dinit.d/litaged`) |
| s6 | `daemon/init/s6/litaged/{run,type}` (`/etc/s6/sv/litaged`) |
| sysvinit | `daemon/init/sysvinit/litaged` (`/etc/init.d/litaged`) |

Manuel: `sudo litaged` (foreground), `sudo litaged --daemon` (fork).

## Proje yapısı

```
litage/                 # python paketi
  capabilities.py       # DMI+sysfs taraması, Capability dataclass
  backends/             # her biri: detect() + get/set, sysfs-only
    ideapad.py platform_profile.py cpufreq.py battery.py
    backlight.py rfkill.py audio.py thinklmi.py sensors.py
    legion.py nvidia.py display.py
  cli.py gui.py daemon.py automation.py utils.py
daemon/init/...         # 6 init sistemi
packaging/              # PKGBUILD, spec, install.sh
tests/                  # pytest, donanımsız mock-sysfs ile çalışır
```

## Güvenlik

Donanıma yazan her şey sysfs üzerinden ve çekirdeğin izin verdiği aralıkta
(LLL'deki gibi ham EC yazımı yok). Tehlikeli bayrak (`fan_unlock`, EC offset)
yoktur. Yazma işlemleri root ister; GUI polkit ile yükselir, CLI `sudo` ister.

## Lisans

GPL-3.0-or-later (LenovoLegionToolkit ile uyumlu).
