# Run dart analyze — zero errors/warnings required
# FROM SPEC: Section 10 — "dart analyze (zero errors/warnings)"

param()

Write-Host "=== Running dart analyze ===" -ForegroundColor Cyan

$output = & flutter analyze 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "FAILED: dart analyze found issues:" -ForegroundColor Red
    $output | ForEach-Object { Write-Host $_ }
    exit 1
}

Write-Host "PASSED: dart analyze" -ForegroundColor Green
exit 0
