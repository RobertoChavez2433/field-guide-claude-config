---
description: "Audit the .claude/ directory against the current codebase. Validates file paths, class references, and security invariants."
---

# Audit Config

## Overview

One-command health check of the `.claude/` configuration directory against the current codebase. Finds broken file paths, stale class references, orphaned config files, and missing coverage.

## Checklist

1. Index codebase with CodeMunch (or use existing recent index)
2. Scan all `.claude/` files for file path references
3. Validate each reference against disk
4. Check class/model names against codebase definitions
5. Verify security invariants
6. Produce structured report
7. Present findings to user with recommended fixes

## Process

### Step 1: Index Codebase

```
mcp__jcodemunch__index_folder(path: ".", use_ai_summaries: false, max_files: 2000)
```

Fallback: Use Glob + Grep + Read if CodeMunch unavailable.

### Step 2: Scan References

For each `.claude/` file in scope:
- `docs/features/` (26 files + README)
- `prds/` (14 files)
- `agents/` (13 files: 10 definitions + 3 memory files)
- `agent-memory/` (10 files across 8 dirs)
- `architecture-decisions/` (15 files)
- `rules/` (9-11 files)
- `state/` (17 files)
- `skills/` (9+ SKILL.md files)
- `CLAUDE.md`
- `docs/` root and guides (~12 files)
- `hooks/` (2 files)
- `autoload/_state.md`
- `memory/MEMORY.md`

Extract file path patterns: `lib/`, `.dart`, `lib/features/`, `lib/core/`
Extract class name patterns: PascalCase words that look like Dart classes

### Step 3: Validate

For each reference:
- File paths: Check if file exists on disk using Glob
- Class names: Check if class exists in CodeMunch index using search_symbols

### Step 4: Security Invariant Check

Verify:
- [ ] All agent files have expected `tools`/`disallowedTools` fields
- [ ] security-agent has `disallowedTools: Write, Edit, Bash`
- [ ] security-agent body contains Iron Law ("NEVER MODIFY CODE. REPORT ONLY.")
- [ ] Constraint files contain `MUST`/`MUST NOT` rules (count >= expected)
- [ ] CLAUDE.md contains string "Security is non-negotiable" (grep, not line number)
- [ ] Rule files contain security directive sentinel strings (token storage, RLS patterns)
- [ ] Blocker entries in `_state.md` reference GitHub Issue numbers

### Step 5: Report

Save to `.claude/outputs/audit-report-YYYY-MM-DD.md`:

```markdown
# .claude/ Audit Report -- YYYY-MM-DD

**Branch**: [current branch]
**Commit**: [commit hash]
**Scanned**: [N] .claude/ files against [N] codebase files

## Summary
- Broken paths: [N]
- Stale references: [N]
- Orphaned config files: [N]
- Missing coverage: [N]
- Security invariants: [PASS/FAIL]

## Broken Paths
[Per-file list with line numbers]

## Stale References
[Class/model names that don't exist]

## Orphaned Config
[.claude/ files with no matching codebase feature]

## Missing Coverage
[Codebase features/files with no .claude/ docs]

## Security Invariants
[Pass/fail for each check]
```

### Step 6: Present to User

Display summary and ask if user wants to:
- A) Fix automatically (invoke brainstorming for significant changes)
- B) Fix manually
- C) Defer to next session

## Scope Exclusions

These directories are NOT scanned:
- `logs/` (historical archives)
- `adversarial_reviews/` (historical reviews)
- `code-reviews/` (historical reviews)
- `test-results/` (historical test data)
- `backlogged-plans/` (future-looking)
- `plans/sections/` (in-progress plan work)

## Security Invariants (Immutable)

This skill NEVER modifies files. It is read-only and report-only.
