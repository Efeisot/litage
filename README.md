# Litage — `BETA`

Lenovo Vantage / Legion Zone alternatifi — Linux için, distro ve init agnostic.

> **Beta uyarısı:** Bu araç geliştirme aşamasındadır. Arayüz ve komutlar değişebilir,
> bazı donanımlarda bazı düğmeler çalışmayabilir. Yazma işlemleri yalnızca çekirdeğin
> izin verdiği sysfs düğümlerine yapılır (ham EC yazımı yok), yine de dizüstü
> bilgisayarınızda denemeden önce `litage doctor` çıktısını kontrol edin.
> Hata bildirirken `litage status --json` çıktısını ekleyin.

LenovoLegionToolkit (Windows) ve LenovoLegionLinux (Linux) projelerinden ilhamla,
ama **herhangi bir Lenovo laptop + herhangi bir distro + herhangi bir init** ile
çalışacak şekilde yazıldı. Birincil test makinesi: Lenovo Yoga 7 2-in-1 14AKP10
(83JR, AMD Ryzen AI 7 350, iGPU) + Artix Linux (OpenRC) + Cinnamon (X11).

## Karşılaştırma

| | LenovoLegionToolkit (Win) | LenovoLegionLinux | Litage (beta) |
|---|---|---|---|
| Platform | Sadece Windows | Sadece Legion (çekirdek modülü + allowlist) | Herhangi bir Linux, modülsüz |
| Yoga/IdeaPad | Kısıtlı (ITS-only) | Allowlist dışı | Birincil hedef, natif backend |
| Legion/LOQ | Tam | Tam (EC/WMI) | Modül varsa Legion sayfası açılır (LLL uyumlu) |
| Init | — | systemd (+deneysel OpenRC) | systemd + OpenRC + runit + dinit + s6 + sysvinit |
| Arayüz | WPF | PyQt6 | GTK4/LibAdwaita, statik sidebar + tepsi |
| TLP | Yok | Yok | Tamamlayıcı entegrasyon (tek opsiyonel bağımlılık) |
| Dağıtım | Installer | DKMS/paket | install.sh + **AppImage** + menü + autostart |

Not: Yoga/IdeaPad'de **Legion EC/WMI backend çalışmaz** (donanımsal yokluk —
`GAMEZONE/CPU/GPU/FAN` WMI GUID'leri bu cihazlarda mevcut değil). Litage bu yüzden
standart çekirdek arayüzlerini kullanır: `ideapad-laptop (VPC2004)`,
`platform_profile` (`ideapad-laptop` + `amd-pmf`), `think-lmi`, `amd-pstate-epp`,
`amdgpu/k10temp hwmon`, ortam ışığı sensörü (ALS), `upower`, `rfkill`.

## Özellikler

Desteklenmeyen donanım gizlenmez — kilitli gösterilir (YOK rozeti, tıklayınca
nedenini söyler). Legion/NVIDIA, destekli makinede otomatik açılır.

- **Güç profili**: `low-power / balanced / performance` (çift sağlayıcı senkronu)
- **CPU**: governor, EPP, boost, frekans okuma
- **Lenovo (ideapad)**: pil koruma, fan modu, Fn-Lock, kamera, kapalıyken USB şarj,
  klavye arka ışığı (0–2) + **otomatik parlaklık** (ALS varsa; daemon yönetir,
  eşikler `litaged.conf` `[keyboard]` bölümünde)
- **Pil**: kapasite/durum/şarj tipi, upower istatistikleri, pil sağlığı (%)
- **Ekran**: parlaklık; **Bağlantı**: Wi-Fi/Bluetooth (rfkill); **Ses**: mic/hoparlör
- **Sensörler + canlı grafikler**: CPU/GPU sıcaklığı ve frekansı (2 sn çizgi grafik)
- **Legion (modül varsa)**: güç limitleri, fan eğrisi okuma/grafik, LLL preset uyumu
- **ThinkPad / dGPU**: varsa ilgili sayfa açılır, yoksa kilitli durur
- **TLP**: profil okuma/zorlama, şarj eşikleri (`tlp setcharge`)
- **Otomasyon (`litaged`)**: AC/pil × profile göre preset + klavye oto + ALS

## Arayüz

- Statik ikonlu sol panel (Genel Bakış, Pil, Klavye, Fan Eğrisi, Legion, Harici GPU,
  Otomasyon, Ayarlar, Sistem, Hakkında) + sağ içerik + bildirimler.
- **Toplu kaydet**: değişiklikler beklemeye alınır, başlıktaki **Kaydet** tek
  şifreyle hepsini uygular (`litage apply`), Vazgeç geri alır.
- Çoğu yazma **şifresizdir** (udev kuralları `power`/`video` grubuna izin verir);
  kalanı pkexec + polkit ile (tek şifre, oturum boyu hatırlanır).
- Sağ tık menüleri (kopyala/yenile/terminal komutu), 4 tema
  (saf siyah `#000` / koyu / gri / beyaz), sensör renk kodları.
- Kapat düğmesi davranışı ayarlanabilir: tepsiye küçült ya da tümden çık.
- Tepsi ayrı `litage-tray` sürecidir (GTK3+Ayatana — GTK4'e gömülemez):
  canlı durum satırı (profil · sıcaklık · pil · W · MHz), profil değiştirme,
  pencere aç/kapat.

## Kurulum (distro agnostic)

```bash
git clone <repo> && cd Litage
sudo ./install.sh              # bağımlılık + udev + polkit + init + menü + ikon
sudo ./install.sh --autostart  # + açılışta başlat (Cinnamon dahil tüm XDG)
sudo ./install.sh --no-tlp     # TLP'siz (önerilmez)
sudo ./install.sh --uninstall
```

Bağımlılık: `python3, python-gobject, gtk4, libadwaita` + tek opsiyonel `tlp`
(+`upower, rfkill`, tepsi için `libayatana-appindicator`, şifre diyaloğu için
polkit agent — örn. `polkit-gnome`). Derleme ve çekirdek modülü yoktur.

Kurulum sonrası **yeniden başlatma önerilir** (udev + agent oturumu için).
Durumu `litage doctor` veya GUI'deki Sistem sayfası gösterir
(`şifresiz yazma: 5/5` hedeflenir).

## AppImage

```bash
./packaging/build-appimage.sh   # -> Litage-x86_64.AppImage (~1MB, sistem GTK'sını kullanır)
./Litage-x86_64.AppImage status # CLI aynı dosyadan çalışır
./Litage-x86_64.AppImage        # GUI
sudo ./install.sh --appimage-menu  # AppImage'ı menüye ekle
```

## Kullanım

```bash
litage status                 # her şey (insan okunur); --json ile makine okunur
litage list                   # BU makinede yazılabilir özellikler
litage get lux                # ortam ışığı (ALS varsa)
litage get platform_profile
sudo litage set fn_lock on
sudo litage set kbd_auto on   # klavye oto-parlaklık (daemon gerekir)
litage apply platform_profile=balanced fn_lock=on   # toplu (tek şifre)
litage monitor -n 5           # sensör dökümü
litage doctor                 # kurulum teşhisi
litage-gui                    # grafik arayüz [--minimized] [--page pil]
sudo litaged --once           # daemon presetini bir kez uygula (test)
```

Config: `/etc/litage/litaged.conf`, presetler `/etc/litage/profiles/*.yaml`,
GUI tercihleri `~/.config/litage/` (tema, kapatma davranışı, autostart).

## Daemon (init agnostic)

`litaged` saf Python'dur. `install.sh` init'i otomatik algılar
(systemd/OpenRC/runit/dinit/s6/sysvinit). Manuel: `sudo litaged` (ön plan),
`sudo litaged --daemon` (arka plan).

## Sorun giderme (beta)

- `litage doctor` ilk bakılacak yerdir: policy/udev/agent + şifresiz düğümler.
- Yazma çalışmıyorsa: `sudo ./install.sh` yeniden çalıştır + yeniden başlat.
  Sistem kısmi yükseltmedeyse (`pacman.log` kontrolü) önce `sudo pacman -Syu`.
- TLP ile çakışma: preset'te `governor`/`epp` boşsa TLP yönetir, doluysa litaged.
- Tepsi görünmüyorsa: Cinnamon'da Sistem Tepsisi applet'i etkin olmalı;
  GUI Sistem sayfasındaki "Tepsiyi başlat" denenebilir.

## Proje yapısı

```
litage/
  capabilities.py   # DMI+sysfs taraması (Capability)
  privileged.py     # pkexec/CLI çözümleme, kurulum teşhisi (doctor)
  themes.py prefs.py autostart.py icons_pkg.py
  cli.py gui.py daemon.py tray.py utils.py
  backends/         # ideapad, platform_profile, cpufreq, battery, backlight,
                    # rfkill, audio, thinklmi, sensors, legion (LLL uyumlu),
                    # tlp, thinkpad, als, optional
  icons/            # gömülü SVG ikonlar
daemon/             # litaged.conf, profiles/*.yaml, init/* (6 init)
packaging/          # install.sh, build-appimage.sh, PKGBUILD, policy,
                    # udev rules + helper, .desktop dosyaları
tests/              # donanımsız + canlı salt-okunur testler
```

## Güvenlik

Yazmalar yalnızca çekirdeğin açtığı sysfs düğümlerine ve izin verilen aralıkta
yapılır (ham EC yazımı yok). udev kuralları yalnızca `power`/`video` grubuna
yazma verir; geri kalan root + polkit ister.

## Lisans ve kaynaklar

GPL-3.0-or-later. Fikir ve donanım bilgisi için teşekkürler:
LenovoLegionToolkit (GPL-3.0) ve LenovoLegionLinux (GPL-2.0) projelerine.
