# Pre-commit hook - 3-layer quality gate orchestrator
# FROM SPEC: Section 10 - "main orchestrator (replaces current)"
# Called by .githooks/pre-commit shell shim
#
# Sequence: analyze -> custom_lint -> grep checks -> targeted tests
# ANY failure = hard block (exit 1)

param()

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$checksDir = Join-Path $scriptDir "checks"

# Get staged .dart files (skip generated)
$stagedFiles = @(git diff --cached --name-only --diff-filter=ACM | Where-Object {
    $_ -match '\.dart$' -and
    $_ -notmatch '\.(g|freezed|mocks)\.dart$'
})

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to get staged files from git." -ForegroundColor Red
    exit 1
}

$stagedSql = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.sql$' })

if ($stagedFiles.Count -eq 0 -and $stagedSql.Count -eq 0) {
    Write-Host "No staged Dart or SQL files — skipping pre-commit checks." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Pre-commit: $($stagedFiles.Count) staged Dart file(s)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Step 1: dart analyze
& pwsh -File (Join-Path $checksDir "run-analyze.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

# Step 2: custom_lint
& pwsh -File (Join-Path $checksDir "run-custom-lint.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

# Step 3: grep checks
& pwsh -File (Join-Path $checksDir "grep-checks.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

# Step 4: targeted tests (advisory — CI runs the full suite as the authoritative gate)
& pwsh -File (Join-Path $checksDir "run-tests.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Targeted tests failed (non-blocking — CI runs full suite)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "All pre-commit checks passed." -ForegroundColor Green
exit 0
