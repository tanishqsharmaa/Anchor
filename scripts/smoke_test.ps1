<#
.SYNOPSIS
    smoke_test.ps1 — Automated Regression Smoke Test for PROJECT ANCHOR (ENH-015)
.DESCRIPTION
    Validates backend liveness, readiness, query resolution, AutoDeck generation,
    and evaluation report endpoints. Returns exit code 0 on success, 1 on failure.
#>

param (
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [int]$TimeoutSeconds = 15
)

$ErrorActionPreference = "Stop"
$failures = 0

function Test-Endpoint {
    param (
        [string]$Name,
        [string]$Uri,
        [string]$Method = "GET",
        [hashtable]$Body = $null,
        [scriptblock]$Validator
    )
    Write-Host "[TEST] $Name ... " -NoNewline
    try {
        $params = @{
            Uri = $Uri
            Method = $Method
            TimeoutSec = $TimeoutSeconds
            ContentType = "application/json"
        }
        if ($Body) {
            $params["Body"] = ($Body | ConvertTo-Json -Depth 5)
        }
        $res = Invoke-RestMethod @params
        $passed = & $Validator $res
        if ($passed) {
            Write-Host "PASS" -ForegroundColor Green
        } else {
            Write-Host "FAIL (Validation Check Failed)" -ForegroundColor Red
            $script:failures++
        }
    } catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
        $script:failures++
    }
}

Write-Host "=================================================================="
Write-Host "PROJECT ANCHOR — AUTOMATED REGRESSION SMOKE TEST"
Write-Host "=================================================================="

# 1. Health Probe
Test-Endpoint -Name "Liveness Probe /health" -Uri "$BaseUrl/health" -Validator {
    param($r) $r.status -eq "ok"
}

# 2. Readiness Probe
Test-Endpoint -Name "Readiness Probe /ready" -Uri "$BaseUrl/ready" -Validator {
    param($r) $r.ready -eq $true -or $r.stores -ne $null
}

# 3. Structured Query Resolution (Path A)
Test-Endpoint -Name "Structured Query (Schedule 7, Tier 3 with IFA)" -Uri "$BaseUrl/query" -Method "POST" -Body @{
    question = "What is the financial power of Fleet Commander (Tier 3) under Schedule 7 with IFA?"
    stream = $false
} -Validator {
    param($r) $r.answer -match "18.00" -or $r.data.answer -match "18.00"
}

# 4. Multi-Schedule Comparative Query (ENH-002)
Test-Endpoint -Name "Comparative Query (Schedule 7 vs 8)" -Uri "$BaseUrl/query" -Method "POST" -Body @{
    question = "Compare financial powers of Tier 3 under Schedule 7 and Schedule 8 with IFA."
    stream = $false
} -Validator {
    param($r) ($r.answer -ne $null -and $r.answer.Length -gt 20) -or ($r.data.answer -ne $null)
}

# 5. Out-of-Domain Abstention Query
Test-Endpoint -Name "Abstention Verification (Schedule 99)" -Uri "$BaseUrl/query" -Method "POST" -Body @{
    question = "What is the sanction limit under Schedule 99 for Fleet Commander?"
    stream = $false
} -Validator {
    param($r) $r.status -eq "abstained" -or $r.refusal_reason -ne $null -or $r.data.status -eq "abstained"
}

# 6. Deck Generation Endpoint
Test-Endpoint -Name "AutoDeck Generation /deck" -Uri "$BaseUrl/deck" -Method "POST" -Body @{
    topic = "Financial Delegations for Fleet Commanders"
    num_slides = 3
} -Validator {
    param($r) $r.success -eq $true -and $r.data.deck_id -ne $null
}

# 7. Evaluation Latest Report
Test-Endpoint -Name "Eval Report /eval/report" -Uri "$BaseUrl/eval/report" -Validator {
    param($r) $r.total_questions -gt 0 -or $r.metrics -ne $null
}

Write-Host "=================================================================="
if ($failures -eq 0) {
    Write-Host "ALL SMOKE TESTS PASSED (0 FAILURES)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "SMOKE TESTS FAILED WITH $failures ERRORS" -ForegroundColor Red
    exit 1
}
