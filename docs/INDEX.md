# Documentation Index

**Restructured**: 2026-02-13
**Status**: Live docs organized by feature, guide, and rule context

---

## Organization Overview

The `.claude/docs/` folder is now organized into two main sections:

### 📁 `features/` - Feature Documentation (34 files)

Complete documentation for all 17 features. Each feature has:
- **`feature-{name}-overview.md`** - Quick reference (purpose, capabilities, data model, sync strategy)
- **`feature-{name}-architecture.md`** - Technical deep-dive (patterns, implementation details)

**Cross-cutting readers**: code-review-agent, qa-testing-agent, completeness-review-agent
**Implementation flow**: domain context comes from routing tables in `.claude/skills/implement/references/worker-rules.md` and `.claude/skills/implement/references/reviewer-rules.md`; feature docs are loaded as needed for deeper context

👉 See [features/README.md](features/README.md) for feature-to-rule mapping

### 📁 `guides/` - Implementation & Testing Guides (6 files)

How-to guides and references organized by type:

#### `guides/testing/` (2 files)
- **`manual-testing-checklist.md`** - 168-point QA coverage across all 12 feature suites
  - Used by: **qa-testing-agent**
  - Quick smoke test (5 min), full suite (45-60 min)
  - Regression triggers and test result template

- **`e2e-test-setup.md`** - Patrol E2E test configuration and troubleshooting
  - Used by: **qa-testing-agent**
  - Device setup, animation settings, permissions, CI/CD integration
  - Test flags, environment configuration, common issues

#### `guides/implementation/` (3 files)
- **`chunked-sync-usage.md`** - Large dataset sync with progress tracking
  - Used by: **implement workers touching sync/realtime code**
  - Configuration, progress callbacks, chunking strategy
  - For: Sync coordinator, large entry/photo datasets

- **`sync-architecture.md`** - Refactored sync architecture guide
  - Used by: **general-purpose**, **code-review-agent**, **qa-testing-agent**
  - Layer boundaries, handler ownership, status vs diagnostics split
  - For: SyncCoordinator, SyncEngine, SyncQueryService, verification model

- **`shared-analyzer-safe-patterns.md`** - Cross-cutting analyzer-safe abstractions
  - Used by: **implement workers and reviewers touching shared analyzer-safe code**
  - Documents `SafeRow`, hook-based `SafeAction`, and repository/copyWith decisions from analyzer-zero
  - For: Shared provider, repository, and SQLite row access patterns

#### `guides/` (root-level, 1 file)
- **`ui-prototyping-workflow.md`** - UI prototyping and mockup workflow
  - Used by: **implement workers doing UI prototyping**
  - Mockup conventions, iteration process, design-to-code handoff

👉 See [guides/README.md](guides/README.md) for guide-to-context mapping

---

### 📄 Root Docs — Audits & Reports (4 files)

Standalone audit and report documents at the `.claude/docs/` root:

- **`2026-03-28-ui-refactor-audit.md`** - UI refactor audit findings (2026-03-28)
- **`ios-build-guide.md`** - iOS build setup and signing guide
- **`pdf-pipeline-performance-audit.md`** - PDF pipeline performance audit findings
- **`workflow-insights-report.md`** - Workflow insights and process improvement report

---

## Agent Integration

### How Context Loads

The repo now uses **role-based agents** plus **domain routing tables**:

- Implementers and fixers load domain rules from `.claude/skills/implement/references/worker-rules.md`
- Reviewers load domain rules from `.claude/skills/implement/references/reviewer-rules.md`
- Feature docs, PRDs, and guides are read on demand when a task needs deeper context than the slim rule files provide

### Agent-to-Guide References

| Role | Guides |
|-------|--------|
| **qa-testing-agent** | Manual Testing Checklist, E2E Test Setup |
| **implement workers touching sync code** | Chunked Sync Usage |
| **code-review-agent** | Feature docs and implementation guides as needed |

---

## Key Improvements

✅ **Eliminated Clutter**: 31 docs in root → Organized into `features/` and `guides/`
✅ **Routing Table Integration**: Implement and review flows load slim rules first, then deeper docs as needed
✅ **Current Format**: Each guide header shows which agent(s) use it
✅ **Navigation**: Feature and guide READMEs provide clear mapping
✅ **Findability**: Agents can quickly locate relevant guidance

---

## Quick Navigation

- **Handling large data syncs?** → [Chunked Sync Usage](guides/implementation/chunked-sync-usage.md)
- **Looking for current sync architecture?** → [Sync Architecture Guide](guides/implementation/sync-architecture.md)
- **Looking for shared analyzer-safe abstractions?** → [Shared Analyzer-Safe Patterns](guides/implementation/shared-analyzer-safe-patterns.md)
- **Setting up E2E tests?** → [E2E Test Setup](guides/testing/e2e-test-setup.md)
- **Running QA coverage?** → [Manual Testing Checklist](guides/testing/manual-testing-checklist.md)

## File Statistics

| Section | Files | Purpose |
|---------|-------|---------|
| Features | 34 | Feature overviews & architecture |
| Testing Guides | 2 | Test setup & QA coverage |
| Implementation Guides | 3 | Feature-specific and cross-cutting implementation how-tos |
| UI Prototyping Guide | 1 | UI prototyping and mockup workflow |
| Root Audits & Reports | 4 | Audits, build guides, and reports |
| **Total** | **45** | Complete project documentation |

---

## Related Resources

- [PRDs](../prds/) - Product requirement documents (17 features)
- [Architecture Decisions](../architecture-decisions/) - Constraints per feature
- [Agents](../agents/) - Role-based agent definitions
- [Rules](../rules/) - Architecture & domain rules
