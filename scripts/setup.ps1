# ==============================================================================
# PROJECT ANCHOR - One-Command Automated Setup Script (setup.ps1)
# Sovereign, Air-Gapped Regulatory AI for the Indian Navy (INICAI 2026)
# ==============================================================================

[CmdletBinding()]
param (
    [switch]$SkipBuild = $false,
    [switch]$SkipDeps = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $ProjectRoot ".venv"
$ConsoleDir = Join-Path $ProjectRoot "console"
$ReqFile = Join-Path $ProjectRoot "requirements.txt"
$ModelsDir = Join-Path $ProjectRoot "models"
$DataDir = Join-Path $ProjectRoot "data"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " [ANCHOR] Initializing Sovereign Regulatory Intelligence System " -ForegroundColor Cyan
Write-Host " Platform: Windows 11 Native | Platform Target: Intel Core Ultra" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Environment & Prerequisites Verification
# ------------------------------------------------------------------------------
Write-Host "[1/6] Verifying System Prerequisites..." -ForegroundColor Yellow

# Check Python
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Error "[FAIL] Python 3.12+ was not found in PATH. Please install Python 3.12."
}
$PyVer = (& python --version 2>&1)
Write-Host "  -> Python Detected: $PyVer" -ForegroundColor Green

# Check Node.js
$NodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $NodeCmd) {
    Write-Error "[FAIL] Node.js 20+ was not found in PATH. Please install Node.js."
}
$NodeVer = (& node --version 2>&1)
Write-Host "  -> Node.js Detected: $NodeVer" -ForegroundColor Green

# Check pnpm
$PnpmCmd = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $PnpmCmd) {
    Write-Host "  -> pnpm not found globally, checking npx..." -ForegroundColor Yellow
} else {
    $PnpmVer = (& pnpm --version 2>&1)
    Write-Host "  -> pnpm Detected: v$PnpmVer" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 2. Python Virtual Environment Setup (.venv)
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/6] Configuring Python Virtual Environment (.venv)..." -ForegroundColor Yellow

$UvCmd = Get-Command uv -ErrorAction SilentlyContinue

if (-not (Test-Path $VenvDir)) {
    Write-Host "  -> Creating virtual environment at $VenvDir..." -ForegroundColor Cyan
    if ($UvCmd) {
        & uv venv --python 3.12 $VenvDir
    } else {
        & python -m venv $VenvDir
    }
} else {
    Write-Host "  -> Virtual environment exists at $VenvDir." -ForegroundColor Green
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "[FAIL] Virtual environment python executable not found at $VenvPython."
}

# ------------------------------------------------------------------------------
# 3. Backend Dependency Installation
# ------------------------------------------------------------------------------
if (-not $SkipDeps) {
    Write-Host ""
    Write-Host "[3/6] Installing Pinned Backend Dependencies..." -ForegroundColor Yellow
    if (Test-Path $ReqFile) {
        if ($UvCmd) {
            Write-Host "  -> Syncing dependencies using uv..." -ForegroundColor Cyan
            & uv pip install -r $ReqFile --directory $ProjectRoot
        } else {
            Write-Host "  -> Installing dependencies using pip..." -ForegroundColor Cyan
            & $VenvPython -m pip install -r $ReqFile
        }
        Write-Host "  -> Backend dependencies verified." -ForegroundColor Green
    } else {
        Write-Host "  -> Warning: requirements.txt not found, skipping pip install." -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[3/6] Skipping backend dependency install (-SkipDeps specified)." -ForegroundColor Cyan
}

# ------------------------------------------------------------------------------
# 4. Frontend Dependency Installation
# ------------------------------------------------------------------------------
if (-not $SkipDeps) {
    Write-Host ""
    Write-Host "[4/6] Installing Frontend Tactical Console Dependencies..." -ForegroundColor Yellow
    Push-Location $ConsoleDir
    try {
        if ($PnpmCmd) {
            & pnpm install
        } else {
            & npx pnpm install
        }
        Write-Host "  -> Frontend dependencies installed." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "[4/6] Skipping frontend dependency install (-SkipDeps specified)." -ForegroundColor Cyan
}

# ------------------------------------------------------------------------------
# 5. Database & Model Asset Verification
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[5/6] Verifying Regulatory Data Stores & OpenVINO Models..." -ForegroundColor Yellow

# Verify/Create Data directories
$SqliteDir = Join-Path $DataDir "sqlite"
$PdfsDir = Join-Path $DataDir "pdfs"
$TantivyDir = Join-Path $DataDir "tantivy"
$LanceDir = Join-Path $DataDir "lancedb"

foreach ($dir in @($SqliteDir, $PdfsDir, $TantivyDir, $LanceDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Run DB & Trigger Initialization check via Python
Write-Host "  -> Verifying SQLite tables and append-only audit triggers..." -ForegroundColor Cyan
$InitDbScript = @"
import sys
from pathlib import Path
sys.path.insert(0, '$($ProjectRoot.Replace('\', '/'))')
try:
    from anchor.trust.audit import get_audit_logger
    logger = get_audit_logger()
    logger.init_schema()
    print('[OK] SQLite audit schema & triggers verified.')
except Exception as e:
    print(f'[WARN] Database schema check: {e}')
"@
& $VenvPython -c $InitDbScript

# Verify Model Assets
if (Test-Path $ModelsDir) {
    Write-Host "  -> Models directory verified at $ModelsDir." -ForegroundColor Green
} else {
    Write-Host "  -> [NOTICE] Models directory not found at $ModelsDir. Ensure NTFS junction to model storage is created." -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# 6. Production Frontend Build Compilation
# ------------------------------------------------------------------------------
if (-not $SkipBuild) {
    Write-Host ""
    Write-Host "[6/6] Compiling Next.js 15 Tactical Console Production Bundle..." -ForegroundColor Yellow
    Push-Location $ConsoleDir
    try {
        if ($PnpmCmd) {
            & pnpm build
        } else {
            & npx pnpm build
        }
        Write-Host "  -> Next.js 15 C4ISR Tactical Console compiled successfully." -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "[6/6] Skipping frontend production build (-SkipBuild specified)." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host " [SUCCESS] PROJECT ANCHOR Setup Complete & Ready for Launch!      " -ForegroundColor Green
Write-Host " Launch Command: .\scripts\start.ps1                             " -ForegroundColor Cyan
Write-Host " Demo Command:   .\scripts\demo.ps1                              " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Green