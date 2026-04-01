# Pre-commit hook — tiered enforcement
# Hard block: security anti-patterns (exit 1)
# Warn only: code quality patterns (exit 0 with warning)

param()

# NOTE: @() ensures proper array parsing on Windows (line-ending issues without it)
$stagedFiles = @(git diff --cached --name-only --diff-filter=ACM)
if ($LASTEXITCODE -ne 0) { exit 0 }

$hardBlockPatterns = @(
    @{
        Pattern = 'db\.execute|db\.rawQuery|db\.rawUpdate|db\.rawDelete|db\.rawInsert'
        PathFilter = 'presentation/'
        Message = 'BLOCKED: Raw SQL found in presentation layer. Move to repository/datasource.'
    }
)

$warnPatterns = @(
    @{
        Pattern = 'catch\s*\(_\)'
        PathFilter = 'lib/'
        Message = 'WARNING: catch (_) without logging detected. Consider adding Logger call.'
    },
    @{
        Pattern = '\.firstWhere\('
        PathFilter = 'lib/'
        Message = 'WARNING: .firstWhere() detected. Verify it has orElse or use .firstOrNull instead.'
    },
    @{
        Pattern = 'debugPrint'
        PathFilter = 'lib/'
        Message = 'WARNING: debugPrint found. Use Logger.<category>() instead.'
    }
)

$blocked = $false
$warned = $false

foreach ($file in $stagedFiles) {
    if (-not (Test-Path $file)) { continue }

    # Check .env files (filename-based check — catches .env, .env.local, .env.production, etc.)
    if ($file -match '\.env') {
        Write-Host "BLOCKED: .env file staged for commit: $file" -ForegroundColor Red
        $blocked = $true
        continue
    }

    # Only check Dart files for code patterns
    if ($file -notmatch '\.dart$') { continue }

    # Skip generated files — they produce false positives
    if ($file -match '\.(g|freezed|mocks)\.dart$') { continue }

    $content = git show ":0:$file" 2>$null
    if (-not $content) { continue }

    foreach ($pattern in $hardBlockPatterns) {
        if ($pattern.PathFilter -and $file -notmatch $pattern.PathFilter) { continue }
        if ($content -match $pattern.Pattern) {
            Write-Host "$($pattern.Message) [$file]" -ForegroundColor Red
            $blocked = $true
        }
    }

    foreach ($pattern in $warnPatterns) {
        if ($pattern.PathFilter -and $file -notmatch $pattern.PathFilter) { continue }
        if ($content -match $pattern.Pattern) {
            Write-Host "$($pattern.Message) [$file]" -ForegroundColor Yellow
            $warned = $true
        }
    }
}

if ($blocked) {
    Write-Host "`nCommit blocked. Fix the issues above and try again." -ForegroundColor Red
    exit 1
}

if ($warned) {
    Write-Host "`nWarnings found but commit allowed. Consider fixing the issues above." -ForegroundColor Yellow
}

exit 0
