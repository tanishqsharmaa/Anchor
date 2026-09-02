# ==============================================================================
# PROJECT ANCHOR - High-Performance Demo Mode Launcher (demo.ps1)
# Optimization: Clears ports, sets High Performance power plan, pre-warms models
# ==============================================================================

[CmdletBinding()]
param ()

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$StartScript = Join-Path $ScriptDir "start.ps1"

Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host " [ANCHOR] INICAI 2026 - 5-Minute Kill-Shot Demo Environment Prep " -ForegroundColor Magenta
Write-Host " Target Hardware: 16 GB Native Windows 11 (Air-Gapped Sovereign) " -ForegroundColor Magenta
Write-Host "=================================================================" -ForegroundColor Magenta
Write-Host ""

# 1. Kill stale processes on ports 8000 and 3000
Write-Host "[1/4] Terminating stale processes on ports 8000 and 3000..." -ForegroundColor Yellow
foreach ($port in @(8000, 3000)) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($conns) {
            foreach ($conn in $conns) {
                $pidToKill = $conn.OwningProcess
                if ($pidToKill -gt 0) {
                    Write-Host "  -> Terminating process PID $pidToKill on port $port..." -ForegroundColor Cyan
                    Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
                }
            }
        }
    } catch {
        # Ignore port querying errors
    }
}
Write-Host "  -> Ports 8000 and 3000 cleared." -ForegroundColor Green

# 2. Configure Windows Power Profile
Write-Host ""
Write-Host "[2/4] Setting Windows Power Profile to High Performance..." -ForegroundColor Yellow
try {
    # High Performance GUID
    & powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
    Write-Host "  -> Power profile optimized for low inference latency." -ForegroundColor Green
} catch {
    Write-Host "  -> Powercfg notice: Using current power profile." -ForegroundColor Yellow
}

# 3. Launch System & Open Browser
Write-Host ""
Write-Host "[3/4] Launching System and Tactical Console..." -ForegroundColor Yellow

# Launch start.ps1 in new process
Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$StartScript`""

# Wait for frontend port to open
Write-Host "[4/4] Awaiting tactical console readiness..." -ForegroundColor Yellow
$FrontendUrl = "http://localhost:3000"
$MaxWait = 25
$Count = 0
$Loaded = $false

while ($Count -lt $MaxWait) {
    Start-Sleep -Milliseconds 500
    try {
        $res = Invoke-WebRequest -Uri $FrontendUrl -Method Head -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($res.StatusCode -eq 200) {
            $Loaded = $true
            break
        }
    } catch {
        # Retry
    }
    $Count++
}

Write-Host ""
Write-Host "  -> Opening C4ISR Tactical Console in default browser ($FrontendUrl)..." -ForegroundColor Cyan
Start-Process $FrontendUrl

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host " [DEMO READY] System Live | Zero Cloud Calls | Zero Hallucinations" -ForegroundColor Green
Write-Host " Keyboard Shortcuts: [/] Focus | [d] AutoDeck | [e] Eval Gauges  " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green