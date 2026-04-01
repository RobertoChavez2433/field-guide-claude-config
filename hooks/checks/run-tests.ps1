# Run targeted flutter tests for changed files only
# FROM SPEC: Section 10 - "flutter test (targeted - changed files only)"
# Test targeting: lib/features/{feature}/.../file.dart -> test/features/{feature}/.../file_test.dart

param()

Write-Host "=== Running targeted tests ===" -ForegroundColor Cyan

# Get staged .dart files (excluding generated)
$stagedFiles = @(git diff --cached --name-only --diff-filter=ACM | Where-Object {
    $_ -match '\.dart$' -and
    $_ -notmatch '\.(g|freezed|mocks)\.dart$'
})

if ($stagedFiles.Count -eq 0) {
    Write-Host "No staged Dart files - skipping tests." -ForegroundColor Yellow
    exit 0
}

# Map source files to test files
$testFiles = @()
foreach ($file in $stagedFiles) {
    if ($file -match '^lib/(.+)\.dart$') {
        $testPath = "test/$($Matches[1])_test.dart"
        if (Test-Path $testPath) {
            $testFiles += $testPath
        }
    }
}

$uniqueTests = $testFiles | Sort-Object -Unique

if ($uniqueTests.Count -eq 0) {
    Write-Host "No matching test files found - skipping. (CI runs full suite.)" -ForegroundColor Yellow
    exit 0
}

Write-Host "Running $($uniqueTests.Count) test file(s)..." -ForegroundColor Cyan

$failed = $false
foreach ($testFile in $uniqueTests) {
    Write-Host "  Testing: $testFile"
    $output = & flutter test $testFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED: $testFile" -ForegroundColor Red
        $output | ForEach-Object { Write-Host "    $_" }
        $failed = $true
    }
}

if ($failed) {
    Write-Host "FAILED: One or more targeted tests failed." -ForegroundColor Red
    exit 1
}

Write-Host "PASSED: $($uniqueTests.Count) targeted test(s)" -ForegroundColor Green
exit 0
