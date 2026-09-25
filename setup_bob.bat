@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :fail
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto :fail

if not exist ".env.local" (
  copy /Y ".env.local.example" ".env.local" >nul
  echo Created .env.local from the safe template.
)

echo.
echo Bob local setup is ready.
echo Next: run first_run_bob.bat once to sign in to ChatGPT.
exit /b 0

:fail
echo.
echo Bob setup failed. See the error above.
pause
exit /b 1
