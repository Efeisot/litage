# Litage — `BETA`

A Lenovo Vantage / Legion Zone alternative for Linux. Distro- and init-agnostic.

> **Beta.** UI and commands may change; some toggles may not work on your hardware.
> Writes only touch kernel-exposed sysfs nodes (no raw EC access). Before testing,
> run `litage doctor`. Please attach `litage status --json` to bug reports.

Inspired by [LenovoLegionToolkit](https://github.com/BartoszCichecki/LenovoLegionToolkit)
(Windows) and [LenovoLegionLinux](https://github.com/johnfanv2/LenovoLegionLinux)
(Linux), rewritten from scratch to run on **any Lenovo laptop, any distro, any init**
— no kernel module required.

**Tested hardware:** only one laptop so far — the author's
Lenovo Yoga 7 2-in-1 14AKP10 (83JR, AMD Ryzen AI 7 350, iGPU-only) running
Artix Linux (OpenRC) + Cinnamon (X11). Legion/ThinkPad/NVIDIA paths exist in code
but are **unverified on real hardware** — reports welcome.

## Features

Unsupported hardware is shown locked (not hidden); Legion/NVIDIA pages unlock
automatically where present.

- Power profiles, CPU governor/EPP/boost, live sensor graphs
- IdeaPad controls: battery conservation, fan mode, Fn-Lock, camera, USB charging,
  keyboard backlight (0–2) + **auto brightness** (ambient-light sensor, via daemon)
- Battery stats + health, display brightness, Wi-Fi/Bluetooth, mic/speaker
- Legion (module present): power limits, fan-curve readout, LLL-compatible presets
- TLP integration (the single optional dependency), ThinkPad basics
- Automation daemon (`litaged`) with AC/battery presets
- GTK4/LibAdwaita GUI: static icon sidebar, batch **Save** (one password for all
  changes), right-click menus, 4 themes (pure-black `#000` / dark / gray / white),
  system tray with live status, close-to-tray or quit setting

## Install

```bash
git clone <repo> && cd Litage
sudo ./install.sh              # deps + udev + polkit + init + menu + icons
sudo ./install.sh --autostart  # + start on login
```

Needs: `python3, python-gobject, gtk4, libadwaita` (+ optional `tlp`;
tray needs `libayatana-appindicator`, password dialogs need a polkit agent).
A reboot is recommended afterwards (udev + agent session).
Check with `litage doctor` (aim: passwordless writes on all nodes).

Portable build: `./packaging/build-appimage.sh` → `Litage-x86_64.AppImage`.

## Usage

```bash
litage status                 # everything; --json for scripts
litage list                   # writable features on THIS machine
sudo litage set fn_lock on
litage apply platform_profile=balanced fn_lock=on   # batched, one password
litage monitor -n 5
litage doctor                 # installation diagnostics
litage-gui                    # [--minimized] [--page battery]
sudo litaged --once           # apply daemon preset once (test)
```

Config: `/etc/litage/litaged.conf`, presets in `/etc/litage/profiles/*.yaml`,
GUI prefs in `~/.config/litage/`. Daemon supports systemd, OpenRC, runit,
dinit, s6 and sysvinit (auto-detected).

## Troubleshooting

- Start with `litage doctor`.
- If writes fail: re-run `sudo ./install.sh`, then reboot. On rolling distros,
  finish partial upgrades first (`sudo pacman -Syu`).
- CPU fight with TLP: leave `governor`/`epp` empty in presets to let TLP manage them.

## Layout

```
litage/            # cli, gui, daemon, tray, capabilities, privileged,
                   # themes, prefs, autostart, utils + backends/
daemon/            # litaged.conf, profiles, 6 init units
packaging/         # install.sh, build-appimage.sh, PKGBUILD, policy,
                   # udev rules, .desktop files, icons
tests/             # hardware-free + live read-only tests
```

## License

GPL-3.0-or-later. Thanks to the LenovoLegionToolkit and LenovoLegionLinux
projects for ideas and hardware knowledge.
