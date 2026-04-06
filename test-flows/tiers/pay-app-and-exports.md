# Supplemental Tier: Pay App & Export Verification (P01-P06)

> Pay-application export, exported-history, contractor comparison, and saved-artifact sync/delete coverage.

| ID | Flow | Table(s) / Storage | Driver Steps | Verify-Logs | Notes |
|----|------|---------------------|--------------|-------------|-------|
| P01 | Exported History Visibility | `export_artifacts`, `pay_applications` | export pay app from Quantities → open Forms → confirm `Exported History` shows pay app row → tap row → wait(pay_app_detail_screen) | db, nav | Saved responses remain separate from exported history |
| P02 | Same-Range Replace Preserves Number | `export_artifacts`, `pay_applications` | export range A → export same range A again → confirm replace → keep suggested number → open detail | db | Verify saved pay-app number is unchanged |
| P03 | Overlap Block | `pay_applications` | export range A → attempt overlapping non-identical range B → confirm export flow blocks continuation | nav | No new saved pay-app row should be created |
| P04 | Pay App Delete Propagation | `pay_applications`, `export_artifacts`, file storage | open pay-app detail → delete → confirm → verify history row removed and file reference cleared | db, storage | Parent and child rows plus file references must disappear |
| P05 | Contractor Comparison + Discrepancy PDF | `export_artifacts` | open saved pay app → compare contractor pay app → import `.xlsx`/`.csv`/best-effort `.pdf` → review cleanup → export discrepancy PDF | pdf, db | Imported contractor file is ephemeral; only PDF artifact persists |
| P06 | Saved Pay App Artifact Sync/Delete Verification | `export_artifacts`, `pay_applications`, remote storage | sync after pay-app export → verify sender UI, sender SQLite, remote state, receiver SQLite, receiver UI → delete pay app → sync again → verify delete propagation | sync, db, storage | Pair with existing sync verification discipline |

## Required Assertions

- Exported history is filtered artifact history, not editable saved responses.
- Exact-range replace preserves logical identity and pay-app number unless explicitly overridden.
- Overlapping non-identical ranges never create a saved pay app.
- Deleting a saved pay app removes both rows and file references.
- Contractor comparison never mutates tracked project data in v1.
- Saved pay-app artifacts participate in normal export/storage sync and delete propagation.
