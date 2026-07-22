@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs

where py >nul 2>nul
if errorlevel 1 (
  echo Python is niet gevonden. Installeer Python 3.11 of nieuwer vanaf python.org.
  pause
  exit /b 1
)

if not exist .venv (
  echo Virtuele omgeving wordt aangemaakt...
  py -m venv .venv >> logs\launcher.log 2>&1
  if errorlevel 1 goto :error
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >> logs\launcher.log 2>&1
pip install -r requirements.txt >> logs\launcher.log 2>&1
if errorlevel 1 goto :error

start "Rebirth Checker" pythonw app.py
exit /b 0

:error
echo Starten is mislukt. Open logs\launcher.log voor details.
pause
exit /b 1
