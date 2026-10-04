@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js is required. Run BUILD_WINDOWS_APP.bat first. & pause & exit /b 1)
if not exist node_modules call npm install
call npm start
