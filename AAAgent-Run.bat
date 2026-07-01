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
  echo [ERROR] Node.js was not found.
  echo Please install Node.js 18 or newer, then run this file again.
  echo.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found.
  echo Please reinstall Node.js with npm enabled.
  echo.
  pause
  exit /b 1
)

echo [1/3] Checking local runtime...
node --version
npm --version
echo.

echo [2/3] Checking project scripts...
node --check server.cjs
if errorlevel 1 (
  echo.
  echo [ERROR] server.cjs check failed.
  pause
  exit /b 1
)

node --check src\ui\app.js
if errorlevel 1 (
  echo.
  echo [ERROR] src\ui\app.js check failed.
  pause
  exit /b 1
)

echo.
echo [3/3] Starting AAAgent...
echo URL: http://localhost:5173
echo.
echo Keep this window open while using AAAgent.
echo Press Ctrl+C to stop the server.
echo.

start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://localhost:5173'"
npm run dev

echo.
echo AAAgent has stopped.
pause
