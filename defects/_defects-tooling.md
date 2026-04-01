# Defects: Tooling & Process

## Active Patterns

### [CONFIG] 2026-04-01: Destructive git checkout on uncommitted work
**Pattern**: `git checkout -- <dir>` used to "revert" a few damaged files, but wiped ALL unstaged changes in those directories — including days of unrelated work from sessions 697-698 (~90+ files).
**Prevention**: NEVER use `git checkout --`, `git restore`, `git reset --hard`, or `git clean` on directories with uncommitted work. Use `git stash` first if you must revert. Better: only revert the SPECIFIC damaged files by name, not entire directories.
**Ref**: Session 699. Root cause: PowerShell `Set-Content -NoNewline` collapsed file newlines, then `git checkout -- lib/ test/ integration_test/` destroyed everything.

### [CONFIG] 2026-04-01: PowerShell Set-Content destroys file formatting
**Pattern**: `Set-Content -NoNewline` combined with regex replacement strips all newlines from files, collapsing multi-line Dart files into single lines (24k+ analyze errors).
**Prevention**: NEVER use PowerShell `Set-Content` for mass file edits. Use Python with explicit line-by-line processing and preserved line endings. Test on 1 file first before batch operations.
**Ref**: Session 699. 468 files corrupted before git checkout compounded the damage.

### [CONFIG] 2026-04-01: Uncommitted work across sessions
**Pattern**: Sessions 681-698 accumulated changes without committing. When disaster struck, 18 sessions of work were at risk with no safety net.
**Prevention**: Commit at the end of every session, even as WIP on a feature branch. `git add -A && git commit -m "WIP: session N"` takes 5 seconds and creates a recovery point.
**Ref**: Session 699. Only reason partial recovery was possible was a dangling stash commit from an earlier auto-stash.
