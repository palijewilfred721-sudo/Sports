@echo off
REM Local Windows build. Run from the project folder.
py -3.11 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --onefile --windowed --name FootballManager ^
  --add-data "templates;templates" --add-data "static;static" desktop.py
echo.
echo Done: dist\FootballManager.exe
pause
