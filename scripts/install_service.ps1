<#
.SYNOPSIS
    install_service.ps1 — Windows Background Service Registration Script (ENH-019)
.DESCRIPTION
    Registers PROJECT ANCHOR backend (FastAPI uvicorn) and frontend (Next.js)
    as autonomous background services for air-gapped sovereign Naval C4ISR workstations.
#>

param (
    [string]$Action = "install",
    [string]$ServiceName = "ProjectAnchorBackend",
    [string]$ServiceDisplayName = "PROJECT ANCHOR AI Intelligence Service",
    [int]$Port = 8000
)

$BuildDir = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $BuildDir ".venv\Scripts\python.exe"
$UvicornExe = Join-Path $BuildDir ".venv\Scripts\uvicorn.exe"
$LogsDir = Join-Path $BuildDir "data\logs"

if (!(Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

$LogFile = Join-Path $LogsDir "service_backend.log"

Write-Host "=================================================================="
Write-Host "PROJECT ANCHOR — WINDOWS SERVICE REGISTRATION (ENH-019)"
Write-Host "=================================================================="
Write-Host "Action:      $Action"
Write-Host "Service:     $ServiceName"
Write-Host "Directory:   $BuildDir"
Write-Host "Python Exec: $VenvPython"
Write-Host "Log Output:  $LogFile"
Write-Host "=================================================================="

if ($Action -eq "install") {
    # Check if service already exists
    $existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "[INFO] Service '$ServiceName' already exists. Stopping and removing..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        sc.exe delete $ServiceName | Out-Null
        Start-Sleep -Seconds 2
    }

    # Register startup command
    $binPath = "$UvicornExe anchor.main:app --host 0.0.0.0 --port $Port --workers 1"
    
    Write-Host "[INSTALL] Creating Windows Service via sc.exe..."
    $createResult = sc.exe create $ServiceName binPath= $binPath start= auto DisplayName= $ServiceDisplayName
    Write-Host $createResult

    # Set failure recovery actions (restart on crash)
    sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null
    
    Write-Host "[SUCCESS] Service '$ServiceName' registered with Automatic startup." -ForegroundColor Green
    Write-Host "[INFO] To start service now, run: Start-Service -Name $ServiceName"

} elseif ($Action -eq "uninstall") {
    Write-Host "[UNINSTALL] Stopping service '$ServiceName'..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $ServiceName
    Write-Host "[SUCCESS] Service '$ServiceName' deleted." -ForegroundColor Green

} elseif ($Action -eq "start") {
    Write-Host "[START] Starting service '$ServiceName'..."
    Start-Service -Name $ServiceName
    Write-Host "[SUCCESS] Service '$ServiceName' is running." -ForegroundColor Green

} elseif ($Action -eq "status") {
    Get-Service -Name $ServiceName -ErrorAction SilentlyContinue | Format-List
}
