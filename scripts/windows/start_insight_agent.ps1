$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$configPath = Join-Path $repoRoot "configs\insight-agent.toml"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "InsightAgent virtual environment is missing. Complete the uv sync step first."
}

if (-not $env:DEEPSEEK_API_KEY) {
    $secureKey = Read-Host "DeepSeek API Key" -AsSecureString
    $env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
}

if (-not $env:INSIGHT_TOOL_DB_PASSWORD) {
    $secureReadonlyPassword = Read-Host "InsightAgent readonly database password" -AsSecureString
    $env:INSIGHT_TOOL_DB_PASSWORD = [System.Net.NetworkCredential]::new("", $secureReadonlyPassword).Password
}

if (-not $env:INSIGHT_TOOL_DB_PASSWORD) {
    throw "INSIGHT_TOOL_DB_PASSWORD is missing."
}

if (-not $env:DEEPSEEK_API_KEY) {
    throw "DEEPSEEK_API_KEY is missing."
}

# The InsightAgent profile uses a local Hugging Face embedding model.  When the
# model is already cached, force offline resolution so a transient Hugging Face
# TLS/proxy failure cannot prevent the worker manager from starting.  If the
# cache is absent, retain the normal online download behavior.
$hfCache = Join-Path $env:USERPROFILE ".cache\huggingface\hub\models--BAAI--bge-small-zh-v1.5"
$hfSnapshot = Join-Path $hfCache "snapshots"
$hasEmbeddingCache = (
    (Test-Path -LiteralPath $hfSnapshot) -and
    (Get-ChildItem -LiteralPath $hfSnapshot -Directory -ErrorAction SilentlyContinue |
        Where-Object {
            (Test-Path -LiteralPath (Join-Path $_.FullName "config.json")) -and
            (Test-Path -LiteralPath (Join-Path $_.FullName "model.safetensors"))
        } |
        Select-Object -First 1
    )
)
if ($hasEmbeddingCache) {
    $env:HF_HUB_OFFLINE = "1"
    $env:TRANSFORMERS_OFFLINE = "1"
    Write-Host "Using cached embedding model BAAI/bge-small-zh-v1.5 (offline mode)"
}

Set-Location $repoRoot
Write-Host "Starting InsightAgent at http://localhost:5670"
& $pythonExe -m dbgpt.cli.cli_scripts start webserver --config $configPath
exit $LASTEXITCODE
