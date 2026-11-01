[app]
title = Football Manager
package.name = footballmanager
package.domain = org.football
source.dir = .
source.include_exts = py,html,css,js,png,jpg,xml
source.exclude_dirs = .github,.git,bin,build,dist,venv,.venv,__pycache__,.buildozer
source.exclude_patterns = football.db,secret.key,desktop.py,build_exe.bat
version = 1.1.0
requirements = python3,kivy==2.3.0,flask,werkzeug,jinja2,markupsafe,itsdangerous,click,blinker,sqlite3,pyjnius,android
orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.ndk = 25b
android.ndk_api = 24
android.extra_manifest_application_arguments = ./extras/application_args.xml
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1

# Pin python-for-android to a release that matches Kivy 2.3.0 (master now builds Python 3.14, which breaks Kivy)
