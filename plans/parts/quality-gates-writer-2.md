## Phase 4: Pre-Commit Hook System

### Sub-phase 4.1: Archive Existing Pre-Commit Hook

**Files:**
- Move: `.claude/hooks/pre-commit.ps1` → `.claude/hooks/archived/pre-commit-v1.ps1`

**Agent**: `general-purpose`

#### Step 4.1.1: Archive the current hook

```powershell
Copy-Item ".claude/hooks/pre-commit.ps1" ".claude/hooks/archived/pre-commit-v1.ps1"
```

<!-- WHY: Preserve the existing hook for reference. The archived/ directory already exists per ground truth. -->

---

### Sub-phase 4.2: Create Check Scripts

**Files:**
- Create: `.claude/hooks/checks/run-analyze.ps1`
- Create: `.claude/hooks/checks/run-custom-lint.ps1`
- Create: `.claude/hooks/checks/run-tests.ps1`
- Create: `.claude/hooks/checks/grep-checks.ps1`

**Agent**: `general-purpose`

#### Step 4.2.1: Create run-analyze.ps1

Create `.claude/hooks/checks/run-analyze.ps1`:

```powershell
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
```

#### Step 4.2.2: Create run-custom-lint.ps1

Create `.claude/hooks/checks/run-custom-lint.ps1`:

```powershell
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
```

#### Step 4.2.3: Create run-tests.ps1

Create `.claude/hooks/checks/run-tests.ps1`:

```powershell
# Run targeted flutter tests for changed files only
# FROM SPEC: Section 10 — "flutter test (targeted — changed files only)"
# Test targeting: lib/features/{feature}/.../file.dart → test/features/{feature}/.../file_test.dart

param()

Write-Host "=== Running targeted tests ===" -ForegroundColor Cyan

# Get staged .dart files (excluding generated)
$stagedFiles = @(git diff --cached --name-only --diff-filter=ACM | Where-Object {
    $_ -match '\.dart$' -and
    $_ -notmatch '\.(g|freezed|mocks)\.dart$'
})

if ($stagedFiles.Count -eq 0) {
    Write-Host "No staged Dart files — skipping tests." -ForegroundColor Yellow
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
    Write-Host "No matching test files found — skipping. (CI runs full suite.)" -ForegroundColor Yellow
    exit 0
}

Write-Host "Running $($uniqueTests.Count) test file(s)..." -ForegroundColor Cyan

$failed = $false
foreach ($testFile in $uniqueTests) {
    Write-Host "  Testing: $testFile"
    & flutter test $testFile 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED: $testFile" -ForegroundColor Red
        $failed = $true
    }
}

if ($failed) {
    Write-Host "FAILED: One or more targeted tests failed." -ForegroundColor Red
    exit 1
}

Write-Host "PASSED: $($uniqueTests.Count) targeted test(s)" -ForegroundColor Green
exit 0
```

#### Step 4.2.4: Create grep-checks.ps1

Create `.claude/hooks/checks/grep-checks.ps1`:

```powershell
# Text pattern checks that custom_lint can't catch
# FROM SPEC: Section 10 — grep checks for patterns not detectable via AST

param()

Write-Host "=== Running grep checks ===" -ForegroundColor Cyan

# Get staged .dart and .sql files
$stagedDart = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.dart$' })
$stagedSql = @(git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.sql$' })
$failed = $false

# Check 1: sync_control writes outside transaction blocks
# FROM SPEC: Section 9 — "sync_control writes outside transaction blocks"
foreach ($file in $stagedDart) {
    $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
    if ($content -match "sync_control" -and $content -notmatch "transaction\s*\(") {
        # Heuristic: if file mentions sync_control but has no transaction() call, flag it
        $lines = Select-String -Path $file -Pattern "sync_control" -SimpleMatch
        foreach ($line in $lines) {
            Write-Host "WARNING: sync_control write may be outside transaction: $($line.Filename):$($line.LineNumber)" -ForegroundColor Yellow
        }
    }
}

# Check 2: change_log DELETE without success guard
# FROM SPEC: Section 9 — "change_log DELETE without success guard"
foreach ($file in $stagedDart) {
    $lines = Select-String -Path $file -Pattern "delete.*change_log|change_log.*delete" -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        # Check surrounding context for success guard
        $content = Get-Content $file -ErrorAction SilentlyContinue
        $lineNum = $line.LineNumber - 1
        $contextStart = [Math]::Max(0, $lineNum - 5)
        $context = $content[$contextStart..$lineNum] -join "`n"
        if ($context -notmatch "rpcSucceeded|success|result\.errors") {
            Write-Host "BLOCKED: change_log DELETE without success guard: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
            $failed = $true
        }
    }
}

# Check 3: Bare threshold literals
# FROM SPEC: Section 9 — "0.85/0.65/0.45 bare threshold literals"
foreach ($file in $stagedDart) {
    $lines = Select-String -Path $file -Pattern '\b0\.(85|65|45)\b' -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        Write-Host "WARNING: Bare threshold literal found — extract to named constant: $($line.Filename):$($line.LineNumber): $($line.Line.Trim())" -ForegroundColor Yellow
    }
}

# Check 4: Hardcoded form type outside registry
# FROM SPEC: Section 9 — "'mdot_0582b' outside builtin_forms.dart"
foreach ($file in $stagedDart) {
    if ($file -match "builtin_forms\.dart$") { continue }
    $lines = Select-String -Path $file -Pattern "mdot_0582b" -SimpleMatch -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        Write-Host "BLOCKED: Hardcoded 'mdot_0582b' outside builtin_forms.dart: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
        $failed = $true
    }
}

# Check 5: AUTOINCREMENT in schema files
# FROM SPEC: Section 9 — "No AUTOINCREMENT in schema"
foreach ($file in ($stagedDart + $stagedSql)) {
    $lines = Select-String -Path $file -Pattern "AUTOINCREMENT" -SimpleMatch -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        Write-Host "BLOCKED: AUTOINCREMENT found: $($line.Filename):$($line.LineNumber)" -ForegroundColor Red
        $failed = $true
    }
}

# Check 6: ALTER TABLE without IF EXISTS in .sql files
# FROM SPEC: Section 9 — "ALTER TABLE without IF EXISTS in .sql files"
foreach ($file in $stagedSql) {
    $lines = Select-String -Path $file -Pattern "ALTER\s+TABLE" -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line.Line -notmatch "IF\s+EXISTS") {
            Write-Host "WARNING: ALTER TABLE without IF EXISTS: $($line.Filename):$($line.LineNumber): $($line.Line.Trim())" -ForegroundColor Yellow
        }
    }
}

if ($failed) {
    Write-Host "FAILED: grep checks found blocking issues." -ForegroundColor Red
    exit 1
}

Write-Host "PASSED: grep checks" -ForegroundColor Green
exit 0
```

---

### Sub-phase 4.3: Create New Pre-Commit Orchestrator

**Files:**
- Create: `.claude/hooks/pre-commit.ps1` (replaces archived version)

**Agent**: `general-purpose`

#### Step 4.3.1: Write the orchestrator

Create `.claude/hooks/pre-commit.ps1`:

```powershell
# Pre-commit hook — 3-layer quality gate orchestrator
# FROM SPEC: Section 10 — "main orchestrator (replaces current)"
# Called by .githooks/pre-commit shell shim
#
# Sequence: analyze → custom_lint → grep checks → targeted tests
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

if ($stagedFiles.Count -eq 0) {
    Write-Host "No staged Dart files — skipping pre-commit checks." -ForegroundColor Yellow
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

# Step 4: targeted tests
& pwsh -File (Join-Path $checksDir "run-tests.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "All pre-commit checks passed." -ForegroundColor Green
exit 0
```

<!-- NOTE: .githooks/pre-commit already delegates to this script via `pwsh -ExecutionPolicy Bypass -File ".claude/hooks/pre-commit.ps1"`. No changes needed to the shell shim. -->

---

### Sub-phase 4.4: Verify Pre-Commit Integration

**Files:** None (verification only)

**Agent**: `general-purpose`

#### Step 4.4.1: Verify shell shim exists

Confirm `.githooks/pre-commit` contains:
```sh
#!/bin/sh
pwsh -ExecutionPolicy Bypass -File ".claude/hooks/pre-commit.ps1"
exit $?
```

#### Step 4.4.2: Verify git hooks path

Run: `pwsh -Command "git config core.hooksPath"`
Expected: `.githooks` (or confirm the shim is in the right location)

#### Step 4.4.3: Smoke test — stage a clean file and commit

```powershell
# Create a trivial change, stage it, attempt commit
# Should pass all 4 checks
```

Run: `pwsh -Command "git stash; git add -A; git stash pop"` (or equivalent dry run)

#### Step 4.4.4: Smoke test — verify violation is blocked

Temporarily add a violation to a staged file (e.g., `Supabase.instance.client` in a presentation file), stage it, and attempt commit. The grep checks or custom_lint should block.

---

## Phase 5: CI & GitHub Automation

### Sub-phase 5.1: Delete Broken Workflows

**Files:**
- Delete: `.github/workflows/e2e-tests.yml`
- Delete: `.github/workflows/nightly-e2e.yml`

**Agent**: `general-purpose`

#### Step 5.1.1: Delete deprecated workflows

```powershell
Remove-Item ".github/workflows/e2e-tests.yml" -Force
Remove-Item ".github/workflows/nightly-e2e.yml" -Force
```

<!-- FROM SPEC: Section 14 — "Delete existing broken workflows" -->
<!-- Ground truth: both files verified to exist -->

---

### Sub-phase 5.2: Create quality-gate.yml

**Files:**
- Create: `.github/workflows/quality-gate.yml`

**Agent**: `general-purpose`

#### Step 5.2.1: Write the main CI workflow

Create `.github/workflows/quality-gate.yml`:

```yaml
name: Quality Gate

on:
  push:
    branches: ['*']
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  FLUTTER_VERSION: '3.32.2'

jobs:
  # ============================================
  # Job 1: Analyze + Test (~5 min)
  # FROM SPEC: Section 11 — "Job 1: analyze-and-test"
  # ============================================
  analyze-and-test:
    name: Analyze & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: subosito/flutter-action@v2
        with:
          flutter-version: ${{ env.FLUTTER_VERSION }}
          channel: stable
          cache: true

      - name: Install dependencies
        run: flutter pub get

      - name: Create .env for build
        run: |
          echo "SUPABASE_URL=${{ secrets.SUPABASE_URL }}" > .env
          echo "SUPABASE_ANON_KEY=${{ secrets.SUPABASE_ANON_KEY }}" >> .env

      - name: Dart analyze (zero errors)
        # FROM SPEC: "dart analyze (zero errors — NO --no-fatal-infos flag)"
        run: flutter analyze

      - name: Custom lint check
        run: dart run custom_lint

      - name: Run full test suite
        # FROM SPEC: "flutter test (full suite, all 337+ test files)"
        run: flutter test

  # ============================================
  # Job 2: Architecture Validation (~1 min)
  # FROM SPEC: Section 11 — "Job 2: architecture-validation"
  # ============================================
  architecture-validation:
    name: Architecture Validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: No AUTOINCREMENT in schema
        run: |
          if grep -rn "AUTOINCREMENT" lib/core/database/ supabase/migrations/ 2>/dev/null; then
            echo "::error::AUTOINCREMENT found in schema files"
            exit 1
          fi

      - name: Deprecated screen exports check
        run: |
          if grep -rn "FormsListScreen\|FormFillScreen" lib/ --include="*.dart" 2>/dev/null | grep -v "// deprecated\|@Deprecated\|_deprecated"; then
            echo "::error::Deprecated screen exports found"
            exit 1
          fi

      - name: change_log trigger count matches adapter count
        # FROM SPEC: "change_log trigger count (20) ≈ adapter count (22, minus 2 push-only)"
        run: |
          TRIGGER_COUNT=$(grep -c "triggersForTable" lib/core/database/schema/sync_engine_tables.dart 2>/dev/null || echo 0)
          ADAPTER_COUNT=$(grep -c "Adapter()" lib/features/sync/engine/sync_registry.dart 2>/dev/null || echo 0)
          echo "Triggers: $TRIGGER_COUNT, Adapters: $ADAPTER_COUNT"
          # Allow ±2 difference (push-only adapters don't have triggers)
          DIFF=$((ADAPTER_COUNT - TRIGGER_COUNT))
          if [ "$DIFF" -lt 0 ] || [ "$DIFF" -gt 3 ]; then
            echo "::error::Trigger/adapter count mismatch: $TRIGGER_COUNT triggers vs $ADAPTER_COUNT adapters"
            exit 1
          fi

      - name: FK index verification
        run: |
          # Check that REFERENCES columns have matching CREATE INDEX
          echo "FK index check — scanning migrations..."
          REFS=$(grep -rn "REFERENCES" lib/core/database/database_service.dart supabase/migrations/ 2>/dev/null | grep -oP '\w+(?=\s+TEXT\s+REFERENCES|\s+INTEGER\s+REFERENCES)' || true)
          MISSING=0
          for col in $REFS; do
            if ! grep -rq "CREATE INDEX.*$col" lib/core/database/database_service.dart supabase/migrations/ 2>/dev/null; then
              echo "::warning::Missing index for FK column: $col"
              MISSING=$((MISSING + 1))
            fi
          done
          if [ "$MISSING" -gt 0 ]; then
            echo "::warning::$MISSING FK columns without indexes"
          fi

  # ============================================
  # Job 3: Security Scanning (~1 min)
  # FROM SPEC: Section 11 — "Job 3: security-scanning"
  # ============================================
  security-scanning:
    name: Security Scanning
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Supabase singleton audit
        # FROM SPEC: "Supabase singleton usage audit (must be zero outside DI root)"
        run: |
          VIOLATIONS=$(grep -rn "Supabase\.instance\.client" lib/ --include="*.dart" \
            | grep -v "app_initializer\.dart" \
            | grep -v "background_sync_handler\.dart" \
            | grep -v "// ignore: avoid_supabase_singleton" || true)
          if [ -n "$VIOLATIONS" ]; then
            echo "::error::Supabase.instance.client violations found outside DI root:"
            echo "$VIOLATIONS"
            exit 1
          fi

      - name: Raw database.delete() audit
        # FROM SPEC: "Raw database.delete() outside SoftDeleteService (must be zero)"
        run: |
          VIOLATIONS=$(grep -rn "database\.delete\|\.delete(" lib/ --include="*.dart" \
            | grep -v "soft_delete_service\.dart" \
            | grep -v "generic_local_datasource\.dart" \
            | grep -v "sync/engine/" \
            | grep -v "change_log\|change_tracker\|sync_control" \
            | grep -v "// ignore: avoid_raw_database_delete" || true)
          # Filter to only actual database.delete calls (heuristic)
          REAL=$(echo "$VIOLATIONS" | grep -i "database\.\|db\.\|txn\." || true)
          if [ -n "$REAL" ]; then
            echo "::warning::Potential raw database.delete() calls found:"
            echo "$REAL"
          fi

      - name: Path traversal guard audit
        run: |
          VIOLATIONS=$(grep -rn "\.contains('\.\.')" lib/ --include="*.dart" \
            | grep -v "path\.normalize" || true)
          if [ -n "$VIOLATIONS" ]; then
            echo "::warning::Weak path traversal guard (contains('..') without normalize):"
            echo "$VIOLATIONS"
          fi

      - name: sync_control transaction boundary check
        run: |
          # Files that write to sync_control should do so inside try/finally
          FILES=$(grep -rln "sync_control" lib/ --include="*.dart" 2>/dev/null || true)
          for file in $FILES; do
            if grep -q "sync_control.*value.*=.*'1'" "$file" 2>/dev/null; then
              if ! grep -q "finally" "$file" 2>/dev/null; then
                echo "::warning::sync_control write without try/finally in $file"
              fi
            fi
          done

      - name: change_log cleanup success-guard check
        run: |
          VIOLATIONS=$(grep -rn "delete.*change_log\|change_log.*delete" lib/ --include="*.dart" 2>/dev/null \
            | grep -v "rpcSucceeded\|success\|result\.errors" || true)
          if [ -n "$VIOLATIONS" ]; then
            echo "::warning::change_log DELETE without success guard:"
            echo "$VIOLATIONS"
          fi
```

---

### Sub-phase 5.3: Create labeler.yml

**Files:**
- Create: `.github/workflows/labeler.yml`
- Create: `.github/labeler.yml`

**Agent**: `general-purpose`

#### Step 5.3.1: Create labeler workflow

Create `.github/workflows/labeler.yml`:

```yaml
name: PR Labeler

on:
  pull_request_target:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/labeler@v5
        with:
          repo-token: ${{ secrets.GITHUB_TOKEN }}
```

#### Step 5.3.2: Create label config

Create `.github/labeler.yml`:

```yaml
# FROM SPEC: Section 11 — PR auto-labeling by changed file paths
sync:
  - changed-files:
    - any-glob-to-any-file: 'lib/features/sync/**'

pdf:
  - changed-files:
    - any-glob-to-any-file: 'lib/features/pdf/**'

auth:
  - changed-files:
    - any-glob-to-any-file: 'lib/features/auth/**'

database:
  - changed-files:
    - any-glob-to-any-file: 'lib/core/database/**'

ui:
  - changed-files:
    - any-glob-to-any-file: 'lib/features/*/presentation/**'

tests:
  - changed-files:
    - any-glob-to-any-file: 'test/**'

config:
  - changed-files:
    - any-glob-to-any-file:
      - '.github/**'
      - 'analysis_options.yaml'
      - 'pubspec.yaml'
```

---

### Sub-phase 5.4: Create sync-defects.yml

**Files:**
- Create: `.github/workflows/sync-defects.yml`

**Agent**: `general-purpose`

#### Step 5.4.1: Write the defect sync workflow

Create `.github/workflows/sync-defects.yml`:

```yaml
name: Sync Defects to Issues

# FROM SPEC: Section 11 — "defect-to-GitHub-Issues sync"
on:
  push:
    branches: [main]
    paths:
      - '.claude/defects/**'

permissions:
  issues: write
  contents: read

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Parse and sync defects
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const glob = require('@actions/glob');

            const globber = await glob.create('.claude/defects/_defects-*.md');
            const files = await globber.glob();

            for (const file of files) {
              const content = fs.readFileSync(file, 'utf8');
              const feature = file.match(/_defects-(\w+)\.md/)?.[1] || 'unknown';

              // Parse defect entries (## headers)
              const defects = content.split(/^## /m).slice(1);

              for (const defect of defects) {
                const title = defect.split('\n')[0].trim();
                const body = defect.split('\n').slice(1).join('\n').trim();
                const issueTitle = `[${feature}] ${title}`;

                // Check if issue already exists
                const { data: existing } = await github.rest.issues.listForRepo({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  state: 'all',
                  labels: `defect,${feature}`,
                  per_page: 100,
                });

                const match = existing.find(i => i.title === issueTitle);

                if (!match) {
                  // Create new issue
                  await github.rest.issues.create({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    title: issueTitle,
                    body: `*Auto-synced from \`.claude/defects/_defects-${feature}.md\`*\n\n${body}`,
                    labels: ['defect', feature],
                  });
                  console.log(`Created issue: ${issueTitle}`);
                }
              }
            }
```

---

### Sub-phase 5.5: Create stale-branches.yml

**Files:**
- Create: `.github/workflows/stale-branches.yml`

**Agent**: `general-purpose`

#### Step 5.5.1: Write the branch cleanup workflow

Create `.github/workflows/stale-branches.yml`:

```yaml
name: Clean Up Merged Branches

# FROM SPEC: Section 11 — "Auto-deletes the source branch after merge"
on:
  pull_request:
    types: [closed]

permissions:
  contents: write

jobs:
  cleanup:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: Delete merged branch
        uses: actions/github-script@v7
        with:
          script: |
            const branch = context.payload.pull_request.head.ref;
            if (branch === 'main' || branch === 'master' || branch === 'develop') {
              console.log(`Skipping protected branch: ${branch}`);
              return;
            }
            try {
              await github.rest.git.deleteRef({
                owner: context.repo.owner,
                repo: context.repo.repo,
                ref: `heads/${branch}`,
              });
              console.log(`Deleted branch: ${branch}`);
            } catch (e) {
              console.log(`Branch ${branch} already deleted or protected: ${e.message}`);
            }
```

---

### Sub-phase 5.6: Create dependabot.yml

**Files:**
- Create: `.github/dependabot.yml`

**Agent**: `general-purpose`

#### Step 5.6.1: Write dependabot config

Create `.github/dependabot.yml`:

```yaml
# FROM SPEC: Section 11 — "Weekly pub dependency updates"
version: 2
updates:
  - package-ecosystem: "pub"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
    open-pull-requests-limit: 5
```

---

### Sub-phase 5.7: Verify CI Workflows

**Files:** None (verification only)

**Agent**: `general-purpose`

#### Step 5.7.1: Validate YAML syntax

Run: `pwsh -Command "Get-ChildItem .github/workflows/*.yml | ForEach-Object { Write-Host $_.Name; python3 -c \"import yaml; yaml.safe_load(open('$($_.FullName)'))\"; if (\$LASTEXITCODE -ne 0) { Write-Host 'INVALID' -ForegroundColor Red } else { Write-Host 'OK' -ForegroundColor Green } }"`

Or manually validate each YAML file.

#### Step 5.7.2: Push to test branch and verify

After committing all changes:
1. Create a feature branch
2. Push to remote
3. Verify `quality-gate.yml` triggers on push
4. Create a PR to main
5. Verify all 3 jobs run: `analyze-and-test`, `architecture-validation`, `security-scanning`
6. Verify labeler applies labels based on changed file paths

---

## Phase 6: Branch Protection + Rule/Doc Updates

### Sub-phase 6.1: Configure Branch Protection

**Files:** None (GitHub API configuration)

**Agent**: `general-purpose`

#### Step 6.1.1: Set branch protection rules via gh CLI

```powershell
# FROM SPEC: Section 12 — Branch protection for main
gh api repos/{owner}/{repo}/branches/main/protection -X PUT --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["analyze-and-test", "architecture-validation", "security-scanning"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

<!-- NOTE: The implementing agent must replace {owner}/{repo} with the actual values: RobertoChavez2433/construction-inspector-tracking-app -->

#### Step 6.1.2: Enable auto-delete head branches

```powershell
# FROM SPEC: Section 12 — "Auto-delete head branches"
gh api repos/{owner}/{repo} -X PATCH -f delete_branch_on_merge=true
```

#### Step 6.1.3: Verify branch protection

Run: `pwsh -Command "gh api repos/RobertoChavez2433/construction-inspector-tracking-app/branches/main/protection --jq '.required_status_checks.contexts[]'"`
Expected: Lists `analyze-and-test`, `architecture-validation`, `security-scanning`

---

### Sub-phase 6.2: Update Rule/Doc Files

**Files:**
- Modify: `.claude/rules/database/schema-patterns.md`
- Modify: `.claude/rules/architecture.md`
- Modify: `.claude/rules/frontend/flutter-ui.md`
- Modify: `.claude/rules/sync/sync-patterns.md`
- Modify: `.claude/rules/testing/patrol-testing.md`

**Agent**: `general-purpose`

#### Step 6.2.1: Update schema-patterns.md

Remove any reference to `is_deleted INTEGER DEFAULT 0`. The column does NOT exist — only `deleted_at` and `deleted_by` are used.

<!-- FROM SPEC: Section 16 — "Remove is_deleted INTEGER DEFAULT 0 — column doesn't exist" -->

#### Step 6.2.2: Update architecture.md

Add an "Anti-Patterns (Enforced by Lint)" section:

```markdown
## Anti-Patterns (Enforced by Lint)

These patterns are enforced by `field_guide_lints` custom lint rules. Violations block commit and CI.

| Anti-Pattern | Rule | Fix |
|-------------|------|-----|
| `Supabase.instance.client` outside DI root | A1 | Inject via constructor from AppInitializer |
| `DatabaseService()` outside DI root | A2 | Inject via constructor |
| Raw SQL in presentation/ | A3 | Use repository/datasource methods |
| Raw SQL in di/ files | A4 | Move to repository layer |
| Datasource imports in presentation/ | A5 | Import repository, not datasource |
| Business logic (await/try) in di/ files | A6 | Move to use case or repository |
| Provider construction outside buildAppProviders() | A7 | Register in app_providers.dart |
| Service construction in widgets | A8 | Inject via Provider.of or context.read |
| Silent catch blocks | A9 | Add Logger.<category>() call |
| `AppTheme.*` color constants | A12 | Use three-tier color system |
| Hardcoded `Colors.*` in presentation | A13 | Use theme tokens |
```

#### Step 6.2.3: Update flutter-ui.md

Add accessibility section:

```markdown
## Accessibility

- **Touch targets**: Minimum 48dp × 48dp for all interactive elements
- **Semantics labels**: All icons and images must have `Semantics` or `semanticLabel`
- **Color contrast**: Use theme tokens (three-tier system) which are designed for contrast
- **Dark mode testing**: All UI must be verified in dark, light, and high-contrast themes
```

Strengthen color rule to reference lint enforcement:

```markdown
## Color System (Enforced by A12, A13)

Colors MUST use the three-tier system. Violations are blocked by custom lint rules.
See spec Section 3 for the full tier mapping.
```

#### Step 6.2.4: Update sync-patterns.md

Add enforced invariants:

```markdown
## Enforced Invariants (Lint Rules)

- **sync_control flag MUST be inside transaction** (S3) — set pulling='1' inside try/finally
- **change_log cleanup MUST be conditional on RPC success** (S2) — never unconditional DELETE
- **ConflictAlgorithm.ignore MUST have rowId==0 fallback** (S1) — check return value, UPDATE on 0
- **No sync_status column** (S4) — deprecated pattern, only change_log is used
- **toMap() MUST include project_id for synced child models** (S5)
- **_lastSyncTime only updated in success path** (S8)
```

#### Step 6.2.5: Update patrol-testing.md

Add deprecated stacks section:

```markdown
## Deprecated Testing Stacks

| Stack | Status | Replacement |
|-------|--------|-------------|
| Patrol | Removed | Unit/widget tests + manual ADB testing |
| flutter_driver | Removed | Unit/widget tests + manual ADB testing |

**Lint rule T6** blocks imports of `patrol` or `flutter_driver` packages.
```

---

### Sub-phase 6.3: End-to-End Verification

**Files:** None (verification only)

**Agent**: `general-purpose`

#### Step 6.3.1: Full local verification

Run in sequence:
1. `pwsh -Command "flutter pub get"`
2. `pwsh -Command "flutter analyze"` — expect zero issues
3. `pwsh -Command "dart run custom_lint"` — expect zero violations
4. `pwsh -Command "flutter test"` — expect all pass

#### Step 6.3.2: Pre-commit verification

Stage a file and attempt commit. All 4 check scripts should run and pass.

#### Step 6.3.3: CI verification

Push to feature branch, create PR to main. Verify:
- All 3 quality-gate jobs pass
- Labels auto-applied
- Branch protection requires CI pass before merge

#### Step 6.3.4: Merge workflow verification

After CI passes, merge the PR. Verify:
- Branch auto-deleted after merge
- Main branch has all changes
