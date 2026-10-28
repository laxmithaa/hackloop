@echo off
title Healthcare Bill Navigator - Local Server
echo ============================================================
echo   Starting Healthcare Bill Navigator...
echo   Local Address: http://localhost:3000/
echo ============================================================
echo Opening website in your default browser...
timeout /t 2 /nobreak >nul
start http://localhost:3000/
echo.
echo Server is running. Press Ctrl+C in this window to stop.
echo.
cd /d "%~dp0"
npm start
pause
