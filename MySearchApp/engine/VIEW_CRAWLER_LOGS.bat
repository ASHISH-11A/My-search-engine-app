@echo off
cd /d "%~dp0"
docker compose logs -f crawler
pause
