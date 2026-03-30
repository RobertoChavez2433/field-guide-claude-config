# Codebase Cleanup Plan Review — 2026-03-30

## Code Review: REJECT → APPROVED (after fixes)

### Blocking Issues (FIXED inline in plan)
1. **ScopeType.viaUser doesn't exist** (Phase 13) — Fixed: use `ScopeType.direct` + `pullFilter()` override
2. **getCountByProject missing from domain interface** (Phase 16) — Fixed: added PREREQUISITE note
3. **FutureBuilder-in-router anti-pattern** (Phase 14.1) — Fixed: moved resolution to screen initState

### High Issues (FIXED inline in plan)
4. **AuthProvider constructor change call-sites** (Phase 11.4) — Fixed: explicit call-site list added
5. **ProjectLifecycleService constructor change** (Phase 11.4) — Fixed: explicit app_initializer line noted
6. **FCM rate limiting** (Phase 22.5) — Fixed: 60s debounce added

### Medium Issues (noted for implementers)
- Phase 1.1: `AppDependencies.copyWith` needs CoreDeps propagation
- Phase 16.1: `FilterEntriesUseCase` is YAGNI pass-through — consider calling repo directly
- Phase 8.1/8.2: Verify `Project.copyWith` includes all needed fields
- Phase 10: Design system migration lacks exact line numbers for screens 2-5

## Security Review: APPROVED WITH CONDITIONS (conditions met)

### All conditions addressed:
1. ScopeType.viaUser → `ScopeType.direct` + `pullFilter()` override
2. FCM debounce → 60s throttle with `_lastFcmSyncTrigger`
3. Consent records → `insertOnly => true` client-side enforcement added

### Advisory findings (non-blocking):
- `adapter.validate()` is a no-op — document limitation
- Support bundle PII — verify `support-logs` bucket RLS
- Document path traversal — OS-mitigated, low risk
