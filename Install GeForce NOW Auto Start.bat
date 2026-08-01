@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo Start eerst een keer Start Rebirth Checker.bat zodat Python wordt voorbereid.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir = Join-Path $env:USERPROFILE '.rebirthchecker';" ^
  "$p = Join-Path $dir 'config.json';" ^
  "New-Item -ItemType Directory -Force -Path $dir | Out-Null;" ^
  "$d = $null; if (Test-Path $p) { try { $d = Get-Content $p -Raw | ConvertFrom-Json } catch {} };" ^
  "if ($null -eq $d) { $d = New-Object PSObject };" ^
  "if ($d.PSObject.Properties.Name -contains 'launch_with_gfn') { $d.launch_with_gfn = $true } else { $d | Add-Member -NotePropertyName launch_with_gfn -NotePropertyValue $true };" ^
  "$d | ConvertTo-Json -Depth 8 | Set-Content $p -Encoding UTF8"

echo.
echo Laat GeForce NOW openstaan. Je kiest nu handmatig het juiste proces.
echo.
".venv\Scripts\python.exe" "process_selector.py"
if errorlevel 1 (
  echo Proces selecteren is mislukt.
  pause
  exit /b 1
)

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\RebirthChecker GeForceNOW Watcher.vbs"

> "%VBS%" echo Set shell = CreateObject("WScript.Shell")
>> "%VBS%" echo shell.Run Chr(34) ^& "%CD%\.venv\Scripts\pythonw.exe" ^& Chr(34) ^& " " ^& Chr(34) ^& "%CD%\watcher.py" ^& Chr(34), 0, False

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*rebirthchecker*watcher.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul

start "Rebirth Checker Watcher" ".venv\Scripts\pythonw.exe" "watcher.py"

echo.
echo GeForce NOW auto-start is geinstalleerd en direct ingeschakeld.
echo De geselecteerde procesnaam is opgeslagen.
echo De widget opent maximaal een keer per GeForce NOW-sessie.
echo Logbestand: %USERPROFILE%\.rebirthchecker\watcher.log
echo.
echo Sluit GeForce NOW volledig af en start het daarna opnieuw om te testen.
pause
