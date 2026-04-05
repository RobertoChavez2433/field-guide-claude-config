# Documentation Index

**Restructured**: 2026-02-13
**Status**: All docs organized, current, and referenced by agents

---

## Organization Overview

The `.claude/docs/` folder is now organized into two main sections:

### 📁 `features/` - Feature Documentation (34 files)

Complete documentation for all 17 features. Each feature has:
- **`feature-{name}-overview.md`** - Quick reference (purpose, capabilities, data model, sync strategy)
- **`feature-{name}-architecture.md`** - Technical deep-dive (patterns, implementation details)

**Agents that load feature docs**: code-review-agent, qa-testing-agent (cross-cutting)
**Agents that load specific features**: Based on their specialization (frontend, backend-data, backend-supabase, auth, pdf agents)

👉 See [features/README.md](features/README.md) for feature-to-agent mapping

### 📁 `guides/` - Implementation & Testing Guides (5 files)

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

#### `guides/implementation/` (2 files)
- **`chunked-sync-usage.md`** - Large dataset sync with progress tracking
  - Used by: **backend-supabase-agent**
  - Configuration, progress callbacks, chunking strategy
  - For: Sync orchestrator, large entry/photo datasets

- **`shared-analyzer-safe-patterns.md`** - Cross-cutting analyzer-safe abstractions
  - Used by: **general-purpose**, **frontend-flutter-specialist-agent**, **backend-data-layer-agent**
  - Documents `SafeRow`, hook-based `SafeAction`, and repository/copyWith decisions from analyzer-zero
  - For: Shared provider, repository, and SQLite row access patterns

#### `guides/` (root-level, 1 file)
- **`ui-prototyping-workflow.md`** - UI prototyping and mockup workflow
  - Used by: **frontend-flutter-specialist-agent**
  - Mockup conventions, iteration process, design-to-code handoff

👉 See [guides/README.md](guides/README.md) for guide-to-agent mapping

---

### 📄 Root Docs — Audits & Reports (4 files)

Standalone audit and report documents at the `.claude/docs/` root:

- **`2026-03-28-ui-refactor-audit.md`** - UI refactor audit findings (2026-03-28)
- **`ios-build-guide.md`** - iOS build setup and signing guide
- **`pdf-pipeline-performance-audit.md`** - PDF pipeline performance audit findings
- **`workflow-insights-report.md`** - Workflow insights and process improvement report

---

## Agent Integration

### How Agents Load Docs

Each agent has **frontmatter** that declares what docs it needs:

```yaml
specialization:
  shared_rules:       # Architecture & constraint files
    - architecture.md
  guides:             # Implementation guides (NEW)
    - docs/guides/implementation/feature-guide.md
  state_files:        # Current state files
    - PROJECT-STATE.json
  prd: prds/...       # Product requirements (if applicable)
```

### Agent-to-Guide References

| Agent | Guides |
|-------|--------|
| **qa-testing-agent** | Manual Testing Checklist, E2E Test Setup |
| **backend-supabase-agent** | Chunked Sync Usage |
| **code-review-agent** | All feature docs (read-only) |

---

## Key Improvements

✅ **Eliminated Clutter**: 31 docs in root → Organized into `features/` and `guides/`
✅ **Agent Integration**: All guides now referenced in agent frontmatter
✅ **Current Format**: Each guide header shows which agent(s) use it
✅ **Navigation**: Feature and guide READMEs provide clear mapping
✅ **Findability**: Agents can quickly locate relevant guidance

---

## Quick Navigation

- **Handling large data syncs?** → [Chunked Sync Usage](guides/implementation/chunked-sync-usage.md)
- **Looking for shared analyzer-safe abstractions?** → [Shared Analyzer-Safe Patterns](guides/implementation/shared-analyzer-safe-patterns.md)
- **Setting up E2E tests?** → [E2E Test Setup](guides/testing/e2e-test-setup.md)
- **Running QA coverage?** → [Manual Testing Checklist](guides/testing/manual-testing-checklist.md)

## File Statistics

| Section | Files | Purpose |
|---------|-------|---------|
| Features | 34 | Feature overviews & architecture |
| Testing Guides | 2 | Test setup & QA coverage |
| Implementation Guides | 2 | Feature-specific and cross-cutting implementation how-tos |
| UI Prototyping Guide | 1 | UI prototyping and mockup workflow |
| Root Audits & Reports | 4 | Audits, build guides, and reports |
| **Total** | **44** | Complete project documentation |

---

## Related Resources

- [PRDs](../prds/) - Product requirement documents (17 features)
- [Architecture Decisions](../architecture-decisions/) - Constraints per feature
- [Agents](../agents/) - Agent definitions with frontmatter
- [Rules](../rules/) - Architecture & domain rules
