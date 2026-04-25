# Beta User Guide + Product Showcase — 1-Day To-Do Spec

## Context

Field Guide App (Flutter, offline-first, construction inspectors) is at `0.2.0+1` and beta is imminent. Beta testers are non-technical construction workers, many older, not strong with phones. We need a **short external document** — **6–8 neat pages**, not a manual — that teaches them the happy paths and doubles as a product feature rundown for the boss/company. In-app onboarding is deferred. Target: **one focused day** of work.

## Scope

- External document only (no in-app changes)
- Audience: inspectors (primary) + leadership (via product-overview excerpt)
- Format: Word + PDF, generated from markdown source via Pandoc (fallback: author in Word directly)
- Forms are the hero section; PDF import is expectation-set via a visual gallery, not taught

## Out of Scope

- In-app coach marks / tours / onboarding overlays
- PowerPoint training deck (v2 — Pandoc supports it from same source)
- Pocket / truck card (v2)
- Integration-test screenshot automation + CI drift gate (v2)
- Localization, iOS-specific screenshots, video
- A PDF import *tutorial* (we only set expectations about what PDFs the pipeline accepts)

## Deliverables

| File | Purpose | Target size |
|---|---|---|
| `docs/user-guide/beta-user-guide.md` | Source of truth (markdown) | ~6–8 pp rendered |
| `docs/user-guide/beta-user-guide.docx` | Editable Word, generated | ≤ 10 MB |
| `docs/user-guide/beta-user-guide.pdf` | Email-friendly PDF, generated | ≤ 10 MB |
| `docs/user-guide/product-overview.pdf` | 1-page leadership hand-out (excerpt of Section 1) | 1 pp |
| `docs/user-guide/screenshots/` | ~14 app screenshots + 4 Section-7 file-shape thumbnails + 6 Section-9 PDF thumbnails | — |
| `docs/user-guide/README.md` | Two-line regenerate instructions | — |

## Document Structure (fits in 6–8 pp)

1. **Cover + Contents** (0.5 pp) — title, version `0.2.0 BETA`, 5-line TOC.
2. **Product Overview** (0.5–1 pp) — grouped-by-benefit feature rundown. Doubles as `product-overview.pdf`. Tiles: *Run your day · Stay compliant · Work offline · Track the money (pay apps & contractor comparison, with Excel exports) · Document the work · Bring your bids · Admin & analytics*.
3. **Your First Day** (0.5 pp) — 5-step quick-start with one screenshot. Log in → pick project → open today's entry → fill → sync.
4. **The 4 Tabs** (0.5 pp) — annotated bottom bar; one sentence per tab.
5. **Daily Workflow** (1–1.5 pp) — compact walkthroughs, ~0.5 pp each:
   - Daily Entry Editor (one screenshot, numbered callouts)
   - Sync Dashboard + "Push is not reversible" red-box tip
   - Project Dashboard / Project Setup (half-page combined)
6. **Forms** (1.5–2 pp) ← biggest section, still compact:
   - Top of section: half-column **"PDF Preview is your safety net"** intro.
   - Each of 5 forms (MDOT-1126, MDOT-1174R, QT, Proctor, Weights) gets ~0.3 pp: 1 screenshot, 3-bullet fill steps, and the recurring **"Tap PDF Preview before you save"** callout.
7. **Pay Apps + Contractor Comparison** (1 pp) ← dedicated section:
   - **Top half — Pay Apps.** Short paragraph (what it is, when to file one) + screenshot of Pay Application detail + **thumbnail of the exported Excel workbook** (the boss-showcase artifact). Mention the workbook lives under Settings → Saved Exports.
   - **Bottom half — Contractor Comparison uploads.** Short paragraph + a **3-thumbnail mini-gallery** showing the three accepted upload shapes (the app's dialog offers all three):
     - **Excel (.xlsx)** — sample contractor spreadsheet
     - **CSV (.csv)** — sample contractor CSV export
     - **PDF (.pdf)** — sample contractor PDF (note: "Check the imported rows before exporting" — OCR quality varies)
   - Plus the output: contractor-comparison PDF discrepancy report lands in Saved Exports when done.
8. **Other Tools** (0.5 pp) — 1 line + thumbnail each for Quantities Calculator, Photo Gallery, Todos.
9. **What PDFs Look Like** (1 pp, visual gallery for **Bid Item import**) — two 2×2 grids of PDF first-page thumbnails:
   - **These work**: DOT pay-item schedules · DOT bid tabulations · Pay-item pages from a bid book · Measurement & payment descriptions (only after pay items are imported).
   - **These don't work**: plan drawings · narrative specifications · handwritten or phone-scanned pages · contracts/letters/emails as PDF.
   - Plain-English captions. No "MDOT/ESTQ&A/CTC" jargon. Plus: 100 MB cap, `.pdf` only, 3-question self-check.
   - *Note:* Section 9 is specifically for the **bid item** importer. Contractor Comparison PDF uploads (Section 7) are a different pipeline — any contractor PDF works if the app can read the rows, but OCR quality is the ceiling.
10. **If Something Goes Wrong + Support** (0.5 pp) — single column: offline indicator, sync conflicts, soft-delete/trash, "No pay items found" → Section 9, "Contractor comparison imported wrong rows" → check Section 7 upload shape, support phone/email, Help & Support form screenshot.

## Screenshot Inventory

### App screens (~14 PNGs, Pixel 6 emulator, seeded `harness-project-001`)

- [ ] 1 · Login
- [ ] 2 · Project Dashboard (landing)
- [ ] 3 · Home / Calendar
- [ ] 4 · Entry Editor (full form)
- [ ] 5 · Sync Dashboard (pending items)
- [ ] 6 · Project Setup (new or edit)
- [ ] 7 · Toolbox Home
- [ ] 8 · Forms Gallery
- [ ] 9 · One MDOT form fill state (1126 or 1174R)
- [ ] 10 · MDOT form PDF Preview ★ *(anchor for recurring callout)*
- [ ] 11 · Pay Application detail
- [ ] 12 · Contractor Comparison screen (with the "Choose Contractor File" dialog visible) *(for Section 7 — shows the 3 upload options in context)*
- [ ] 13 · Help & Support form *(for Section 10)*
- [ ] 14 · Settings → Saved Exports list *(shows where the Excel and discrepancy-PDF artifacts land)*

### File-shape thumbnails for Section 7 — Contractor Comparison uploads + Pay App export (~4 PNGs)

*Sources are user-provided; snip first page or a representative screen. Anonymize contractor/project names before embedding.*

- [ ] 15 · Pay App **exported Excel workbook** — open the generated `.xlsx` in Excel, screenshot the main tab (headers visible, first ~10 rows). This is the feature-showcase shot for the boss too.
- [ ] 16 · Contractor upload — **Excel (.xlsx) sample** — screenshot of an expected contractor spreadsheet. Shape/columns: whatever the user's current pipeline accepts.
- [ ] 17 · Contractor upload — **CSV (.csv) sample** — same contractor data as #16 but in CSV form (open in Excel or a text editor).
- [ ] 18 · Contractor upload — **PDF (.pdf) sample** — first page of an accepted contractor PDF.

### PDF first-page thumbnails for Section 9 — Bid Item import gallery (~6 PNGs; cut to 4 if tight)

*Snip first page in Edge/Chrome; save as ~800 px PNG.*

- [ ] 19 · Supported — DOT pay-item schedule *(source: `.tmp/public_mdot_pdf_corpus/bid_item_stress/` or public MDOT letting URL in manifest)*
- [ ] 20 · Supported — DOT bid tabulation *(same source)*
- [ ] 21 · Supported — Pay-item pages from a bid book *(user's OneDrive corpus — anonymize project name if needed)*
- [ ] 22 · Unsupported — Plan drawing *(user's own file)*
- [ ] 23 · Unsupported — Narrative spec *(MDOT Standard Specs chapter works)*
- [ ] 24 · Unsupported — Contract letter or email saved as PDF *(user's own file)*

## Critical Files (read-only, cite for accuracy)

- `lib/core/driver/screen_registry.dart` — screen names
- `lib/core/driver/seed/harness_seed_data.dart` — seeded project/entry IDs
- `lib/core/router/scaffold_with_nav_bar.dart` — `PrimaryNavTab` (bottom tabs)
- `lib/features/forms/presentation/screens/` — 5 MDOT form screens
- `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`, `entry_editor_screen.dart`
- `lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart`, `contractor_comparison_screen.dart` — Section 7 screens
- `lib/features/pay_applications/presentation/dialogs/contractor_import_source_dialog.dart` — confirms the 3 accepted upload types (`.xlsx`, `.csv`, `.pdf`) with the user-facing subtitles
- `lib/features/pay_applications/data/services/pay_app_excel_exporter.dart`, `contractor_comparison_pdf_exporter.dart` — export mechanics (for accurate Section 7 wording)
- `test/features/pdf/extraction/fixtures/pre_release_pdf_corpus_manifest.json` — supported PDF sources (thumbnail references for Section 9)
- `lib/features/pdf/services/pdf_import_limits.dart` — 100 MB cap
- `lib/features/pdf/services/extraction/models/document_profile.dart` — confirms `ocr_only` strategy
- `pubspec.yaml` — app version for cover

## To-Do List (~8 hours, one focused day)

### Phase 1 — Prep (30 min)
- [ ] Create `docs/user-guide/` and `docs/user-guide/screenshots/`
- [ ] Boot Pixel 6 Android 14 emulator
- [ ] Launch app via driver with seed flag so harness data is loaded (`harness-project-001`, `harness-entry-001`)
- [ ] Confirm Pandoc + XeLaTeX installed on Windows; if blocked > 15 min, commit to authoring directly in Word
- [ ] Verify `pandoc hello.md -o hello.pdf` produces a file

### Phase 2 — Capture (~110 min)
- [ ] Capture all 14 app screens (list above) and save as `section<N>_<name>.png`. Includes Contractor Comparison screen with the "Choose Contractor File" dialog open (item #12) and Saved Exports list (#14).
- [ ] Generate one pay app and export to Excel; open the `.xlsx` in Excel; screenshot as item #15.
- [ ] Assemble 3 contractor-upload samples (Excel, CSV, PDF) using user-provided data; thumbnail each as items #16–#18. Anonymize contractor/project names.
- [ ] Snip 6 PDF first-page thumbnails for Section 9 (items #19–#24); anonymize project names where relevant.
- [ ] Spot-check: every form page PDF Preview is captured; the Excel export screenshot clearly shows headers; contractor-upload thumbnails are labeled and distinguishable.

### Phase 3 — Author (~5 hours total)
- [ ] 3a · Section 2 (Product Overview) — 30 min. Tile format; grouped by user benefit. Includes the pay-app/contractor-comparison tile.
- [ ] 3b · Section 3 (First Day) — 15 min. 5 bullets + 1 screenshot.
- [ ] 3c · Section 4 (4 Tabs) — 10 min. Annotated bottom bar.
- [ ] 3d · Section 5 (Daily Workflow) — 45 min. Entry Editor + Sync + Dashboard/Setup.
- [ ] 3e · Section 6 (Forms) — 90 min. Top-of-section "PDF Preview is your safety net" intro. One compact page block per form with the recurring callout.
- [ ] 3f · Section 7 (Pay Apps + Contractor Comparison) — 40 min. Top half: Pay App detail + Excel export thumbnail, note on Saved Exports. Bottom half: contractor-comparison short paragraph + 3-thumbnail mini-gallery (Excel/CSV/PDF) with plain-English captions straight from the `ContractorImportSourceDialog` subtitles. Mention output goes to Saved Exports as a discrepancy PDF.
- [ ] 3g · Section 8 (Other Tools) — 10 min. Quantities/Gallery/Todos one-liners with thumbnails.
- [ ] 3h · Section 9 (What PDFs Look Like — bid item import) — 40 min. Two 2×2 thumbnail grids + captions + 3-question check. Footer note clarifying this is for bid import only, not Section 7's contractor comparison PDFs.
- [ ] 3i · Section 10 (Troubleshooting + Support) — 20 min.
- [ ] 3j · Cover + TOC (Section 1) — 10 min.

### Phase 4 — Export + Polish (60 min)
- [ ] Run Pandoc: `pandoc beta-user-guide.md -o beta-user-guide.docx --toc --toc-depth=2`
- [ ] Run Pandoc: `pandoc beta-user-guide.md -o beta-user-guide.pdf --toc --toc-depth=2 --pdf-engine=xelatex`
- [ ] Create `product-overview.md` from Section 2; export `product-overview.pdf` (1 page)
- [ ] Open both PDFs; verify every image renders, no broken refs, page count ≤ 8
- [ ] Spellcheck in Word
- [ ] Write `docs/user-guide/README.md` (two Pandoc commands + regeneration note)

### Phase 5 — Validate (30 min)
- [ ] Hand `beta-user-guide.pdf` to one non-technical person; time them on login → daily entry → sync push
- [ ] Hand `product-overview.pdf` to one non-inspector; 2-minute recall test ("what does this app do?")
- [ ] Show Section 9 to a tester with 3 sample PDFs (1 pay-item table, 1 spec, 1 drawing); verify they predict correctly from thumbnails alone
- [ ] Show Section 7 to a tester with one of each accepted contractor upload (xlsx, csv, pdf); verify they map each sample to the right option in the dialog

### Phase 6 — File + Follow-Up (10 min)
- [ ] Commit the generated files into `docs/user-guide/` (or attach to a PR)
- [ ] Note v2 roadmap items somewhere visible: PPTX deck from same md, pocket card, integration-test screenshot automation, CI drift gate, in-app tour (separate plan)

## Definition of Done (acceptance checks)

- [ ] `beta-user-guide.pdf` exists, is **≤ 8 pages**, ≤ 10 MB, opens cleanly on a phone PDF viewer
- [ ] `product-overview.pdf` exists, is **1 page**, stands alone (no "see Section X" references pointing outside it)
- [ ] All 5 form types appear in Section 6
- [ ] "Tap PDF Preview before you save" callout appears on every form page (≥ 5 times)
- [ ] Section 7 shows the **Pay App Excel export** thumbnail and a 3-thumbnail mini-gallery of accepted Contractor Comparison upload shapes (Excel / CSV / PDF) with plain-English captions
- [ ] Section 9 shows **visible thumbnails** of ≥ 3 supported + ≥ 3 unsupported PDF shapes with plain-English captions (no MDOT/ESTQ&A/CTC jargon in the user-facing text)
- [ ] Hero check passed: non-technical tester completes login → daily entry → sync push using only the PDF, ≤ 12 min, ≤ 1 unguided question
- [ ] Leadership check passed: non-inspector can describe app purpose in 2 min after reading `product-overview.pdf`
- [ ] PDF-expectations check passed: tester correctly predicts which of 3 sample PDFs will import using Section 9 thumbnails alone
- [ ] Pay-app-export check passed: tester opens the guide's Excel thumbnail and knows what they'd get from "Export to Excel"
- [ ] Contractor-upload check passed: tester picks the correct file type from the 3 accepted shapes given a sample
- [ ] 100 MB cap and M&P "needs existing pay items" precondition both stated in Section 9
- [ ] `README.md` regenerate commands actually work from a fresh shell

## Risks & Mitigations

- **Pandoc/XeLaTeX install stalls:** hard 15-min cap; fall back to authoring in Word.
- **Emulator seed doesn't load harness data:** use the same flag `tools/testing/flows/ui/UiFlowRuntime.ps1` uses for flows (invokes `HarnessSeedData`).
- **Project/contractor-name leakage on thumbnails:** items #15–#18 (Section 7 Excel/CSV/PDF samples) and item #21 (Section 9 bid-book excerpt) may contain real project or contractor names. Black-box redact in the image before embedding; verify by zooming each rendered PDF page to 200%.
- **Over-running the 8.5-hour budget:** cut order — drop items #23/#24 (unsupported PDF thumbnails) → drop item #17 (CSV sample — Excel/PDF thumbnails are enough for Section 7) → drop items #19/#20 (public DOT PDFs from corpus if cached copies unavailable) → drop leadership check. **Never drop:** Section 6 forms, Section 7 Excel export thumbnail (#15), Section 9 gallery.
