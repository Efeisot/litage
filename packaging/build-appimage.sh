#!/bin/sh
# Litage AppImage builder — son iş: taşınabilir tek dosya + menü entegrasyonu.
#
# Strateji: Python+GTK AppImage'leri sistem GTK'sını kullanır (bundle'lamak
# ~500MB olur). Bu AppImage uygulamayı + wrapper'ları paketler, çalışma
# anında sistem python3 + GTK4/LibAdwaita + TLP'yi kullanır. Bağımlılık
# yoksa AppRun anlaşılır hata verir.
#
# Çıktı: Litage-x86_64.AppImage (+ .desktop + .png önizleme)
# Gereken: curl, python3; appimagetool otomatik indirilir.
set -eu
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$HERE/Litage-x86_64.AppImage}"
APPDIR="$(mktemp -d /tmp/Litage.AppDir.XXXXXX)"
ARCH="$(uname -m)"
APPIMAGETOOL="${APPIMAGETOOL:-$HERE/packaging/appimagetool-$ARCH.AppImage}"

cleanup() { rm -rf "$APPDIR"; }
trap cleanup EXIT

echo "== AppDir: $APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib/litage" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/scalable/apps" "$APPDIR/etc/litage/profiles"

cp -r "$HERE/litage" "$APPDIR/usr/lib/litage/"
cp "$HERE/daemon/litaged.conf" "$APPDIR/etc/litage/" 2>/dev/null || cp "$HERE/daemon/litaged.conf" "$APPDIR/etc/litage/litaged.conf"
cp "$HERE"/daemon/profiles/*.yaml "$APPDIR/etc/litage/profiles/"
cp "$HERE/packaging/dev.litage.app.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/dev.litage.app.svg"
cp "$HERE/packaging/dev.litage.app.svg" "$APPDIR/dev.litage.app.svg"
cp "$HERE/packaging/dev.litage.app.desktop" "$APPDIR/usr/share/applications/"
cp "$HERE/packaging/dev.litage.app.desktop" "$APPDIR/dev.litage.app.desktop"

# AppRun: sistem python3'ü bul, yoksa hata ver
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
SELF="$(readlink -f "$0")"
HERE="$(dirname "$SELF")"
export LITAGE_LIB="$HERE/usr/lib/litage"
export PYTHONPATH="$LITAGE_LIB:${PYTHONPATH:-}"
export LITAGE_PROFILES="$HERE/etc/litage/profiles"
if ! command -v python3 >/dev/null; then
  echo "Litage AppImage: python3 bulunamadı" >&2
  exit 1
fi
if ! python3 -c "import gi" 2>/dev/null; then
  echo "Litage AppImage: python3-gobject eksik (kur: pacman -S python-gobject gtk4 libadwaita)" >&2
  exit 1
fi
MODE="$(basename "$ARGV0" 2>/dev/null || echo gui)"
case "$1" in
  cli|status|list|get|set|monitor|doctor) exec env PYTHONPATH="$LITAGE_LIB" python3 -m litage.cli "$@" ;;
  daemon|litaged) shift; exec env PYTHONPATH="$LITAGE_LIB" python3 -m litage.daemon "$@" ;;
  *) exec env PYTHONPATH="$LITAGE_LIB" python3 -m litage.gui "$@" ;;
esac
EOF
chmod +x "$APPDIR/AppRun"
ln -sf usr/bin "$APPDIR/bin" 2>/dev/null || true

# CLI/daemon shims (AppImage içinde de çalışsın)
for t in litage litage-gui litaged; do
  case "$t" in
    litage) mod=cli;; litage-gui) mod=gui;; litaged) mod=daemon;;
  esac
  printf '#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec env PYTHONPATH="$(dirname "$HERE")/lib/litage" python3 -m litage.%s "$@"\n' "$mod" > "$APPDIR/usr/bin/$t"
  chmod +x "$APPDIR/usr/bin/$t"
done

if [ ! -x "$APPIMAGETOOL" ]; then
  echo "== appimagetool indiriliyor..."
  URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
  curl -L -o "$APPIMAGETOOL" "$URL"
  chmod +x "$APPIMAGETOOL"
fi

echo "== AppImage derleniyor: $OUT"
ARCH="$ARCH" "$APPIMAGETOOL" "$APPDIR" "$OUT"
chmod +x "$OUT"
echo "OK: $OUT"
ls -lh "$OUT"
echo "Kurulum: ./Litage-x86_64.AppImage  (menü için ./install.sh --appimage-menü)"
