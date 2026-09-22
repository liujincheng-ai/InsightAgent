param(
    [ValidateSet("dev", "test", "challenge", "all")]
    [string]$Split = "dev",
    [string]$RunPrefix = "week3-retrieval",
    [string]$ResultsRoot = "insight_agent/evaluation/results"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Project virtual environment is missing: $python"
}

$chunkSizes = @(256, 512, 800)
$overlaps = @(0, 50, 100)
$topKs = @(3, 5, 8)
$retrievers = @("vector", "bm25")

Push-Location $repoRoot
try {
    foreach ($retriever in $retrievers) {
        foreach ($chunkSize in $chunkSizes) {
            foreach ($overlap in $overlaps) {
                foreach ($topK in $topKs) {
                    $runId = "$RunPrefix-$retriever-c$chunkSize-o$overlap-k$topK-$Split"
                    $output = Join-Path $ResultsRoot $runId
                    if (Test-Path -LiteralPath $output) {
                        throw "Result directory already exists; refusing overwrite: $output"
                    }
                    & $python -m insight_agent.evaluation.run_rag_eval `
                        --mode retrieval `
                        --retriever $retriever `
                        --chunk-size $chunkSize `
                        --chunk-overlap $overlap `
                        --top-k $topK `
                        --split $Split `
                        --output-dir $output
                    if ($LASTEXITCODE -ne 0) {
                        throw "Week 3 retrieval run failed: $runId"
                    }
                }
            }
        }
    }
}
finally {
    Pop-Location
}
