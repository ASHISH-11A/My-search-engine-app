# One-click launcher for My Search: local Meilisearch + SearXNG web metasearch.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Elevate {
  $id=[Security.Principal.WindowsIdentity]::GetCurrent(); $p=New-Object Security.Principal.WindowsPrincipal($id)
  if(-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs; exit
  }
}
Elevate
Write-Host "`n=== MY SEARCH - LOCAL INDEX + WEB SEARCH ===`n" -ForegroundColor Cyan

wsl --status *> $null
if($LASTEXITCODE -ne 0){
  Write-Host "WSL is not ready. Installing/enabling WSL..." -ForegroundColor Yellow
  wsl --install --no-distribution
  if($LASTEXITCODE -ne 0){Write-Host "WSL needs a Windows Update/restart. Run this launcher again after that." -ForegroundColor Red; pause; exit 1}
  Write-Host "If Windows asks for a restart, restart and run this launcher again." -ForegroundColor Yellow; pause; exit 0
}
wsl --update *> $null

$docker=Get-Command docker -ErrorAction SilentlyContinue
if(-not $docker){
  if(Get-Command winget -ErrorAction SilentlyContinue){
    Write-Host "Docker Desktop is missing. Installing it with winget..." -ForegroundColor Yellow
    winget install --id Docker.DockerDesktop --exact --accept-source-agreements --accept-package-agreements
  } else {Write-Host "Docker Desktop is missing and winget is unavailable." -ForegroundColor Red; Start-Process "https://docs.docker.com/desktop/setup/install/windows-install/"; pause; exit 1}
}
$dockerExe="$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
if(Test-Path $dockerExe){Start-Process $dockerExe}else{try{Start-Process "Docker Desktop"}catch{}}

Write-Host "Waiting for Docker Engine..." -ForegroundColor Yellow
$ready=$false
for($i=0;$i -lt 90;$i++){docker info *> $null;if($LASTEXITCODE -eq 0){$ready=$true;break};Start-Sleep 2}
if(-not $ready){Write-Host "Docker Engine did not become ready." -ForegroundColor Red;Write-Host "Open Docker Desktop, wait until it is Running, then launch this file again." -ForegroundColor Yellow;pause;exit 1}

$port=3000
while($port -le 3099){$inUse=Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue;if(-not $inUse){break};$port++}
if($port -gt 3099){Write-Host "No free port was found between 3000 and 3099." -ForegroundColor Red;pause;exit 1}
$env:WEB_PORT="$port"
Write-Host "Using free web port: $port" -ForegroundColor Green

Write-Host "Cleaning up previous search-engine containers..." -ForegroundColor Yellow
$oldNames=@("googlelike_meili","googlelike_api","googlelike_crawler","googlelike_web","searxng","searxng-core","searxng-valkey")
foreach($name in $oldNames){$exists=docker ps -a --filter "name=^/$name$" --format "{{.ID}}" 2>$null;if($exists){Write-Host "Removing old container: $name" -ForegroundColor DarkYellow;docker rm -f $name *> $null}}
docker compose down --remove-orphans *> $null

Write-Host "Building and starting local search + SearXNG..." -ForegroundColor Yellow
docker compose up --build -d
if($LASTEXITCODE -ne 0){
  Write-Host "`nFirst Docker Compose start failed. Cleaning up and retrying..." -ForegroundColor Yellow
  docker compose down --remove-orphans *> $null
  foreach($name in $oldNames){docker rm -f $name *> $null}
  Start-Sleep 2
  docker compose up --build -d
}
if($LASTEXITCODE -ne 0){Write-Host "`nDocker Compose failed after automatic cleanup/retry." -ForegroundColor Red;docker compose ps;docker compose logs --tail=120;pause;exit 1}

Write-Host "Waiting for the search page..." -ForegroundColor Yellow
$url="http://localhost:$port"
for($i=0;$i -lt 60;$i++){try{$r=Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2;if($r.StatusCode -eq 200){break}}catch{};Start-Sleep 2}
Write-Host "`n=== READY ===" -ForegroundColor Green
Write-Host "MY SEARCH: $url" -ForegroundColor Cyan
Write-Host "Searches your local Meilisearch index AND the web through SearXNG." -ForegroundColor Gray
Write-Host "SearXNG is the metasearch layer; it does not replace your own crawler/index." -ForegroundColor Gray
Start-Process $url
docker compose ps
Write-Host "`n"
pause
