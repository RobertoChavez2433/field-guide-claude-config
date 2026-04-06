# Sync Verification Report — 2026-04-05 16:24

Platform: dual (android:4948 + windows:4949)

## Results
| Flow | Status | Notes |
|------|--------|-------|
| S01 | PASS | Project, assignments, locations, contractors, equipment, and bid item synced across both devices. |
| S02 | PASS | Daily entry synced and was queryable in Supabase. |
| S03 | FAIL | Photo reached Supabase, but the inspector report route got stuck on `Loading...` and logged `type 'Null' is not a subtype of type 'String' in type cast`. Issue: #206. |
| S04 | PASS_WITH_ERRORS | Form response `4ea459a2-6d2b-4e00-99c5-733465fbf853` synced to the inspector Forms screen, but inspector pull still emitted the known integrity failures from #204 and the expected dynamic form-row testing keys were not exposed. |
| S05 | PASS_WITH_ERRORS | Todo `76e7366e-6244-4723-bcfb-39f74a84fe4e` pushed to Supabase and appeared on the inspector Todos screen, but inspector sync still emitted the known integrity failures from #204. |
| S06 | PASS_WITH_ERRORS | Calculation history row `01dc88b7-3187-45ef-94ee-e64f61fe41f7` pushed to Supabase and appeared on the inspector Calculator screen, but inspector sync still emitted the known integrity failures from #204. |
| S07 | PASS_WITH_ERRORS | Spot-check update coverage passed for todo title mutation (`VRF-Check rebar spacing 4c6ho [done]`) on Supabase and inspector, but inspector sync still emitted the known integrity failures from #204. |
| S09 | PASS_WITH_ERRORS | Remote project delete cascaded correctly in Supabase and both devices removed the project, but the inspector never showed the expected deletion notification banner. Issue: #211. |
| S10 | PASS | The unassignment test project `57241ac2-95c2-435a-aeb9-cb68050da127` appeared on the inspector when assigned, disappeared after assignment removal, and was then remotely deleted for cleanup. |
| S11 | PASS_WITH_ERRORS | Document `85a4812d-cc96-486d-8554-3616044c4419` synced to Supabase with a non-null `remote_path` and matching storage object, but the inspector report route did not expose any document attachment UI; recorded as an observation per spec rather than a failure. |
| S12 | FAIL | Android resume logged `SyncLifecycleManager: App resumed, triggering quick sync`, but quick sync reported `no dirty scopes or tracker unavailable`, pulled `0` rows, and the resumed report stayed stale on `[auto2]` even though the peer had already synced `[auto3]`. Issue: #224. |
| S13 | FAIL | While the inspector stayed foregrounded on the shared entry report, an admin-side synced activities update did not appear automatically. The inspector remained stale until a manual sync was triggered. Issue: #212. |
| S15 | PASS | Both roles exposed the global app-bar full-sync affordance on Dashboard and Calendar, and both could also reach Sync Dashboard through Settings and run `sync_now_full_button` successfully. |
| S18 | FAIL | Private-channel verification is currently broken at the backend layer: realtime registration still fails in logs and `sync_hint_subscriptions` is not present in the active PostgREST schema cache. Covered by #205. |
| S19 | FAIL | After inspector sign-out/sign-in, the app rebounded auth context but immediately hit the same `register_sync_hint_channel` failure. A follow-up admin mutation to `[auto2]` still did not auto-appear on the inspector without manual sync. Covered by #205 and #212. |

## Bugs Found
- #198 ToS consent is requested again after signing back in.
- #199 Review Drafts screen has no way to delete a draft.
- #200 Dashboard Review Drafts action should use the same tile-card style as Start/Continue Entry.
- #201 Android soft keyboard frequently stays open and blocks action buttons.
- #202 Quantity picker search text is not cleared after selecting a quantity.
- #203 Quantities `+` button should open the quantity list directly.
- #204 Inspector full sync fails integrity verification and clears cursors after a successful sync cycle.
- #205 Realtime sync hint RPC registration fails because required Supabase functions are missing.
- #206 Inspector report can get stuck on Loading after sync and throws a Null-to-String cast error.
- #207 Dashboard empty-state View Projects button has poor text contrast.
- #208 Dashboard project header blue gradient feels visually out of place.
- #209 Forms list shows internal identifier/status instead of friendly form name.
- #210 Entry PDF preview shows mismapped values and fields in the wrong positions.
- #211 Inspector does not show deletion notification banner after synced project removal.
- #212 Foreground inspector does not auto-catch-up after admin sync.
- #224 Android resume quick sync does not catch up remote entry changes.

## Verified IDs
- projectId: `642909d6-7c0b-4d3a-bda1-084f915f705e`
- entryId: `4b4b6cc9-0747-47c1-8118-216caf5f6b62`
- photoId: `3c919290-97ac-4da3-aa02-37adb38f0eb8`
- formResponseId: `4ea459a2-6d2b-4e00-99c5-733465fbf853`
- todoId: `76e7366e-6244-4723-bcfb-39f74a84fe4e`
- calculationId: `01dc88b7-3187-45ef-94ee-e64f61fe41f7`
- project2Id: `57241ac2-95c2-435a-aeb9-cb68050da127`
- documentId: `85a4812d-cc96-486d-8554-3616044c4419`

## Screenshots
- `screenshots/inspector-report-after-photo-sync.png`
- `screenshots/inspector-forms-after-sync.png`
- `screenshots/inspector-todos-after-sync.png`
- `screenshots/inspector-calculator-after-sync.png`
- `screenshots/inspector-todo-updated-after-sync.png`
- `screenshots/android-current-screen.png`
- `screenshots/inspector-project-list-after-delete-sync.png`
- `screenshots/inspector-dashboard-after-project-delete.png`
- `screenshots/inspector-project2-visible.png`
- `screenshots/inspector-project2-removed.png`
- `screenshots/inspector-documents-after-sync.png`
- `screenshots/inspector-s13-after-admin-sync.png`
- `screenshots/inspector-s13-after-manual-sync.png`
- `screenshots/android-before-s12-rerun.png`
- `screenshots/android-after-s12-rerun.png`
- `screenshots/inspector-s19-before-admin-sync.png`
- `screenshots/inspector-s19-after-admin-sync-no-manual.png`

## Observations
- Bottom-nav taps to Settings are unreliable when the app is still inside a nested dashboard stack; backing out to the root state first makes route changes deterministic.
- On the inspector settings screen, a single sync tap is sufficient for log capture. The button disappears during sync and comes back after completion.
- The inspector sync failures are currently consistent and reproducible across photo, todo, and calculator pull verification.
- The inspector Forms screen visually rendered the synced `mdot_0582b` row, but the expected dynamic testing keys for saved responses were not exposed in the live widget tree during this run.
- The delete-cascade flow in the current app uses `delete_sheet_*` keys followed by `project_remote_delete_dialog_confirm`, which diverges from the older text-confirm flow written in the sync spec.
- Final VRF sweep showed both test projects present only as soft-deleted rows with non-null `deleted_at` timestamps.
- S11 document sync data-path verification passed through Supabase REST and storage, but the inspector report tree exposed only `report_attachments_section` plus `report_add_photo_button`; no document attachment keys were present on that route.
- S12 was verified on Android using real OS background/restore via `adb`: the lifecycle manager did run the resume quick-sync path, but because the tracker had no dirty scope it performed no pull and left the entry report stale.
- S15 clarified intended product behavior: the app-bar sync icon is supposed to run a full sync from anywhere. A temporary issue filed against that behavior was closed after product clarification.
- The inspector re-login path in S19 did not show the consent screen in this pass; logs loaded consent as `accepted=true` for the same user. The private-channel rebind still failed immediately afterward.
- S14 and S17 still require deeper background/OS control than the current cross-device harness provides. S16 is presently blocked by the broken hint/private-channel path captured in #205, #212, and #224.

