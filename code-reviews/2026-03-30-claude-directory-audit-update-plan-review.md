# Claude Directory Audit & Update — Plan Review

**Date**: 2026-03-30
**Verdict**: APPROVE (after fixing 2 CRITICAL issues inline)

## CRITICAL (Fixed)
1. Wrong constraint file paths in Part 3 Phase 9 — all used `.claude/` root instead of `.claude/architecture-decisions/`. Fixed all 15 occurrences.
2. Same issue for CREATE operations (forms-constraints.md, consent-telemetry-constraints.md). Fixed.

## HIGH
1. Testing keys count imprecise (13→16 vs actual 15-16 depending on barrel inclusion). Note for implementation: verify actual count.
2. Schema file count says 14, actual is 16 (including barrel). Note for implementation.
3. `data-validation-rules.md` path was wrong (same root-path issue). Fixed.
4. `locations-prd.md` not mentioned in PRD updates. Reviewed, no changes needed.
5. Part 1 verification grep less thorough than Part 3. Recommend single final verification in Part 3 only.

## MEDIUM
1. 17 defect files on disk vs 16 stated (includes `_deferred-sv3-sv6-context.md`)
2. Existing 13 feature-*.json files not checked for stale content
3. 5 of 8 agent-memory directories not checked (assumed clean by audit)
4. 4 rules files not addressed (platform-standards, supabase-sql, ui-prototyping, patrol-testing — audited clean)
5. Part 2 Dispatch Group 3 proposes 13 parallel agents — consider batching

## Security Review (Separate Agent)
**Verdict**: APPROVE with 1 HIGH (same path issue, fixed) + 4 MEDIUM

### Security MEDIUMs (All addressed inline in plan):
- M1: consent-telemetry-constraints.md expanded with breadcrumb scrubbing, log upload PII filtering, consent record integrity, retention policy
- M2: auth-constraints.md expanded with company_id JWT rule, server-side admin validation, company switch session refresh
- M3: sync-constraints.md expanded with company_id trust boundary rule
- M4: security-agent RLS table list noted for update (Phase 4.10)
