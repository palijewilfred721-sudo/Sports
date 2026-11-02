@echo off
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --onefile --windowed --name FootballManager ^
  --add-data "templates;templates" --add-data "static;static" desktop.py
echo.
echo Done: dist\FootballManager.exe
pause
