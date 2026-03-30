# Pre-Production Audit Index

Date: 2026-03-30
Auditor: Codex
Scope: full read-only hygiene and architecture audit using `.claude/autoload/_state.md`, `.claude/logs/state-archive.md`, dated plans/specs where helpful, current source, current git status, `flutter analyze`, and `flutter test`.

This index and the layer reports were expanded with a second scoped verification pass focused on tightening evidence, separating stale drift from unfinished recent work, and adding missing coverage/tooling findings.

## Historical Context Used

Recent sessions show the current app shape is the result of several large refactors landing in quick succession:

- Sessions 675-677: Forms Infrastructure, UI Refactor V2, Clean Architecture refactor, and Pre-Release Hardening landed across hundreds of files.
- Session 678: prior deep codebase audit generated a 22-phase cleanup plan.
- Session 680: config and workflow changes only, no codebase cleanup pass executed yet.

That history matters for classification:

- `stale drift`: older code paths left behind after the recent refactors.
- `unfinished recent work`: newly introduced paths that are clearly mid-integration.

## Verification Snapshot

- `flutter analyze`: failed on 2026-03-30 with `383 issues`.
- `flutter test`: passed on 2026-03-30 on the current working tree.
- Current git working tree at audit time: `144` changed paths.
  - `105` modified
  - `1` deleted
  - `38` untracked

## Quantitative Signals

- Direct `Supabase.instance.client` usages in `lib/`: `19`
- Direct `DatabaseService()` usages in `lib/`: `6`
- Silent `catch (_) / catch(_)` blocks in `lib/`: `32`
- Explicit `TODO:` markers in `lib/`: `4`
- Async `BuildContext` warnings in current analyzer output: `6`
- Deprecated theme-token usages in current analyzer output: `135`
- Unused/unnecessary-import-or-member issues in current analyzer output: `39`

## Report Set

- `2026-03-30-preprod-audit-wiring-routing-codex-review.md`
- `2026-03-30-preprod-audit-data-sync-codex-review.md`
- `2026-03-30-preprod-audit-providers-state-codex-review.md`
- `2026-03-30-preprod-audit-services-integrations-codex-review.md`
- `2026-03-30-preprod-audit-features-business-logic-codex-review.md`
- `2026-03-30-preprod-audit-screens-navigation-codex-review.md`
- `2026-03-30-preprod-audit-shared-ui-hygiene-codex-review.md`
- `2026-03-30-preprod-audit-tests-tooling-codex-review.md`

## Cross-Layer Themes

1. The recent clean-architecture and DI refactors changed file layout faster than they reduced real coupling. Several old global/singleton patterns still exist under the new structure.
2. Form generalization is only partially complete. Registry-based code exists, but 0582B assumptions still leak through schema, providers, screens, and PDF/export paths.
3. Test health and runtime health have diverged. The suite is green, but analyzer debt, stale code paths, and coverage gaps remain material for pre-production readiness.
4. The codebase is currently too dirty to treat git status alone as a source of truth for dead code. Findings below distinguish recent unfinished work from older stale drift where possible.
