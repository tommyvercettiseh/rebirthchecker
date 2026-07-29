@echo off
setlocal EnableExtensions
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RebirthChecker GeForceNOW Watcher.vbs"

if exist "%VBS%" del /q "%VBS%"
taskkill /f /im pythonw.exe /fi "WINDOWTITLE eq Rebirth Checker Watcher" >nul 2>nul

echo.
echo GeForce NOW auto-start is verwijderd.
pause
