@echo off
setlocal
cd /d "%~dp0"
title AAAgent Local Runner

echo ========================================
echo  AAAgent Local Compile and Run
echo ========================================
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js was not found. Install Node.js 18 or newer.
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found. Reinstall Node.js with npm enabled.
  pause
  exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Install Python 3.11 or newer.
  pause
  exit /b 1
)

echo [1/3] Checking local runtime...
node --version
call npm --version
echo.
echo [2/3] Checking project files...
node --check server.cjs
if errorlevel 1 goto :check_failed
node --check src\ui\app.js
if errorlevel 1 goto :check_failed
python -m py_compile backend\database.py backend\prompts.py backend\professional.py backend\sse_server.py
if errorlevel 1 goto :check_failed

echo.
echo [3/3] Starting local services...
echo Starting managed local service...
netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul
if errorlevel 1 (
  echo Starting UI on port 5173...
  start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:5173'"
  call npm run dev
  goto :finished
) else (
  echo UI is already running on port 5173.
  start "" http://localhost:5173
)

:finished
echo.
echo AAAgent is ready at http://localhost:5173
echo Press any key to close this window. Services keep running in their own processes.
pause >nul
exit /b 0

:check_failed
echo.
echo [ERROR] A project syntax check failed. Read the message above.
pause
exit /b 1