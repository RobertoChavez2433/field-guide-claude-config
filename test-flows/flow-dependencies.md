# Flow Dependencies & Execution Order

> Reference for `/test full` and `--resume` — shows tier ordering, flow dependencies, and total counts.

## Dependency Chain (Execution Order)

```
T01 (Login Admin)
 ├── T02 (Navigate Tabs)
 ├── T03 (Sign Out) — run last in auth tier
 ├── T05 (Create Project)
 │    ├── T06 (Add Location A)
 │    │    └── T15 (Create Entry)
 │    │         ├── T16 (Safety Fields)
 │    │         ├── T17 (Add Contractor to Entry) → T18 (Personnel) → T19 (Equipment Usage)
 │    │         ├── T20 (Log Quantity) → T21 (Calculator)
 │    │         ├── T22 (Attach Photo) → T23 (Second Photo)
 │    │         ├── T24 (Edit Location) → T25 (Edit Weather)
 │    │         ├── T62 (Edit Activities) → T63 (Edit Temp) → T64 (Edit Qty)
 │    │         ├── T41 (Export PDF) → T42 (Export Folder)
 │    │         └── T68 (Delete Photo)
 │    ├── T07 (Add Location B) → T71 (Delete Location B)
 │    ├── T08 (Prime Contractor) → T10 (Equipment) → T69 (Delete Equipment)
 │    ├── T09 (Sub Contractor) → T70 (Delete Contractor)
 │    ├── T11 (Pay Item 1) → T61 (Edit Pay Item)
 │    ├── T12 (Pay Item 2) → T72 (Delete Pay Item)
 │    ├── T13 (Assignment) → T66 (Remove Assignment)
 │    ├── T14 (Search)
 │    ├── T26 (Day 2 Entry) → T27 (Review) → T28 (Submit) → T29 (Undo) → T30 (Delete)
 │    ├── T31 (Todo) → T32 (Edit) → T33 (Complete) → T34 (Delete)
 │    ├── T35 (Form) → T36 (Fill) → T37 (Submit) → T43 (Export) → T74 (Delete)
 │    ├── T58 (Archive) → T65 (Unarchive)
 │    └── T59 (Edit Project)
 ├── T38 (Calculator HMA) → T39 (Calculator Concrete)
 ├── T40 (Gallery Browse)
 ├── T44-T49, T51-T52 (Settings flows; T50 removed — sync via dedicated sync verification flows)
 ├── T53-T58 (Admin flows)
 ├── T75 (Remove from Device)
 ├── T92-T96 (Navigation verification)
 └── T51 (Trash Restore) → T77 (Trash Delete Forever)

T04 (Login Inspector) — separate session
 ├── T85-T91 (Permission checks)
 ├── T87 (Inspector Create Entry)
 └── T88 (Inspector Create Todo)

S01 (Project Setup) — dual-device session (admin:4948, inspector:4949)
 ├── S02 (Daily Entry) → S03 (Photos) [COMPACTION]
 ├── S04 (Forms)
 ├── S05 (Todos)
 ├── S06 (Calculator) [COMPACTION]
 ├── S07 (Update All) → S08 (PDF Export) → S11 (Documents)
 ├── S12 (Quick Resume Catch-Up)
 ├── S13 (Foreground Realtime Hint)
 ├── S14 (Background FCM Hint Recovery) [MANUAL]
 ├── S15 (Global Full Sync Action + Role Visibility)
 ├── S16 (Dirty-Scope Project Isolation)
 ├── S17 (Maintenance Sync Housekeeping) [MANUAL]
 ├── S18 (Private Channel Registration)
 ├── S19 (Private Channel Teardown + Rebind)
 ├── S20 (Support Ticket Sync)
 ├── S21 (Consent Audit Sync)
 └── S09 (Delete Cascade) → S10 (Unassignment + Cleanup) [COMPACTION]
```

## Flow Count Summary

| Tier | Range | Count | Description |
|------|-------|-------|-------------|
| Tier 0 | T01-T04 | 4 | Auth & Smoke |
| Tier 1 | T05-T14 | 10 | Project Setup (Admin) |
| Tier 2 | T15-T23 | 9 | Daily Entry Creation |
| Tier 3 | T24-T30 | 7 | Entry Lifecycle |
| Tier 4 | T31-T40 | 10 | Toolbox |
| Tier 5 | T41-T43 | 3 | PDF & Export |
| Tier 6 | T44-T52 | 8 | Settings & Profile (T50 removed — replaced by sync verification coverage) |
| Tier 7 | T53-T58 | 6 | Admin Operations |
| Tier 8 | T59-T67 | 9 | Edit & Update Mutations |
| Tier 9 | T68-T77 | 10 | Delete Operations |
| Sync | S01-S21 | 21 | Sync Verification (Claude-driven, dual-device + SQLite/change_log/Supabase/storage proofs + sync-mode coverage) |
| Tier 11 | T85-T91 | 7 | Role & Permission Verification |
| Tier 12 | T92-T96 | 5 | Navigation & Dashboard |
| Manual | M01-M13 | 12 | Manual-Only Flows (M06 removed — offline-reconnect covered by sync verification coverage) |
| **Total** | | **121 IDs** | **88 T-flows (5 also in manual: T21, T37, T56, T57, T67) + 12 manual + 21 sync = 116 distinct test objectives** |
