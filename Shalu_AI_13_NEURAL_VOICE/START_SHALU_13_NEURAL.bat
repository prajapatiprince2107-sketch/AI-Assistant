@echo off
setlocal
title SHALU AI 13.0 - Neural Voice
cd /d "%~dp0"

python -c "import piper" >nul 2>&1
if errorlevel 1 (
  echo Piper is not installed yet.
  echo Run SETUP_SHALU_13_NEURAL.bat first.
  pause
  exit /b 1
)

start "" http://127.0.0.1:8765
python server.py
pause
