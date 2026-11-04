#!/bin/bash
# Build do Winh Ditado para Linux: binário PyInstaller + AppImage.
#
# Uso:  ./build-linux.sh
#
# Testado em Ubuntu 24.04. O AppImage gerado roda em distros com glibc >= 2.39;
# para alcançar distros mais antigas, gere em uma máquina com glibc mais velha
# (Ubuntu 22.04) — o processo é o mesmo.
set -euo pipefail

cd "$(dirname "$0")"
PY=${PYTHON:-python3}

# 1. dependências de sistema (precisa de sudo)
if command -v apt-get >/dev/null && [ "$(id -u)" = "0" -o -n "${SUDO_OK:-}" ]; then
  apt-get update -qq
  apt-get install -y --no-install-recommends \
    python3-venv python3-tk libportaudio2 libx11-6 libxext6 libxrender1 \
    libtk8.6 libtcl8.6 wget file
fi

# 2. ambiente de build isolado
rm -rf .venv-build
$PY -m venv .venv-build
. .venv-build/bin/activate
pip install --quiet --upgrade pip
pip install --quiet faster-whisper sounddevice numpy pyinstaller python-xlib

# 3. binário (onedir: abre rápido dentro do AppImage)
WINH_ONEFILE=0 pyinstaller --noconfirm --clean winh.spec

# 4. AppDir
rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/256x256/apps
cp -r dist/WinhDitado/. AppDir/usr/bin/
cp packaging/winh-ditado.desktop AppDir/
cp packaging/winh-ditado.desktop AppDir/usr/share/applications/
cp packaging/winh-ditado.png AppDir/winh-ditado.png
cp packaging/winh-ditado.png AppDir/usr/share/icons/hicolor/256x256/apps/
cp packaging/AppRun AppDir/AppRun
chmod +x AppDir/AppRun

# libs do sistema que o PyInstaller pode não copiar
for lib in libportaudio.so.2 libtk8.6.so libtcl8.6.so; do
  path=$(ldconfig -p | awk -v l="$lib" '$1 == l {print $NF; exit}')
  [ -n "$path" ] && cp -L "$path" AppDir/usr/bin/ || true
done

# 5. AppImage
if [ ! -x appimagetool ]; then
  wget -q https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool
  chmod +x appimagetool
fi
ARCH=x86_64 ./appimagetool --appimage-extract-and-run AppDir "WinhDitado-x86_64.AppImage"

echo "OK: $(pwd)/WinhDitado-x86_64.AppImage"
