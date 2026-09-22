$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$evidenceDir = Join-Path (Split-Path $repoRoot -Parent) "notes\evidence\day1"
$sqlEvidence = Join-Path $evidenceDir "sql-verification.txt"
$jsonEvidence = Join-Path $evidenceDir "day1-validation.json"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "InsightAgent virtual environment is missing. Complete dependency setup first."
}

if (-not $env:INSIGHT_DB_PASSWORD) {
    $secureDatabasePassword = Read-Host "InsightAgent database owner password" -AsSecureString
    $env:INSIGHT_DB_PASSWORD = [System.Net.NetworkCredential]::new("", $secureDatabasePassword).Password
}

if (-not $env:INSIGHT_TOOL_DB_PASSWORD) {
    $secureReadonlyPassword = Read-Host "InsightAgent readonly database password" -AsSecureString
    $env:INSIGHT_TOOL_DB_PASSWORD = [System.Net.NetworkCredential]::new("", $secureReadonlyPassword).Password
}

if (-not $env:INSIGHT_TOOL_DB_PASSWORD) {
    throw "INSIGHT_TOOL_DB_PASSWORD is missing."
}

if (-not $env:INSIGHT_DB_PASSWORD) {
    throw "INSIGHT_DB_PASSWORD is missing."
}

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
Set-Location $repoRoot

Write-Host "[1/6] Generating deterministic synthetic CSV data..."
& $pythonExe -m insight_agent.database.generate_data
if ($LASTEXITCODE -ne 0) { throw "Synthetic data generation failed." }

Write-Host "[2/6] Rebuilding and loading the four InsightAgent tables..."
& $pythonExe -m insight_agent.database.load_data
if ($LASTEXITCODE -ne 0) { throw "Database rebuild or bulk load failed." }

Write-Host "[3/6] Provisioning the least-privilege read-only role..."
& $pythonExe -m insight_agent.database.provision_readonly
if ($LASTEXITCODE -ne 0) { throw "Read-only role provisioning failed." }

Write-Host "[4/6] Creating Week 1 read-only semantic views..."
& $pythonExe -m insight_agent.database.apply_views
if ($LASTEXITCODE -ne 0) { throw "Semantic view creation failed." }

Write-Host "[5/6] Executing the six human-readable SQL checks..."
& $pythonExe -m insight_agent.database.run_verification --output $sqlEvidence
if ($LASTEXITCODE -ne 0) { throw "SQL verification failed." }

Write-Host "[6/6] Validating invariants and freezing Gold Truth..."
& $pythonExe -m insight_agent.database.validate_day1 --evidence-output $jsonEvidence
if ($LASTEXITCODE -ne 0) { throw "Day 1 validation failed." }

Write-Host "InsightAgent Day 1 data initialization completed successfully."
Write-Host "Evidence: $evidenceDir"
