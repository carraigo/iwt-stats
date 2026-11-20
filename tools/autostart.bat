@echo off
rem Publish the guild page automatically: starts a hidden watcher now and at every Windows
rem login. Whenever the game saves (logout or /reload) it exports data.json and pushes it.
rem   tools\autostart.bat          turn it on
rem   tools\autostart.bat off      turn it off
rem The watcher writes what it does to tools\watch.log.
setlocal
set SAVED=C:\Program Files (x86)\World of Warcraft\_forever_\WTF\Account\CRAIGRM\SavedVariables\IssuesWithTissues.lua
set REPO=%~dp0..
for %%I in ("%REPO%") do set REPO=%%~fI
set VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\iwt-stats-watcher.vbs

rem Stop a watcher that is already running (it is the only pyw running export.py --watch).
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'pythonw%%' or Name like 'pyw%%'\" | Where-Object { $_.CommandLine -like '*export.py*--watch*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

if /i "%~1"=="off" (
  del "%VBS%" >nul 2>&1
  echo Automatic publishing is off.
  goto :eof
)

> "%VBS%" echo CreateObject("WScript.Shell").Run "cmd /c cd /d ""%REPO%"" && pyw -3 -u tools\export.py ""%SAVED%"" data.json --watch --push >> tools\watch.log 2>&1", 0, False
wscript "%VBS%"
echo Automatic publishing is on. It starts with Windows; see tools\watch.log for what it did.
