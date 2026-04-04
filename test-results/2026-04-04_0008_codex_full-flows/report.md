# Test Run Report — 2026-04-04 00:08

Platform: android `RFCNC0Y975L`
Run Dir: `.claude/test-results/2026-04-04_0008_codex_full-flows`

## Results
| Flow | Status | Notes |
|------|--------|-------|
| T02 | PASS_WITH_ERRORS | Tab navigation worked, but debug logs recorded RenderFlex overflows. Existing issue: #165. |
| T05 | PASS | Project created successfully; app returned to dashboard after save instead of projects list. |
| T06 | PASS | First location added successfully. |
| T07 | PASS | Second location added successfully. |
| T08 | FAIL | Project setup contractor add flow lost HTTP-driver keys after inline create refactor. Issue: #163. |
| T09 | BLOCKED | Blocked by T08. |
| T10 | BLOCKED | Blocked by T08/T09. |
| T11 | PASS | Manual pay item added successfully. |
| T12 | PASS | Second pay item added successfully. |
| T13 | PASS | Inspector assignment saved successfully. |
| T14 | PASS | Project search returned the created project. |
| T15 | PASS | Daily entry created, saved, and returned to dashboard. |
| T16 | PASS_WITH_ERRORS | Safety fields accepted text and updated the entry, but the section did not clearly exit edit mode and report view later overflowed. |
| T17 | BLOCKED | Entry contractor flow blocked because project-level contractor setup failed in T08. |
| T18 | BLOCKED | Blocked by T17. |
| T19 | BLOCKED | Blocked by T17/T10. |
| T20 | PASS | Quantity autocomplete, dialog, and insert worked; `entry_quantities` row created. |
| T22 | PASS | Photo injected successfully via driver direct-insert path; `photos` row created. |
| T41 | PASS_WITH_ERRORS | PDF preview route opened and template filled, but export logs omitted attached photos and closing preview triggered a widget lifecycle error. Issues: #166, #168. |

## Bugs Found
- #163 Project setup inline contractor creation lost HTTP-driver keys.
- #164 Startup/manual sync pushed daily entry into Supabase RLS denial during the earlier part of the run.
- #165 Basic navigation/report surfaces still throw RenderFlex overflow errors.
- #166 Entry PDF export omits attached photos after successful entry photo insert.
- #167 `verify-sync.ps1` cannot verify Supabase state because the loaded API key is invalid.
- #168 Closing entry PDF preview triggers deactivated widget ancestor lookup in the entry editor.

## Sync Verification
- Only one ADB device was connected, so the dual-device S01-S11 sync suite could not be completed as written.
- Admin-side sync verification was still run at the end through the UI:
  - pre-sync state: `pendingCount=15`
  - post-sync state: `pendingCount=0`
  - final sync timestamp: `2026-04-04T04:31:28.767342Z`
- The final sync cycle logged:
  - `Push complete: 15 pushed, 0 errors, 0 RLS denials`
  - `Sync cycle: pushed=15 pulled=0 errors=0 conflicts=0 skippedFk=0 skippedPush=6 duration=6419ms`
- Supabase verification script could not be used because `tools/verify-sync.ps1` returned `Invalid API key` for every query attempt. Issue: #167.

## Key IDs
- projectId: `f5c773bf-974d-4285-8ed1-66ca594e82d9`
- locationA: `8d677c92-112f-4357-8246-b31a295ebcdd`
- locationB: `2ca56ab8-bbc4-4031-a532-f516d8514acf`
- entryId: `e9926da5-aa6a-4149-8c79-20fcec3693f9`
- bidItem1: `339cbf5a-d807-4526-be41-7a33014a8e80`
- bidItem2: `efe5f632-e218-4bcb-ad0e-0a8a687543a6`
- entryQuantity1: `d0540d98-75d7-45f7-9050-ef346b173e78`
- photo1: `22c83530-265f-4b5f-a793-76176fe13412`

## Observations
- Started from an already-authenticated admin session on dashboard; cold-login auth flows were not exercised first.
- New entry weather auto-populate did fire on initial load before manual header edits:
  - `WeatherService: Got location 42.65, -85.28`
  - `WeatherService: Got weather WeatherData(condition: Rain, high: 64, low: 41)`
- Route handling on the current shell is more reliable through `POST /driver/navigate` than bottom-nav taps when overlays are present.
- The report screen generated a larger overflow once the entry/report route was exercised more deeply:
  - `FlutterError: A RenderFlex overflowed by 244 pixels on the bottom.`
