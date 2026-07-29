@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo Start eerst een keer Start Rebirth Checker.bat zodat Python wordt voorbereid.
  pause
  exit /b 1
)

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\RebirthChecker GeForceNOW Watcher.vbs"

> "%VBS%" echo Set shell = CreateObject("WScript.Shell")
>> "%VBS%" echo shell.Run Chr(34) ^& "%CD%\.venv\Scripts\pythonw.exe" ^& Chr(34) ^& " " ^& Chr(34) ^& "%CD%\watcher.py" ^& Chr(34), 0, False

start "Rebirth Checker Watcher" ".venv\Scripts\pythonw.exe" "watcher.py"

echo.
echo GeForce NOW auto-start is geinstalleerd.
echo De watcher start voortaan automatisch met Windows.
echo Je kunt dit verwijderen met Uninstall GeForce NOW Auto Start.bat.
pause
