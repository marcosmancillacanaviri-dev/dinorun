#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Compilacion del APK de Dino Runner (pygame-ce) con buildozer + python-for-android.
# Lo ejecuta el workflow .github/workflows/build-apk.yml en el runner de GitHub.
#
# Primer paso: reordena los archivos que se subieron dentro de carpetas "subir-N"
# (GitHub web no permite mover carpetas) para dejar el proyecto con la estructura
# que espera main.py:  main.py, buildozer.spec, img/, music/, p4a-recipes/.
# ---------------------------------------------------------------------------
set -euo pipefail

echo "==================== 1) REORGANIZAR ARCHIVOS SUBIDOS ===================="
# Cualquier carpeta "subir*" que se haya subido se vuelca en la raiz del proyecto.
for d in subir*/; do
  [ -d "$d" ] || continue
  echo "-> volcando $d en la raiz"
  cp -a "$d"/. .
done
rm -rf subir*/

# Frames que se hayan subido sueltos en la raiz -> a su carpeta.
mkdir -p img/jefes/dragon
for n in 21 22 23 24; do
  if [ -f "walk_$n.png" ] && [ ! -f "img/jefes/dragon/walk_$n.png" ]; then
    mv -f "walk_$n.png" "img/jefes/dragon/"
  fi
done

echo "--- contenido de la raiz ---"
ls -la
echo "--- conteo de archivos ---"
echo "img:         $(find img -type f 2>/dev/null | wc -l)"
echo "music:       $(find music -type f 2>/dev/null | wc -l)"
echo "p4a-recipes: $(find p4a-recipes -type f 2>/dev/null | wc -l)"
echo "dragon:      $(ls img/jefes/dragon 2>/dev/null | wc -l) frames"
echo "golem:       $(ls img/jefes/golem 2>/dev/null | wc -l) frames"

echo "--- comprobaciones criticas ---"
faltan=0
for k in main.py buildozer.spec img/icono.png img/presplash.png \
         img/jefes/dragon/walk_00.png img/jefes/dragon/walk_21.png \
         img/jefes/dragon/walk_24.png img/jefes/golem/idle_00.png \
         music/fondo.mp3 music/boss.mp3 p4a-recipes/pygame-ce/__init__.py; do
  if [ -e "$k" ]; then echo "OK    $k"; else echo "FALTA $k"; faltan=1; fi
done
if [ "$faltan" = "1" ]; then
  echo "ERROR: faltan archivos del juego; abortando."
  exit 1
fi

echo "==================== 2) DEPENDENCIAS DEL SISTEMA ===================="
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  git zip unzip wget autoconf automake libtool pkg-config \
  zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev libltdl-dev ccache

echo "==================== 3) BUILDozer + CYTHON ===================="
python -m pip install --upgrade "pip==24.0" "setuptools<70" wheel
python -m pip install "cython==0.29.36" "buildozer==1.6.0"
buildozer --version

echo "==================== 4) SDK DE ANDROID (cmdline-tools + licencias) ===================="
SDK="$HOME/.buildozer/android/platform/android-sdk"
mkdir -p "$SDK/cmdline-tools" "$SDK/tools/bin" "$SDK/licenses" "$HOME/.android"
touch "$HOME/.android/repositories.cfg"

if [ ! -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]; then
  wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O /tmp/cmdline-tools.zip
  rm -rf /tmp/clt && mkdir -p /tmp/clt
  unzip -q /tmp/cmdline-tools.zip -d /tmp/clt
  rm -rf "$SDK/cmdline-tools/latest" && mkdir -p "$SDK/cmdline-tools/latest"
  cp -r /tmp/clt/cmdline-tools/* "$SDK/cmdline-tools/latest/"
  chmod +x "$SDK"/cmdline-tools/latest/bin/* || true
fi

# buildozer busca el sdkmanager en <sdk>/tools/bin/
ln -sf "$SDK/cmdline-tools/latest/bin/sdkmanager" "$SDK/tools/bin/sdkmanager"

# licencias pre-aceptadas (por si sdkmanager --licenses falla)
printf '8933bad161af4178b1185d1a37fbf41ea5269c55\nd56f5187479451eabf01fb78af6dfcb131a6481e\n24333f8a63b6825ea9c5514f83c2829b004d1fee\n' > "$SDK/licenses/android-sdk-license"
printf '84831b9409646a918e30573bab4c9c91346d8abd\n' > "$SDK/licenses/android-sdk-preview-license"
printf '601085b94cd77f0b54ff86406957099ebe79c4d6\n' > "$SDK/licenses/android-googletv-license"
printf '33b6a2b64607f11b759f320ef9dff4ae5c47d97a\n' > "$SDK/licenses/google-gdk-license"
printf 'd56f5187479451eabf01fb78af6dfcb131a6481e\n24333f8a63b6825ea9c5514f83c2829b004d1fee\n' > "$SDK/licenses/android-sdk-arm-dbt-license"
yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK" --licenses > /dev/null 2>&1 || true

echo "==================== 5) PYTHON-FOR-ANDROID ===================="
P4A="$HOME/.buildozer/android/platform/python-for-android"
mkdir -p "$HOME/.buildozer/android/platform"
if [ ! -d "$P4A/.git" ]; then
  git clone -b master --single-branch https://github.com/kivy/python-for-android.git "$P4A"
fi
# pip>=25 rompe la instalacion de dependencias de build de p4a
sed -i "s/pip install -U pip/pip install pip==24.0/" "$P4A/pythonforandroid/build.py" || true
grep -n "pip install pip==24.0" "$P4A/pythonforandroid/build.py" || true

echo "==================== 6) COMPILAR APK ===================="
export ANDROIDSDK="$SDK"
export ANDROIDNDK="$HOME/.buildozer/android/platform/android-ndk-r28c"
export ANDROIDAPI=34
export ANDROIDMINAPI=24
buildozer -v android debug 2>&1 | tee buildozer-build.log

echo "==================== FIN ===================="
ls -la bin/ || true
