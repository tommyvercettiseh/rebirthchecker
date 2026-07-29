@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo Start eerst een keer Start Rebirth Checker.bat zodat Python wordt voorbereid.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = Join-Path $env:USERPROFILE '.rebirthchecker\config.json';" ^
  "$d = @{}; if (Test-Path $p) { try { $d = Get-Content $p -Raw | ConvertFrom-Json -AsHashtable } catch {} };" ^
  "$d['launch_with_gfn'] = $true;" ^
  "$d | ConvertTo-Json -Depth 8 | Set-Content $p -Encoding UTF8"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\RebirthChecker GeForceNOW Watcher.vbs"

> "%VBS%" echo Set shell = CreateObject("WScript.Shell")
>> "%VBS%" echo shell.Run Chr(34) ^& "%CD%\.venv\Scripts\pythonw.exe" ^& Chr(34) ^& " " ^& Chr(34) ^& "%CD%\watcher.py" ^& Chr(34), 0, False

taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq Rebirth Checker Watcher" >nul 2>nul
start "Rebirth Checker Watcher" ".venv\Scripts\pythonw.exe" "watcher.py"

echo.
echo GeForce NOW auto-start is geinstalleerd en direct ingeschakeld.
echo Logbestand: %USERPROFILE%\.rebirthchecker\watcher.log
echo Test nu door GeForce NOW te starten.
pause
