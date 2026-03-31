# Security Review — Cycle 1

**Verdict**: REJECT

## Findings

### [HIGH] Finding 1: `pull_request_target` trigger in labeler.yml enables fork-based code execution
**Location**: Phase 5, Sub-phase 5.3, Step 5.3.1
**Fix**: Change `on: pull_request_target` to `on: pull_request`

### [HIGH] Finding 2: quality-gate.yml missing `permissions:` block
**Location**: Phase 5, Sub-phase 5.2, Step 5.2.1
**Fix**: Add `permissions: contents: read, checks: write`

### [HIGH] Finding 3: Branch protection `enforce_admins: false` allows admin bypass
**Location**: Phase 6, Sub-phase 6.1, Step 6.1.1
**Fix**: Set `"enforce_admins": true`

### [HIGH] Finding 4: .env file written to CI runner with secrets, no cleanup
**Location**: Phase 5, Sub-phase 5.2, Step 5.2.1
**Fix**: Use `--dart-define` or add cleanup step. Since analyze/test don't need Supabase creds, consider removing entirely.

### [MEDIUM] Finding 5: Pre-commit hooks bypassable via --no-verify
**Location**: Phase 4, Sub-phase 4.3
**Fix**: Acceptable if Finding 3 is fixed (CI becomes the hard gate)

### [MEDIUM] Finding 6: Lint rule A1 allowlist uses path suffix matching
**Location**: Phase 3, Sub-phase 3.2, Step 3.2.1
**Fix**: Use full path matching from project root, not endsWith

### [MEDIUM] Finding 7: Redundant // ignore: comments alongside allowlist
**Location**: Phase 2, Sub-phases 2.2/2.3
**Fix**: Rely on allowlist, remove // ignore: comments

### [MEDIUM] Finding 8: sync-defects.yml script injection risk
**Location**: Phase 5, Sub-phase 5.4
**Fix**: Sanitize title, limit body length, add [auto-created] prefix

### [MEDIUM] Finding 9: stale-branches.yml missing release/hotfix branch protection
**Location**: Phase 5, Sub-phase 5.5
**Fix**: Add release/*, hotfix/* to skip list

### [LOW] Finding 10: Lint rule allowlists not centralized
**Fix**: Create shared allowlists.dart

### [LOW] Finding 11: grep-checks.ps1 heuristic matching can produce false negatives
**Fix**: Accept for pre-commit, ensure CI has more precise checks

### [LOW] Finding 12: push: branches: ['*'] triggers CI on all branches
**Fix**: Scope to specific branch patterns or add branches-ignore
