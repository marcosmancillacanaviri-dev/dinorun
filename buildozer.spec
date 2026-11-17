[app]

title = Dino Runner 2.0
package.name = dinorunner20
package.domain = com.dinorunner.ultimate

source.dir = .
# Todo lo que necesita el juego: codigo, sprites, fuentes de jefes y musica.
source.include_exts = py,png,jpg,jpeg,jfif,json,txt,mp3,ogg,wav,ttf
# Artefactos de desarrollo que NO deben acabar dentro del APK.
source.exclude_dirs = __pycache__, bin, .buildozer, .git, .github, .vscode, .idea
source.exclude_patterns = _preview_*.png, _test_*.png, main_pygame_backup.py, crash.log, progreso_dino.json, top_scores.txt, upload_dino.ps1, *.pyc, *.pyo

version = 2.0
android.numeric_version = 20

# ---------------------------------------------------------------------------
#  python-for-android  (pygame-ce via recipe local en p4a-recipes/)
# ---------------------------------------------------------------------------
requirements = python3,pygame-ce
p4a.bootstrap = sdl2
p4a.branch = master
p4a.local_recipes = ./p4a-recipes

# ---------------------------------------------------------------------------
#  Android
# ---------------------------------------------------------------------------
orientation = landscape
fullscreen = 1

android.api = 34
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = False
android.presplash_color = #0b1030

# El juego es 100% offline: no pide ningun permiso.
android.permissions =

icon.filename = %(source.dir)s/img/icono.png
presplash.filename = %(source.dir)s/img/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
