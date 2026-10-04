@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo       MY SEARCH - WINDOWS APP BUILDER
echo ================================================
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed. Installing Node.js LTS with winget...
  where winget >nul 2>nul
  if errorlevel 1 (
    echo winget is unavailable. Please install Node.js LTS manually.
    start https://nodejs.org/en/download
    pause
    exit /b 1
  )
  winget install OpenJS.NodeJS.LTS --exact --accept-source-agreements --accept-package-agreements
  if errorlevel 1 goto :fail
)
call npm install
if errorlevel 1 goto :fail
call npm run dist
if errorlevel 1 goto :fail
echo.
echo BUILD COMPLETE.
echo Check the dist folder for the Windows installer and portable EXE.
explorer "%~dp0dist"
pause
exit /b 0
:fail
echo.
echo Build failed. See the messages above.
pause
exit /b 1
