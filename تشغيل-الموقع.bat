@echo off
title QIMMA HUB - Local Server
cd /d "%USERPROFILE%\Documents\Qoder\2026-11-21\0727cc66"
if not exist "run.py" (
  echo Project folder was not found.
  echo Expected path: %CD%
  pause
  exit /b 1
)
python run.py
if errorlevel 1 (
  echo.
  echo The server could not start. Check the messages above.
  pause
)
