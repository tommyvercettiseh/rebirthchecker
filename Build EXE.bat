@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs

where py >nul 2>nul
if errorlevel 1 (
  echo Python is niet gevonden.
  pause
  exit /b 1
)

if not exist .venv py -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >> logs\build.log 2>&1
pip install -r requirements.txt pyinstaller >> logs\build.log 2>&1
if errorlevel 1 goto :error

pyinstaller --noconfirm --clean --onefile --windowed --name "RebirthChecker" app.py >> logs\build.log 2>&1
if errorlevel 1 goto :error

echo.
echo Klaar: dist\RebirthChecker.exe
explorer dist
pause
exit /b 0

:error
echo Build mislukt. Bekijk logs\build.log.
pause
exit /b 1
