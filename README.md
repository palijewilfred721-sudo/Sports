# Football Manager

Flask + SQLite app to manage teams, players, fixtures, results and the league table.
One codebase runs as a web app, a Windows `.exe` and an Android `.apk`.

## Run from source
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. The database `football.db` is created automatically.

## Where data is stored
- Source run: next to `app.py`
- Windows exe: `%APPDATA%\FootballManager\football.db`
- Android: the app's private storage

## Build on GitHub
Push to `main` (or run the workflow manually) to build both files; download them from the run's **Artifacts**.
To publish a release: `git tag v1.1.0 && git push origin v1.1.0`.

## Build the EXE locally
Run `build_exe.bat` -> `dist\FootballManager.exe`.

## Files
- `app.py` routes and database
- `desktop.py` Windows window launcher (pywebview)
- `main.py` + `buildozer.spec` Android launcher (Kivy WebView)
- `.github/workflows/build.yml` CI build
