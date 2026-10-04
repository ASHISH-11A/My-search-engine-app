@echo off
cd /d "%~dp0engine"
docker compose down --remove-orphans
pause
