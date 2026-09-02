# ==============================================================================
# PROJECT ANCHOR - Concurrent Application Launcher (start.ps1)
# Launches FastAPI Backend + Next.js C4ISR Tactical Console Concurrently
# ==============================================================================

[CmdletBinding()]
param (
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [switch]$Dev = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $ProjectRoot ".venv"
$ConsoleDir = Join-Path $ProjectRoot "console"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [ANCHOR] Launching Sovereign Defence Regulatory Command System  " -ForegroundColor Cyan
Write-Host " Backend: http://127.0.0.1:$BackendPort | Frontend: http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# Verify Python executable
if (-not (Test-Path $VenvPython)) {
    Write-Error "[FAIL] Virtual environment python executable not found at $VenvPython. Run .\scripts\setup.ps1 first."
}

# Launch FastAPI Backend in a separate process window
Write-Host "[1/3] Starting FastAPI Backend on port $BackendPort..." -ForegroundColor Yellow
$BackendCmd = "cd '$ProjectRoot'; & '$VenvPython' -m uvicorn anchor.main:app --host 127.0.0.1 --port $BackendPort --workers 1"
$BackendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd -PassThru

# Wait for Backend to become healthy
Write-Host "[2/3] Awaiting Backend /health liveness probe..." -ForegroundColor Yellow
$HealthUrl = "http://127.0.0.1:$BackendPort/health"
$MaxAttempts = 30
$Attempt = 0
$BackendReady = $false

while ($Attempt -lt $MaxAttempts) {
    Start-Sleep -Milliseconds 500
    try {
        $Response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($Response.status -eq "ok") {
            $BackendReady = $true
            break
        }
    } catch {
        # Retry until available
    }
    $Attempt++
}

if ($BackendReady) {
    Write-Host "  -> Backend Online & Responding (PID: $($BackendProcess.Id))." -ForegroundColor Green
} else {
    Write-Host "  -> [NOTICE] Backend probe timed out, proceeding with frontend launch..." -ForegroundColor Yellow
}

# Launch Next.js Tactical Console
Write-Host "[3/3] Starting Next.js Tactical Console on port $FrontendPort..." -ForegroundColor Yellow
Push-Location $ConsoleDir
try {
    $PnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($Dev) {
        Write-Host "  -> Starting development server..." -ForegroundColor Cyan
        if ($PnpmCmd) {
            & pnpm dev --port $FrontendPort
        } else {
            & npx pnpm dev --port $FrontendPort
        }
    } else {
        if (-not (Test-Path ".next")) {
            Write-Host "  -> No production build detected. Building Next.js console..." -ForegroundColor Yellow
            if ($PnpmCmd) {
                & pnpm build
            } else {
                & npx pnpm build
            }
        }
        Write-Host "  -> Starting production server..." -ForegroundColor Cyan
        if ($PnpmCmd) {
            & pnpm start --port $FrontendPort
        } else {
            & npx pnpm start --port $FrontendPort
        }
    }
} finally {
    Pop-Location
}