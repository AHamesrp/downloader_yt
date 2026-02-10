@echo off
REM Inicia backend (Flask) e frontend (servidor estático) com um duplo clique

REM Caminho base = pasta onde este .bat está
set "BASE_DIR=%~dp0"

REM Inicia o backend Flask
start "YT Downloader - Backend" cmd /k "cd /d \"%BASE_DIR%donwloader\" && python server.py"

REM Inicia um servidor HTTP simples para o front
REM Acesse depois em: http://localhost:5500
start "YT Downloader - Front" cmd /k "cd /d \"%BASE_DIR%front\" && python -m http.server 5500"

REM Abre o navegador apontando para o front
start "" "http://localhost:5500"

