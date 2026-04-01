# Tailor Manifest

**Spec**: `.claude/specs/2026-03-30-wiring-routing-audit-fixes-spec.md`
**Review**: `.claude/code-reviews/2026-03-30-preprod-audit-layer-application-wiring-startup-routing-codex-review.md`
**Created**: 2026-03-31 20:15
**Files analyzed**: 14
**Patterns discovered**: 7
**Methods mapped**: 42
**Ground truth**: 48 verified, 0 flagged

## Contents
- [dependency-graph.md](dependency-graph.md) — Import chains, upstream/downstream deps
- [ground-truth.md](ground-truth.md) — Verified literals table
- [blast-radius.md](blast-radius.md) — Impact analysis + importers
- [patterns/](patterns/) — Architectural patterns with exemplars and methods
  - [deps-container.md](patterns/deps-container.md) — Feature Deps container pattern
  - [di-module.md](patterns/di-module.md) — DI module pattern (static initialize + providers)
  - [provider-composition.md](patterns/provider-composition.md) — Provider graph assembly
  - [entrypoint.md](patterns/entrypoint.md) — Entrypoint initialization pattern
  - [router-redirect.md](patterns/router-redirect.md) — Router redirect gate pattern
  - [consent-factory.md](patterns/consent-factory.md) — Consent/support factory pattern
  - [lifecycle-callback.md](patterns/lifecycle-callback.md) — Lifecycle callback wiring pattern
- [source-excerpts/](source-excerpts/) — Full source organized by file and by concern
  - [by-file.md](source-excerpts/by-file.md)
  - [by-concern.md](source-excerpts/by-concern.md)
