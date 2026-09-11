@echo off
title SHALU AI 12.5 - Emotional Conversation
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py server.py) else (python server.py)
pause
