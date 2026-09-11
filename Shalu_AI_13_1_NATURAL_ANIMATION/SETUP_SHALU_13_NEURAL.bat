@echo off
setlocal
title SHALU AI 13.0 - Neural Voice Setup
cd /d "%~dp0"

echo.
echo ==========================================================
echo   SHALU AI 13.0 - LOCAL NEURAL VOICE SETUP
echo ==========================================================
echo.
echo This will install Piper TTS and download one local voice.
echo Internet is required only during this first setup.
echo.

python --version
if errorlevel 1 (
  echo.
  echo Python was not found on PATH.
  echo Install Python 3.10-3.13 and run this file again.
  pause
  exit /b 1
)

echo.
echo [1/3] Installing Piper TTS...
python -m pip install --upgrade pip
python -m pip install piper-tts
if errorlevel 1 (
  echo.
  echo Piper installation failed.
  pause
  exit /b 1
)

echo.
echo [2/3] Downloading en_US-amy-medium neural voice...
python -m piper.download_voices en_US-amy-medium
if errorlevel 1 (
  echo.
  echo Voice download failed.
  pause
  exit /b 1
)

echo.
echo [3/3] Starting Shalu...
start "" http://127.0.0.1:8765
python server.py
pause
