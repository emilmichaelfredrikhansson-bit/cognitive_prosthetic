@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" bob_local.py
) else if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" bob_local.py
) else (
  py -3 bob_local.py
)
if errorlevel 1 pause
