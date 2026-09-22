param(
    [ValidateSet("baseline", "after")]
    [string]$Profile,
    [ValidateSet("dev", "test", "challenge", "all")]
    [string]$Split = "all",
    [string]$Model = "deepseek-v4-flash",
    [ValidateRange(1, 20)]
    [int]$Repeats = 3,
    [string]$RunPrefix = "week4-reliability",
    [string]$ResultsRoot = "insight_agent/evaluation/results",
    [string]$Endpoint = "http://127.0.0.1:5670/api/v1/chat/react-agent",
    [ValidateRange(1, 600)]
    [int]$Timeout = 150
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Project virtual environment is missing: $python"
}

Push-Location $repoRoot
try {
    for ($repeat = 1; $repeat -le $Repeats; $repeat++) {
        $runId = "$RunPrefix-$Profile-$Model-$Split-run$repeat"
        $output = Join-Path $ResultsRoot $runId
        if (Test-Path -LiteralPath $output) {
            throw "Result directory already exists; refusing overwrite: $output"
        }
        & $python -m insight_agent.evaluation.run_reliability_eval `
            --profile $Profile `
            --split $Split `
            --model $Model `
            --repeat-index $repeat `
            --timeout $Timeout `
            --endpoint $Endpoint `
            --output-dir $output
        if ($LASTEXITCODE -ne 0) {
            throw "Week 4 reliability run failed: $runId"
        }
    }
}
finally {
    Pop-Location
}
