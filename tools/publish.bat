@echo off
rem Export the addon's saved data to data.json and push it, so the site updates.
rem Run it after logging out of the game or a /reload. Add --watch to keep exporting
rem whenever the game saves (it then doesn't push; run this again without it to push).
setlocal
set WOW=C:\Program Files (x86)\World of Warcraft\_forever_
rem Find the saved data under whichever account folder the game uses on this PC.
set SAVED=
for /d %%A in ("%WOW%\WTF\Account\*") do if exist "%%A\SavedVariables\IssuesWithTissues.lua" set "SAVED=%%A\SavedVariables\IssuesWithTissues.lua"
if defined SAVED goto :found
echo Could not find IssuesWithTissues.lua in the game's WTF\Account folders. Log in with the addon once, then try again.
goto :eof
:found
cd /d "%~dp0.."
py -3 tools\export.py "%SAVED%" data.json %* || goto :eof
git add data.json
git diff --cached --quiet && (echo Nothing new to publish.& goto :eof)
git commit -m "Update guild data" && git push
