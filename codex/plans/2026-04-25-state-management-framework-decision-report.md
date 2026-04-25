# State Management Framework Decision Report — Field Guide App

Date: 2026-04-25
Author: Claude (Opus 4.7) — commissioned audit
Scope: Should the app migrate from `provider` + `ChangeNotifier` to Riverpod 3.x or `flutter_bloc` 9.x?
Status: Recommendation drafted. Decision pending.

---

## TL;DR

**Do not migrate. Continue and finish the in-flight Provider decomposition work.**

The codebase has real state-management pain — primarily concentrated in two god-object notifiers (`AuthProvider`, `ProjectProvider`) and a 297-call-site discipline problem around `notifyListeners()`. But the highest-friction integration point everyone migrates Provider apps to escape — the auto_route guard / `BuildContext`-less navigation problem — has already been **solved cleanly** in this codebase via `RouteAccessController` / `RouteAccessSnapshot`. And the team is already mid-flight on a documented refactor plan (`.codex/plans/2026-04-20-autoroute-routing-provider-refactor-todo-spec.md`) that explicitly chose to keep Provider and is producing the right kind of decomposition (extract `RolePolicy`, narrow notifiers, immutable snapshots, scheduler-mediated refreshes).

A migration today would:
- Cost an estimated 6–12 weeks of focused engineering for a usable end state, with a long tail of months to fully retire Provider.
- Force rewrites of 184 provider declarations, 522 consumption sites, and 60 `ChangeNotifier` classes across 91+ files.
- Invalidate 392 `pumpAndSettle`-style widget tests and the existing fake/test-helper ecosystem (`test/helpers/provider_wrapper.dart`).
- Conflict with an active routing/auth/driver migration that just stabilized — exactly the moment when introducing a second axis of churn is most dangerous.
- Deliver real ergonomic wins, but **none of those wins are unblocking** any feature, bug class, or production incident the audit surfaced.

The honest framing is: this is an *aesthetic and ergonomic* decision, not a *correctness or capability* one. Provider 6.1.5 is still officially maintained (no deprecation marker on pub.dev) and its known pain points are addressable in-place. The team has been doing exactly that.

**Reconsider the decision in 6–12 months** if (a) the current refactor plateaus without resolving the god-object problem, (b) Provider drops to single-digit-month maintenance cadence, or (c) a feature genuinely needs Riverpod 3.0's experimental offline persistence or mutation primitives — both of which are interesting for an offline-first app but currently labeled experimental.

---

## 1. What the audit found

I ran four parallel codebase audits (inventory, pain-points, auto_route integration, testing seams). Headline numbers verified by direct grep:

| Metric | Value | File:line evidence |
|---|---|---|
| Total Dart files in `lib/` | 1,776 | repo-wide |
| Feature directories | 20 | `lib/features/*/` |
| `ChangeNotifier` subclasses | **60** | direct grep across `lib/` |
| `notifyListeners()` call sites | **297** in 69 files | direct grep |
| `Provider`-package declarations | ~184 in 91 files | inventory audit |
| Provider consumption sites | 522 | `Consumer`, `context.read/watch/select`, `Selector` |
| `context.read` share of consumption | 67% (348/522) | imperative-heavy pattern |
| `context.watch` + `context.select` combined | 9% (46/522) | broad rebuilds dominate |
| `ProxyProvider` declarations | <10 | minimal cross-provider chaining |
| `MultiProvider` instances | Single root | `lib/core/di/app_providers.dart:43-194` |
| Notifiers overriding `dispose()` | ~7 of 60 | latent leak risk in others |
| Manual `addListener`/`removeListener` pairs | ~37 | tight coupling, lifecycle risk |
| `@visibleForTesting` markers in `lib/` | 50 across 25 files | mostly low-level services, not notifiers |
| Test files | 946 | `test/**/*.dart` + `integration_test/` |
| `pumpAndSettle` call sites | 392 in 92 test files | high — Riverpod/Bloc would reduce this |

### 1.1 The two god objects

These are by far the most consequential findings — both are well past the size where a single `notifyListeners()` call should be fanning out:

**`AuthProvider` — 838 LOC across 8 part files**
```
auth_provider.dart                            219
auth_provider_auth_actions.dart               130
auth_provider_company_profile_actions.dart    193
auth_provider_logging.dart                     30
auth_provider_recovery_actions.dart            98
auth_provider_runtime_coordinator.dart         89
auth_provider_security_actions.dart            50
auth_provider_state_reset.dart                 29
TOTAL                                         838
```

**`ProjectProvider` — 1,044 LOC across 7 part files**
```
project_provider.dart                         112
project_provider_auth_controller.dart         200
project_provider_auth_init.dart                71
project_provider_data_actions.dart            182
project_provider_filters.dart                 148
project_provider_mutations.dart               180
project_provider_selection.dart               151
TOTAL                                        1044
```

Both have been split via Dart `part` files — a coping strategy that fragments code organization without changing the underlying problem: every state mutation in any part file fans out to every listener of the unified notifier. This is the textbook case where Riverpod's "compose many small providers" model would shine. It is also addressable inside Provider by extracting independent `ChangeNotifier`s and exposing read-only aggregates — which is exactly what the in-flight plan started doing (`RolePolicy`, `RouteAccessController`, `ProfileRefreshScheduler`).

Other notable notifiers (200–360 LOC, all single-file): `AppLockProvider` (358), `AppConfigProvider` (299), `ConsentProvider` (295), `ProjectAnalyticsProvider` (295), `PhotoProvider` (262), `DailyEntryProvider` (243), `BidItemProvider` (239), `AdminProvider` (223), `SyncProvider` (217). None of these individually justify a framework migration; each is decomposable in place.

### 1.2 The discipline problem

The team has already independently identified `notifyListeners()` discipline as a structural risk: a custom lint rule lives at `fg_lint_packages/field_guide_lints/lib/sync_integrity/rules/no_state_reload_after_rpc.dart` that fails the build when an `.rpc()` call is followed by no `notifyListeners()` / `loadData()` / `refresh()`. This is a meaningful signal — the lint exists because developers were forgetting to notify, and the team chose to engineer around it rather than migrate.

This pattern — engineering around Provider's footguns — is sustainable up to a point. With 297 call sites and 60 notifiers, that point is approaching but not crossed.

### 1.3 What is not a problem

The audit was specifically tasked to find friction. Several places I expected pain, there isn't any:

- **auto_route + Provider integration is clean.** The repo solved the classic "guards can't access `BuildContext`" problem by making `RouteAccessController` a slim `ChangeNotifier` that exposes an immutable `RouteAccessSnapshot` and is injected into guards at construction. Auth, config, and consent state flow through it via three explicit `addListener` lines (`lib/core/router/route_access_controller.dart`). Tab shell, deep links, and hot restart are all clean. This is a load-bearing finding: **the most common reason teams cite for migrating large Provider apps does not apply here.**
- **The DI architecture is already sane.** Pure typed Dart composition (no `get_it` or `injectable`), feature DI files (`*_providers.dart`), tier-ordered root composition. Riverpod's DI sugar would be a smaller delta than I expected.
- **Testing posture is mature, not framework-bound.** Real fakes (`test/helpers/mocks/mock_repositories.dart` etc.), no `mockito`/`mocktail`, in-memory `sqflite_ffi` database, `TestingKeys` facade. The framework underneath is replaceable but the discipline is not — and that discipline is the actual asset.
- **No deep `ProxyProvider` chains.** Cross-provider dependencies are passed through constructors, not chained at the Provider level. Migration would not need to unwind a tower of `ProxyProvider`s.

---

## 2. Why this question is being asked at exactly the wrong moment

There is an active, recently-stabilized routing/auth migration in the repo:

- `.codex/plans/2026-04-20-autoroute-routing-provider-refactor-todo-spec.md` (active)
- `.codex/plans/2026-04-21-routing-auth-driver-decomposition-plan.md` (status: complete)
- `.codex/plans/2026-04-19-four-role-sync-hardening-scale-up-spec.md`

The 2026-04-20 spec includes this exact statement (Phase 2):

> "Keep `provider` and `ChangeNotifier`; do not add Riverpod, BLoC, GetX, or another state-management system."

And it has **already delivered** the key decomposition primitives a Riverpod migration would otherwise be the trigger for:

- `RouteAccessSnapshot` — immutable snapshot, no listener fan-out
- `RouteAccessController` — narrow notifier, three explicit sources
- `RolePolicy` — extracted from `AuthProvider`
- Attribution / company / user cache for stable identity reads
- `ProfileRefreshScheduler` — replaces ad-hoc `refreshUserProfile()` calls

This is the *content* of a state-management cleanup, just done inside Provider rather than on top of a new framework. The remaining open work in that plan (e.g., remove `isLoadingProfile` from route reevaluation) is exactly the kind of work that finishes the decomposition.

Layering a framework migration on top of an active routing/auth migration plus an active sync hardening effort would mean three concurrent foundational migrations. The routing red-screen / duplicate-GlobalKey class of bugs that motivated the AutoRoute lane (per `.codex/research/2026-04-19-router-red-screen-architecture-research.md`) is exactly the kind of failure that gets harder, not easier, to diagnose when the state layer is also churning.

---

## 3. The current state of the ecosystem (April 2026)

### 3.1 Provider 6.1.5 is maintained, not deprecated

- **pub.dev shows no discontinued/deprecated marker** ([provider on pub.dev](https://pub.dev/packages/provider)). Latest release 6.1.5+1, last published ~8 months ago. Flutter Favorite designation intact.
- The package's creator (Remi Rousselet) wrote Riverpod and recommends it for new projects, but neither his public communication nor the package metadata declares Provider end-of-life.
- Flutter docs still document Provider in the official simple-app-state-management guide ([flutter.dev](https://docs.flutter.dev/data-and-backend/state-mgmt/simple)).

What this means: Provider is in mature maintenance mode. No urgent deprecation pressure. Community sentiment in 2025–2026 articles consistently frames it as "legacy for new complex apps, fine for existing apps that work" ([Foresight Mobile 2026](https://foresightmobile.com/blog/best-flutter-state-management), [Flutter Studio comparison](https://flutterstudio.dev/blog/state-management-comparison-2026.html)).

### 3.2 Riverpod 3.0 (released 2025-09-10) is genuinely improved

The major-version bump shipped on 2025-09-10 ([riverpod.dev whats_new](https://riverpod.dev/docs/whats_new), [Code with Andrea Sept 2025 newsletter](https://codewithandrea.com/newsletter/september-2025/)). Notable for an offline-first construction app:

- **Experimental offline persistence** for `Notifier` providers (companion package `riverpod_sqflite`). For Field Guide App, which already runs SQLite-first, this could collapse some manual cache-then-sync glue. **Caveat: experimental.**
- **Experimental mutations** for form-submission-style side effects with native loading/error/success state. Field Guide has many forms that today reinvent this with `bool _isLoading + String? _error`.
- **Automatic retry with exponential backoff** for failed providers (200ms → 6.4s). Useful for sync-adjacent state.
- **`Ref.mounted`** post-async-gap, **pause/resume** when widgets are off-screen, **`ProviderContainer.test()`** for tests.
- **Breaking changes** include `valueOrNull` → `value`, `StateNotifierProvider` moved to `legacy.dart`, and `==`-based update filtering for streams. Not trivial, but bounded ([Riverpod 3 migration](https://riverpod.dev/docs/3.0_migration), [Zenn migration guide](https://zenn.dev/harx/articles/d8c49cdec0ab1d?locale=en), [Flutter Studio migration guide](https://flutterstudio.dev/blog/flutter-riverpod-3-complete-migration-guide.html)).

### 3.3 Bloc 9.x is mature and stable

- `flutter_bloc` 9.1.1 + `bloc` 9.2.0 are the current line ([bloclibrary.dev](https://bloclibrary.dev/)).
- Native event transformers (`restartable()`, `droppable()`, `concurrent()`) replace manual debouncing.
- `BlocSelector`, `buildWhen`/`listenWhen` for granular rebuilds.
- `hydrated_bloc` 11.x adds wasm support, persistent state across sessions.
- 2025–2026 sentiment positions Bloc as the *enterprise* default — preferred for regulated industries (finance, healthcare) where event-sourced audit trails are valuable ([Foresight Mobile](https://foresightmobile.com/blog/best-flutter-state-management), [Sharpskill](https://sharpskill.dev/en/blog/flutter/flutter-state-management-riverpod-vs-bloc)).

For Field Guide App's domain (construction inspectors, offline data capture, optional Supabase sync), Bloc's audit-trail strengths are not obviously load-bearing. The sync engine *internally* benefits from event-stream thinking, but it already has that — the friction (per the audit) is at the UI/notifier seam, not at the engine.

### 3.4 Migration costs are real and well-documented

Riverpod's own docs explicitly counsel patience:

> "Don't try to migrate all your providers at once! While you should strive toward moving all your application to Riverpod in the long-run, don't burn yourself out. Do it one provider at a time." ([Riverpod from-provider quickstart](https://riverpod.dev/docs/from_provider/quickstart))

Strategy: leaf providers first, then dependents, save `ProxyProvider`s for last. Both packages can run side-by-side during migration. LeanCode has published battle-tested playbooks from large-scale migrations at Virgin Money, Crédit Agricole Bank Polska, Sonova, NOS — credible third-party evidence that incremental migration of large codebases is viable but non-trivial.

For a codebase this size (60 notifiers, 522 consumption sites, 91 provider files), realistic effort estimates from comparable public migrations and from the structure of this code:

| Effort phase | Estimate (focused engineering) |
|---|---|
| Tooling, conventions, Riverpod 3 codegen wired in CI | 0.5–1 week |
| Migrate leaf providers (theme, weather, calendar format, etc., ~15 small notifiers) | 1–2 weeks |
| Migrate mid-tier feature providers (~25 notifiers) | 3–5 weeks |
| Decompose + migrate `AuthProvider` and `ProjectProvider` | 2–4 weeks |
| Migrate test harness, eliminate `pumpAndSettle` overuse, port 946 test files | 2–4 weeks (overlap) |
| Retire `provider` package, simplify DI | 0.5–1 week |
| **Total to a usable end state** | **~8–14 weeks of focused work** |
| **Total to fully retire `provider`** | **3–6 months elapsed (with feature work continuing)** |

This is the optimistic case where nothing blows up. Real costs are higher because of overlap with the active routing/auth/sync migrations.

---

## 4. Direct comparison for Field Guide App's specific situation

### 4.1 Stay on Provider, finish the in-flight decomposition (recommended)

**Pros**
- Zero migration cost. Engineering capacity stays on shipping features, hardening sync (active), and finishing AutoRoute (active).
- The painful decompositions are already underway and demonstrably working (`RouteAccessController` proves the pattern).
- Test suite, fake ecosystem, `TestingKeys`, driver contracts all stay valid.
- No second axis of churn during routing/sync stabilization.
- Provider remains officially maintained; no urgency.

**Cons**
- `notifyListeners()` discipline tax persists. The custom lint mitigates but doesn't eliminate the footgun. Each new feature adds risk.
- God-object notifiers won't dissolve on their own; they require explicit decomposition work.
- Async state patterns (`bool _isLoading + String? _error`) stay ad-hoc unless a shared `AsyncValue`-equivalent is introduced (which is doable as a small shared utility).
- Some testing verbosity (`pumpAndSettle` instead of stream-aware assertions) persists.

**Required follow-through to make this responsible**
1. Finish the open Phase 2 items in `.codex/plans/2026-04-20-autoroute-routing-provider-refactor-todo-spec.md`.
2. Add a concrete plan to decompose `AuthProvider` and `ProjectProvider` further (`AuthProvider` already started with `RolePolicy`; do the same for company-profile, recovery, security actions).
3. Introduce a lightweight `AsyncState<T>` (sealed: `Idle | Loading | Data(T) | Error(e, st)`) in `lib/shared/`, and migrate notifiers opportunistically as they're touched. No big-bang.
4. Add a lint or mixin that nudges new `ChangeNotifier`s toward `dispose()` overrides if they hold streams/timers (extend the existing `field_guide_lints` package).
5. Set a 6-month review trigger to revisit this decision against the criteria in §6.

### 4.2 Migrate to Riverpod 3.x

**Pros**
- Compile-time-safe DI; no `BuildContext`-shape errors.
- Composable providers replace god-objects naturally — the AuthProvider/ProjectProvider problem dissolves rather than being managed.
- `AsyncValue` first-class; eliminates the ad-hoc loading/error pattern across 60 notifiers.
- `ref.listen` and `ref.watch` replace 37+ manual `addListener`/`removeListener` pairs.
- `ref.mounted`, `ProviderContainer.test()`, `overrideWithBuild` make test setup substantially cleaner.
- Created by Provider's author; well-maintained, growing ecosystem.
- Riverpod 3's experimental offline persistence + mutations align with this app's offline-first model — *if* you accept experimental APIs.

**Cons**
- 8–14 weeks of focused engineering (likely longer in practice given concurrent migrations).
- Forces a third concurrent foundational migration on top of routing + sync hardening.
- Riverpod 3's lifecycle changes are subtle ("code that previously worked suddenly stops" — [Zenn migration guide](https://zenn.dev/harx/articles/d8c49cdec0ab1d?locale=en)). Bug surface during migration is real.
- Some Riverpod 3 features you'd most want (offline persistence, mutations) are explicitly experimental.
- `RouteAccessController` would need to be re-expressed as a Riverpod provider; auto_route guard integration is solved but in a different shape.
- Driver contracts (`lib/core/driver/`) and `TestingKeys` would need a sweep to align with the new state model.

### 4.3 Migrate to Bloc 9.x

**Pros**
- Maximum determinism: events → states with first-class testing (`bloc_test`, `blocTest()`), audit-trail clarity.
- Native concurrency primitives (`droppable`, `restartable`, `concurrent`) align well with sync-coordination semantics.
- Strong fit for compliance-heavy domains.

**Cons**
- Heaviest migration of the three: every notifier becomes an event hierarchy + state hierarchy + Bloc class. Realistic effort 12–20+ weeks.
- Adds boilerplate that the codebase doesn't currently have. The audit shows imperative `context.read` is dominant (67%) — that's a Bloc-resistant pattern.
- For a construction-inspector app (not finance/healthcare), the audit-trail benefit is overkill.
- Auto_route integration is awkward (no `BuildContext` in guards; you'd inject the Bloc via constructor — workable, but no more elegant than today's `RouteAccessController`).

Bloc is the right tool for a different problem domain. Not this one.

---

## 5. Final recommendation

**Do not migrate. Finish the Provider decomposition that's already in flight.**

The case for migration would be strongest if any of these were true, and none are:

- ❌ Provider is end-of-life or unsupported. *(It's not; 6.1.5+1 actively maintained.)*
- ❌ A specific feature is blocked by Provider's limitations. *(None surfaced in the audit.)*
- ❌ The auto_route + Provider seam is unworkable. *(`RouteAccessController` proves it works.)*
- ❌ Production incidents trace back to Provider mechanics. *(Lints catch the main footgun; no incident-to-Provider chain in the audit.)*
- ❌ The team has spare capacity and no concurrent foundational migrations. *(Two concurrent migrations are active.)*

The case *for* concentrated, in-place Provider hardening is strong because:

- ✅ The decomposition primitives already shipped (`RouteAccessController`, `RolePolicy`, `ProfileRefreshScheduler`) prove the pattern works.
- ✅ A small, targeted set of follow-ups (`AuthProvider` further extraction, `AsyncState<T>` utility, `dispose()` lint) would address the audit's biggest pains at maybe 1/4 the cost of a framework migration.
- ✅ No production work is blocked. The team gets to keep shipping features.
- ✅ A 6–12 month review window preserves optionality if the ecosystem (or the codebase) shifts.

**Concrete next steps if this recommendation is accepted:**

1. Add a checklist to `.codex/plans/2026-04-20-autoroute-routing-provider-refactor-todo-spec.md` (or open a sibling spec) for the remaining Phase 2 / decomposition follow-ups: `AuthProvider` further extraction, `AsyncState<T>`, `dispose()` lint nudge.
2. Define a measurable end goal: cap any single `ChangeNotifier` at ~250 LOC; require shared `AsyncState<T>` for any new notifier; reduce `addListener`/`removeListener` pairs by 50% via narrower notifiers + read-only snapshots.
3. Schedule a 6-month review (October 2026) against the trigger criteria in §6.
4. Update CLAUDE.md only if needed — current rule already encodes the recommendation.

---

## 6. When to revisit

Revisit the migration decision in 6–12 months if any of the following are observed:

| Trigger | What it means |
|---|---|
| `notifyListeners()` discipline causes a P1 incident or repeated regressions despite the lint | The custom-lint mitigation is no longer sufficient. Migration begins to pay for itself. |
| `AuthProvider` / `ProjectProvider` decomposition stalls or grows past current size despite explicit work | In-place fix isn't converging. Framework migration is the bigger hammer. |
| Provider's pub.dev cadence drops below one release per 12 months, or a Flutter SDK release breaks Provider compatibility | Maintenance signal flips. Move before forced. |
| A feature genuinely needs Riverpod 3.0 mutations or offline persistence and those exit experimental status | Concrete capability gap, not aesthetic preference. |
| The team grows substantially and onboarding new engineers onto the manual `notifyListeners` model becomes an observable drag | Team-cost calculus shifts. |
| The active routing + sync migrations both fully ship and stabilize, *and* the app enters a calm period | Capacity is available without compounding migration risk. |

If none of these trigger, the recommendation is to stay.

---

## 7. Sources

- [provider on pub.dev (6.1.5+1)](https://pub.dev/packages/provider)
- [Riverpod 3 — What's New](https://riverpod.dev/docs/whats_new)
- [Riverpod 3 — Migrating from 2.0 to 3.0](https://riverpod.dev/docs/3.0_migration)
- [Riverpod — Migrating from `provider` quickstart](https://riverpod.dev/docs/from_provider/quickstart)
- [flutter_riverpod changelog (pub.dev)](https://pub.dev/packages/flutter_riverpod/changelog)
- [BLoC library home (flutter_bloc 9.1.1, bloc 9.2.0)](https://bloclibrary.dev/)
- [hydrated_bloc on pub.dev](https://pub.dev/packages/hydrated_bloc)
- [Code with Andrea — September 2025 Newsletter (Riverpod 3.0)](https://codewithandrea.com/newsletter/september-2025/)
- [Foresight Mobile — Best Flutter State Management Libraries 2026](https://foresightmobile.com/blog/best-flutter-state-management)
- [Flutter Studio — State Management Comparison 2026](https://flutterstudio.dev/blog/state-management-comparison-2026.html)
- [Flutter Studio — Riverpod 3 Migration Guide](https://flutterstudio.dev/blog/flutter-riverpod-3-complete-migration-guide.html)
- [Sharpskill — Riverpod vs BLoC 2026](https://sharpskill.dev/en/blog/flutter/flutter-state-management-riverpod-vs-bloc)
- [Zenn — Migration Guide to Riverpod 3](https://zenn.dev/harx/articles/d8c49cdec0ab1d?locale=en)
- [Dasroot — Flutter State Management: Riverpod, Bloc, and Provider Compared (Mar 2026)](https://dasroot.net/posts/2026/03/flutter-state-management-riverpod-bloc-provider-compared/)
- [Flutter docs — Simple App State Management](https://docs.flutter.dev/data-and-backend/state-mgmt/simple)
- [Medium — "Stop Using These Flutter Packages in 2026"](https://medium.com/@gurlekyunusemre2/stop-using-these-flutter-packages-in-2026-579b2e4c9d12)
- [auto_route on pub.dev](https://pub.dev/packages/auto_route)
- [Medium — Auto Route Guards with Riverpod (2026)](https://medium.com/@alaxhenry0121/stop-wrestling-with-flutter-navigation-how-riverpod-auto-route-will-save-your-sanity-e03daae15d9d)

---

## Appendix A — Codebase audit raw findings

Four parallel agents ran. Summaries:

**Inventory audit:** 60 ChangeNotifiers, 184 provider declarations across 91 files, 522 consumption sites (67% imperative `read`), single root MultiProvider with ~100+ entries, pure-Dart typed DI. AuthProvider 838 LOC, ProjectProvider 1,044 LOC.

**Pain-points audit:** Manual `notifyListeners()` is the dominant structural debt (297 call sites; team built a custom lint). 22+ notifiers without `dispose()` override. 37+ manual `addListener`/`removeListener` pairs. God objects above. Async state ad-hoc across all sampled notifiers. Sync coordination layer is well-bounded (separate domain service + provider wrapper). No load-bearing TODOs.

**Auto_route + Provider audit:** Single `RootStackRouter` with one tab shell; no nested routers. `RouteAccessController` solves the no-`BuildContext`-in-guards problem cleanly via interface-based injection. Per-screen scope wrappers (`FormViewerControllerScope` etc.), not deep MultiProvider nesting. Tab shell, deep links, hot restart, route observers all clean. Verdict: not a friction point.

**Testing audit:** 946 test files. Real-fake philosophy with mature mock repository / mock provider ecosystem (no mockito/mocktail). 392 `pumpAndSettle` sites — verbose but functional. 50 `@visibleForTesting` markers, mostly in services not notifiers. `TestingKeys` facade actively used. Provider testability rated 6.5/10 by the auditor. Estimated migration effect: Riverpod +1.5 to +2.0; Bloc +1.0.

## Appendix B — Existing Provider-decomposition work (already shipped)

From `.codex/plans/2026-04-20-autoroute-routing-provider-refactor-todo-spec.md` Phase 2 (selected delivered items):

- ✅ Add immutable `RouteAccessSnapshot`.
- ✅ Add `RouteAccessController` as the narrow route-reevaluation notifier.
- ✅ Make route guards read only `RouteAccessSnapshot`, not broad presentation providers.
- ✅ Extract role and permission logic from `AuthProvider` into `RolePolicy`.
- ✅ Add an attribution/company/user cache for stable route and sync identity reads.
- ✅ Add `ProfileRefreshScheduler`.
- ⏳ Remove `isLoadingProfile` from route reevaluation unless part of first auth bootstrap decision.
- ⏳ Move screen-mounted `refreshUserProfile()` calls behind the scheduler.

This is the substantive content of a state-management cleanup. The recommendation is to keep doing it.

