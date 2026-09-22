param(
    [string]$Model = "deepseek-v4-flash",
    [ValidateSet("dev", "test", "challenge", "all")]
    [string]$Split = "all",
    [int]$Repeats = 3,
    [string]$Endpoint = "http://127.0.0.1:5670/api/v1/chat/react-agent",
    [string]$RunPrefix = "week2-flash"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$resultsRoot = Join-Path $repoRoot "insight_agent\evaluation\results"
$profiles = @("baseline", "positive", "boundary")
$runDirs = [System.Collections.Generic.List[string]]::new()

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "InsightAgent virtual environment is missing."
}
if ($Repeats -lt 1) {
    throw "Repeats must be at least 1."
}

Set-Location $repoRoot
foreach ($profile in $profiles) {
    for ($repeat = 1; $repeat -le $Repeats; $repeat++) {
        $runId = "$RunPrefix-$profile-run$repeat"
        $outputDir = Join-Path $resultsRoot $runId
        if ((Test-Path -LiteralPath $outputDir) -and (Get-ChildItem -LiteralPath $outputDir -Force)) {
            throw "Result directory is non-empty: $outputDir"
        }
        & $pythonExe -m insight_agent.evaluation.run_tool_calling_eval `
            --split $Split `
            --profile $profile `
            --model $Model `
            --temperature 0 `
            --repeat-index $repeat `
            --endpoint $Endpoint `
            --output-dir $outputDir
        if ($LASTEXITCODE -ne 0) {
            throw "Week 2 run failed: $runId"
        }
        $runDirs.Add($outputDir)
    }
}

$aggregateDir = Join-Path $resultsRoot "$RunPrefix-aggregate"
$arguments = @(
    "-m", "insight_agent.evaluation.tool_confusion_matrix",
    "--output-dir", $aggregateDir
)
foreach ($runDir in $runDirs) {
    $arguments += @("--run-dir", $runDir)
}
& $pythonExe @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Week 2 aggregation failed."
}

Write-Host "Week 2 Tool Calling runs completed."
Write-Host "Aggregate: $aggregateDir"
