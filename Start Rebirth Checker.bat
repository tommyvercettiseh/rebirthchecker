@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist logs mkdir logs

set "PYTHON_CMD="
where py >nul 2>nul && set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
  where python >nul 2>nul && set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo Python is niet gevonden of staat niet in PATH.
  echo Open Python en kies bij Modify ook "Add Python to environment variables".
  echo.
  echo Controleer daarna met: python --version
  pause
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Virtuele omgeving wordt aangemaakt...
  %PYTHON_CMD% -m venv .venv >> logs\launcher.log 2>&1
  if errorlevel 1 goto :error
)

.venv\Scripts\python.exe -m pip install --upgrade pip >> logs\launcher.log 2>&1
.venv\Scripts\python.exe -m pip install -r requirements.txt >> logs\launcher.log 2>&1
if errorlevel 1 goto :error

start "Rebirth Checker" .venv\Scripts\pythonw.exe app_v023.py
exit /b 0

:error
echo Starten is mislukt. Open logs\launcher.log voor details.
pause
exit /b 1
