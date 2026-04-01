# Text pattern checks that custom_lint can't catch
# FROM SPEC: Section 10 - grep checks for patterns not detectable via AST

param()

Write-Host "=== Running grep checks ===" -ForegroundColor Cyan

function Get-StagedContent {
    param([string]$FilePath)
    $raw = git show ":0:$FilePath" 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return $raw
}

# Get staged .dart and .sql files
$stagedDart = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.dart$' -and $_ -notmatch '\.(g|freezed|mocks)\.dart$' })
$stagedSql = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.sql$' })
$failed = $false

# Check 1: sync_control writes outside transaction blocks
# FROM SPEC: Section 9 - "sync_control writes outside transaction blocks"
foreach ($file in $stagedDart) {
    $content = (Get-StagedContent $file) -join "`n"
    if ($content -match "sync_control" -and $content -notmatch "transaction\s*\(") {
        # Heuristic: if file mentions sync_control but has no transaction() call, flag it
        $lineNum = 0
        $lines = @()
        foreach ($l in (Get-StagedContent $file)) {
            $lineNum++
            if ($l -match "sync_control") {
                $lines += [PSCustomObject]@{ Filename = $file; LineNumber = $lineNum; Line = $l }
            }
        }
        foreach ($line in $lines) {
            Write-Host "WARNING: sync_control write may be outside transaction: $($line.Filename):$($line.LineNumber)" -ForegroundColor Yellow
        }
    }
}

# Check 2: change_log DELETE without success guard
# FROM SPEC: Section 9 - "change_log DELETE without success guard"
# Skip files that legitimately manage change_log as part of sync/delete infrastructure
foreach ($file in $stagedDart) {
    if ($file -match "soft_delete_service\.dart$|project_lifecycle_service\.dart$|project_repository\.dart$|^lib/features/sync/|^fg_lint_packages/") { continue }
    $stagedLines = Get-StagedContent $file
    if ($null -eq $stagedLines) { continue }
    $lineNum = 0
    $lines = @()
    foreach ($l in $stagedLines) {
        $lineNum++
        if ($l -match "delete.*['""]change_log['""]|['""]change_log['""].*delete") {
            $lines += [PSCustomObject]@{ Filename = $file; LineNumber = $lineNum; Line = $l }
        }
    }
    foreach ($line in $lines) {
        $content = $stagedLines
        $lineIdx = $line.LineNumber - 1
        $contextStart = [Math]::Max(0, $lineIdx - 5)
        $context = $content[$contextStart..$lineIdx] -join "`n"
        if ($context -notmatch "rpcSucceeded|success|result\.errors") {
            Write-Host "BLOCKED: change_log DELETE without success guard: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
            $failed = $true
        }
    }
}

# Check 3: Bare threshold literals
# FROM SPEC: Section 9 - "0.85/0.65/0.45 bare threshold literals"
foreach ($file in $stagedDart) {
    $stagedLines = Get-StagedContent $file
    if ($null -eq $stagedLines) { continue }
    $lineNum = 0
    $lines = @()
    foreach ($l in $stagedLines) {
        $lineNum++
        if ($l -match '\b0\.(85|65|45)\b') {
            $lines += [PSCustomObject]@{ Filename = $file; LineNumber = $lineNum; Line = $l }
        }
    }
    foreach ($line in $lines) {
        Write-Host "WARNING: Bare threshold literal found - extract to named constant: $($line.Filename):$($line.LineNumber): $($line.Line.Trim())" -ForegroundColor Yellow
    }
}

# Check 4: Hardcoded form type outside registry
# FROM SPEC: Section 9 - "'mdot_0582b' outside builtin_forms.dart"
foreach ($file in $stagedDart) {
    if ($file -match "builtin_forms\.dart$|form_type_constants\.dart$|^fg_lint_packages/|inspector_form_provider\.dart$|mdot_hub_screen\.dart$|mdot_0582b_registrations\.dart$|mdot_0582b_form_calculator\.dart$|form_response\.dart$|forms_init\.dart$|form_pdf_service_test\.dart$|form_pdf_service_cache_test\.dart$") { continue }
    $stagedLines = Get-StagedContent $file
    if ($null -eq $stagedLines) { continue }
    $lineNum = 0
    $lines = @()
    foreach ($l in $stagedLines) {
        $lineNum++
        if ($l -match "['""]mdot_0582b['""]") {
            $lines += [PSCustomObject]@{ Filename = $file; LineNumber = $lineNum; Line = $l }
        }
    }
    foreach ($line in $lines) {
        Write-Host "BLOCKED: Hardcoded 'mdot_0582b' outside builtin_forms.dart: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
        $failed = $true
    }
}

# Check 5: AUTOINCREMENT in schema files
# FROM SPEC: Section 9 - "No AUTOINCREMENT in schema"
foreach ($file in ($stagedDart + $stagedSql)) {
    # Skip schema_verifier (reads/validates schema) and test files (create test databases)
    if ($file -match "schema_verifier\.dart$|^test/|^integration_test/") { continue }
    $stagedLines = Get-StagedContent $file
    if ($null -eq $stagedLines) { continue }
    $lineNum = 0
    $lines = @()
    foreach ($l in $stagedLines) {
        $lineNum++
        if ($l -match "AUTOINCREMENT") {
            $lines += [PSCustomObject]@{ Filename = $file; LineNumber = $lineNum; Line = $l }
        }
    }
    foreach ($line in $lines) {
        Write-Host "BLOCKED: AUTOINCREMENT found: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
        $failed = $true
    }
}

# Check 6: ALTER TABLE without IF EXISTS in .sql files
# FROM SPEC: Section 9 - "ALTER TABLE without IF EXISTS in .sql files"
foreach ($file in $stagedSql) {
    $stagedLines = Get-StagedContent $file
    if ($null -eq $stagedLines) { continue }
    $lineNum = 0
    $lines = @()
    foreach ($l in $stagedLines) {
        $lineNum++
        if ($l -match "ALTER\s+TABLE") {
            $lines += [PSCustomObject]@{ Filename = $file; LineNumber = $lineNum; Line = $l }
        }
    }
    foreach ($line in $lines) {
        if ($line.Line -notmatch "IF\s+EXISTS") {
            Write-Host "WARNING: ALTER TABLE without IF EXISTS: $($line.Filename):$($line.LineNumber): $($line.Line.Trim())" -ForegroundColor Yellow
        }
    }
}

# Check 7: Block .env files from being committed
# FROM SPEC: Restored from v1 hook — prevents credential leaks
$stagedEnv = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.env$' })
foreach ($file in $stagedEnv) {
    Write-Host "BLOCKED: .env file staged for commit: $file — remove with 'git reset HEAD $file'" -ForegroundColor Red
    $failed = $true
}

if ($failed) {
    Write-Host "FAILED: grep checks found blocking issues." -ForegroundColor Red
    exit 1
}

Write-Host "PASSED: grep checks" -ForegroundColor Green
exit 0
