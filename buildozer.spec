[app]
title = Football Manager
package.name = footballmanager
package.domain = org.football
source.dir = .
source.include_exts = py,html,css,js,png,jpg,ico,svg
source.include_patterns = templates/*,static/*
source.exclude_dirs = .github,.buildozer,bin,build,dist,__pycache__
source.exclude_patterns = football.db,desktop.py
version = 1.0.0
requirements = python3,sqlite3,flask,werkzeug,jinja2,markupsafe,itsdangerous,click,blinker
orientation = portrait
fullscreen = 0

# Run Flask inside a WebView
p4a.bootstrap = webview
p4a.port = 5000

android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
