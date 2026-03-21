@echo off
REM Site no navegador: um único servidor Flask (API + página em /)

set "BASE_DIR=%~dp0"

start "AuroraYt - Site" cmd /k "cd /d \"%BASE_DIR%\" && python downloader\server.py"

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000/"

