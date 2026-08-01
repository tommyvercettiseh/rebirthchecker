@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Start eerst een keer Start Rebirth Checker.bat zodat Python wordt voorbereid.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" "process_selector.py"
if errorlevel 1 (
  echo Proces selecteren is mislukt.
  pause
  exit /b 1
)

echo.
echo Proces opgeslagen. De watcher wordt nu opnieuw gestart.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*rebirthchecker*watcher.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul
start "Rebirth Checker Watcher" ".venv\Scripts\pythonw.exe" "watcher.py"

echo Klaar. Sluit GeForce NOW volledig af en start het daarna opnieuw.
pause
