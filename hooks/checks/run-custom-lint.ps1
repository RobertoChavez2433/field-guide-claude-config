# Run custom_lint — zero violations required
# FROM SPEC: Section 10 — "custom_lint check"

param()

Write-Host "=== Running custom_lint ===" -ForegroundColor Cyan

$output = & dart run custom_lint 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "FAILED: custom_lint found violations:" -ForegroundColor Red
    $output | ForEach-Object { Write-Host $_ }
    exit 1
}

# Also check output for lint warnings (custom_lint may exit 0 but print warnings)
$violations = $output | Where-Object { $_ -match '(WARNING|ERROR|INFO)\s*-' }
if ($violations.Count -gt 0) {
    Write-Host "FAILED: custom_lint found $($violations.Count) violation(s):" -ForegroundColor Red
    $violations | ForEach-Object { Write-Host $_ }
    exit 1
}

Write-Host "PASSED: custom_lint" -ForegroundColor Green
exit 0
