@echo off
title SHALU AI - Safe Voice
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py server.py
) else (
    python server.py
)
pause
