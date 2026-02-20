# Documentation System Audit & Restructure
**Date**: 2026-02-20
**Status**: Ready for implementation
**Priority**: High — stale content actively misleads agents; orphaned rules waste tokens and drift silently

---

## Problem Summary

Full audit of `.claude/` documentation system revealed:
1. **Stale content**: `pdf-generation.md` OCR section documents a binarization step that was deliberately removed. Documents a 7-step pipeline that no longer exists.
2. **Orphaned rule files**: 4 rules with `paths:` triggers but no agent `@` or `shared_rules` reference — invisible to agents unless they happen to edit matching files
3. **Exact duplicates**: Platform Requirements tables, schema file trees, Supabase error tables maintained in two places — guaranteed to drift
4. **Critical content without a home**: Scorecard format, MCP Stability, Context Efficiency rules live only in root CLAUDE.md — not reachable via path-triggered rules
5. **Root CLAUDE.md too heavy**: 360 lines loaded every session; ~150 lines are context-irrelevant for most sessions
6. **One architecture.md leak**: `@.claude/rules/architecture.md` in root forces eager load every session, bypassing its own `paths:` frontmatter

---

## Guiding Principles

- **Never delete without rehoming**: Every piece of content removed from one file must land in a better home first
- **Verify before editing rule files**: Current code is the source of truth, not prior documentation
- **Prefer rule files over root**: Content that is path-specific belongs in a rule file with `paths:` frontmatter
- **Orphaned ≠ useless**: A rule file with no agent `@` load is still valuable (path-triggered); "orphaned" means we explicitly wire it or document why it doesn't need wiring
- **One source of truth**: Duplicates must be consolidated — pick one canonical location and remove the copy

---

## Phase 1 — Fix Stale Content in `pdf-generation.md`

**File**: `.claude/rules/pdf/pdf-generation.md`
**Problem**: OCR Preprocessing Pipeline section (lines 100-108) documents a 7-step process that no longer exists. Step 6 ("Adaptive binarization") was removed because it destroyed 92% of image data on clean PDFs. The entire preprocessing architecture has changed.

### Rewrite the OCR Integration section with actual current pipeline:

Replace the entire "OCR Integration" section with:

```markdown
## PDF Extraction Pipeline (V2 — Current)

### Stage Overview
The extraction pipeline runs in this order:

| Stage | Class | Purpose |
|-------|-------|---------|
| 0 | `DocumentQualityProfiler` | Detect scan vs native PDF, char count |
| 2B-i | `PageRendererV2` | Rasterize pages to PNG (adaptive DPI: ≤10 pages→300, 11-25→250, >25→200) |
| 2B-ii | `ImagePreprocessorV2` | Grayscale + adaptive contrast (no binarization) |
| 2B-ii.5 | `GridLineDetector` | Detect table grid lines (normalized positions) |
| 2B-ii.6 | `GridLineRemover` | Remove grid lines via OpenCV inpainting (grid pages only) |
| 2B-iii | `TextRecognizerV2` | Cell-level OCR (grid pages) or full-page PSM 4 (non-grid) |
| 3 | `ElementValidator` | Coordinate normalization + element filtering |
| 4A | `RowClassifierV3` | Row classification (provisional then final) |
| 4B | `RegionDetectorV2` | Table region detection (two-pass) |
| 4C | `ColumnDetectorV2` | Column boundary detection |
| 4D | `CellExtractorV2` | Extract text per grid cell |
| 4D.5 | `NumericInterpreter` | Parse numeric/currency values |
| 4E | `RowParserV3` | Map cells to ParsedBidItem fields |
| 4E.5 | `FieldConfidenceScorer` | Per-field confidence (weighted geometric mean) |
| 5 | `PostProcessorV2` | Normalization, deduplication, math backsolve |
| 6 | `QualityValidator` | Overall quality check; triggers re-extraction if below threshold |

Re-extraction loop: up to 2 retries at 400 DPI (PSM 3 then PSM 6). Best result by `overallScore` kept.

### Image Preprocessing (Stage 2B-ii)
File: `lib/features/pdf/services/extraction/stages/image_preprocessor_v2.dart`

Steps (in order):
1. Decode PNG (`image` package)
2. Measure contrast (luminance std dev, sampled 1-in-10 pixels)
3. Grayscale conversion (`img.grayscale`)
4. Adaptive contrast enhancement (`img.adjustColor`, factor chosen by pre-contrast: <0.3→1.8, <0.5→1.5, <0.7→1.2, ≥0.7→no-op)
5. Convert to 1-channel (`processed.convert(numChannels: 1)`) for Tesseract compatibility
6. Encode to PNG

**REMOVED**: Binarization — deliberately removed (destroyed 92% of image data on clean PDFs).
**NOT IMPLEMENTED**: Deskewing (`skewAngle` hardcoded to 0.0).

### Grid Line Removal (Stage 2B-ii.6)
File: `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
Package: `opencv_dart` v2.2.1+3

Only runs on pages where `GridLineDetector` flagged a grid. Steps:
1. Decode to grayscale Mat
2. Adaptive threshold (ADAPTIVE_THRESH_MEAN_C, THRESH_BINARY_INV, blockSize=15, C=-2.0)
3. Morphological open for horizontal lines (kernel: width/30 × 1)
4. Morphological open for vertical lines (kernel: 1 × height/30)
5. Combine masks + dilate 1 iteration with 3×3 kernel
6. Inpaint (`cv.INPAINT_TELEA`, radius=2.0)

### OCR Engine (Stage 2B-iii)
File: `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`
Package: `flusseract` (Tesseract 5)

**Grid pages** — cell-level cropping:
- PSM per cell: row 0 (header) → PSM 6, tall rows (>1.8× median height) → PSM 6, data rows → PSM 7
- CropUpscaler: targets 600 DPI, cubic interpolation, 10px padding, max 2000px output
- Re-OCR fallback: PSM 8 + numeric whitelist if numeric column has <0.50 confidence across all words

**Non-grid pages** — full page with PSM 4 (single column)

### Confidence Scoring (Stage 4E.5)
File: `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart`

Weighted geometric mean across 3 factors:
| Factor | Weight | Source |
|--------|--------|--------|
| OCR confidence | 50% | Tesseract `x_wconf` / 100 |
| Format validation | 30% | `FieldFormatValidator` per field type |
| Interpretation confidence | 20% | Pattern match name |

Zero-conf sentinel: if `x_wconf == 0.0` but text is non-empty → uses 0.50 neutral prior.

Low-confidence threshold: **0.80**. Items below this counted in `items_below_0_80`.

### Math Backsolve (Stage 5)
When `qty × unitPrice ≠ bidAmount`: derives `unitPrice = bidAmount / qty` (if round-trips within $0.02).
Applies -0.03 confidence penalty.
```

**Also remove** the old "OCR Integration" section (PSM table + 7-step preprocessing list) — fully replaced above.
**Keep** unchanged: PDF Template Field Mapping, PDF Parsing (Bid Items, ParsedBidItem model, Confidence Handling), Common Issues, Debugging, Testing pattern, Quality Checklist, PR Template.

---

## Phase 2 — Wire Orphaned Rule Files to Agents

Four rule files have valid `paths:` triggers but are invisible to agents.

### 2A. Wire `supabase-sql.md` to `backend-supabase-agent.md`

**Problem**: `backend-supabase-agent.md` loads `data-layer.md` via `@` but NOT `supabase-sql.md`. The SQL cookbook (migrations, RLS, performance queries, error table) is unreachable.

**Fix**: In `backend-supabase-agent.md`:
- Add `@.claude/rules/backend/supabase-sql.md` eager load (alongside existing `@.claude/rules/backend/data-layer.md`)
- Add `backend/supabase-sql.md` to `shared_rules` frontmatter list
- Remove the Common Errors table from the agent body (it duplicates `supabase-sql.md`) — see Phase 3

### 2B. Wire `schema-patterns.md` to `backend-data-layer-agent.md`

**Problem**: `backend-data-layer-agent.md` loads `data-layer.md` but not `schema-patterns.md`. The schema migration pattern, anti-patterns, and quality checklist are unreachable to the data layer agent.

**Fix**: In `backend-data-layer-agent.md`:
- Add `@.claude/rules/database/schema-patterns.md` eager load
- Add `database/schema-patterns.md` to `shared_rules` frontmatter list

### 2C. Wire `sync-patterns.md` to `backend-supabase-agent.md`

**Problem**: `backend-supabase-agent.md` references `sync-constraints.md` (architecture-decisions) but not the architectural layer diagram and class relationships in `sync-patterns.md`.

**Fix**: In `backend-supabase-agent.md`:
- Add `@.claude/rules/sync/sync-patterns.md` eager load
- Add `sync/sync-patterns.md` to `shared_rules` frontmatter list

### 2D. `platform-standards.md` — Explicit Documentation, No Agent Wire Needed

**Rationale**: Platform standards are only needed when editing `android/**/*`, `ios/**/*`, or `pubspec.yaml`. No agent is specifically assigned to platform work — it's handled inline by whichever agent is working. The `paths:` trigger is sufficient. Document this explicitly in the file's frontmatter comment.

**Fix**: Add a comment block at top of `platform-standards.md`:
```markdown
<!--
  Loaded automatically when editing Android/iOS config or pubspec.yaml.
  Not wired to a specific agent — platform work is done inline.
  Canonical source for SDK versions. Root CLAUDE.md references these tables.
-->
```

---

## Phase 3 — Eliminate Exact Duplicates

### 3A. Platform Requirements: Remove from Root CLAUDE.md

**Problem**: Platform Requirements tables (Android SDK, iOS, Test Config) at lines 265-294 are verbatim copy of `platform-standards.md`. Two copies will drift.

**Fix in root CLAUDE.md**: Replace the ~30-line tables block with:
```markdown
## Platform Requirements
See `.claude/rules/platform-standards.md` for Android SDK (compileSdk 36/targetSdk 36/minSdk 24), iOS (15.0+), and test config (Orchestrator 1.6.1 / JVM 12G / Patrol 4.1.0).
```

### 3B. Schema File Tree: Consolidate in `data-layer.md`, Remove from `schema-patterns.md`

**Problem**: `lib/core/database/schema/` file tree appears identically in both `data-layer.md` and `schema-patterns.md`.

**Fix**: Remove the file tree from `schema-patterns.md` Key Files section. Replace with:
```markdown
## Key Files
See `rules/backend/data-layer.md` for the full schema file tree. This file focuses on schema patterns and migration conventions.
```
Keep `schema-patterns.md` focused on: table naming, column conventions, migration pattern, seed data, common patterns (sync_status, timestamps, soft delete), anti-patterns, quality checklist.

### 3C. Supabase Common Errors: Remove from Agent Body

**Problem**: The `PGRST205`, `23503`, `23505`, `42501`, `42P01` error table appears verbatim in both `supabase-sql.md` and `backend-supabase-agent.md` body.

**Fix**: Remove the Common Errors table section from `backend-supabase-agent.md`. After Phase 2A wires `supabase-sql.md` to the agent via `@`, the agent will have access to the table. Add a reference comment:
```
See `rules/backend/supabase-sql.md` for Common Errors table.
```

### 3D. Auth Flow Code Blocks: Thin Out Agent Body

**Problem**: `auth-agent.md` body contains detailed Sign In / Sign Up / Password Reset code blocks that substantially duplicate `supabase-auth.md`.

**Fix**: In `auth-agent.md`, replace the code block sections with brief pattern names and file references:
```markdown
## Auth Patterns
See `@.claude/rules/auth/supabase-auth.md` for full AuthService and AuthProvider patterns.

Key entry points:
- `AuthService.signIn()` / `.signUp()` / `.signOut()` / `.resetPassword()`
- `AuthProvider` — stream listener, `isAuthenticated` getter
- Deep link callback: `com.fvconstruction.construction_inspector://login-callback`
```
Keep: security requirements (token storage, password rules, rate limiting) and the Supabase project reference if it doesn't exist in the rule file.

### 3E. Responsive Breakpoints: Remove from Agent Body

**Problem**: Mobile/Tablet/Desktop breakpoints table appears identically in `flutter-ui.md` and `frontend-flutter-specialist-agent.md`.

**Fix**: Remove the table from `frontend-flutter-specialist-agent.md`. Add reference:
```
Responsive breakpoints: see `rules/frontend/flutter-ui.md` (Mobile <600, Tablet 600-1200, Desktop >1200).
```

---

## Phase 4 — Expand `patrol-testing.md` into Unified Testing Rule

**File**: `.claude/rules/testing/patrol-testing.md`
**Action**: Expand significantly. Keep all existing Patrol / TestingKeys content. Add new sections below.

### Update `paths:` frontmatter
```yaml
---
paths:
  - "integration_test/**/*.dart"
  - "test/**/*.dart"
  - "lib/shared/testing_keys/testing_keys.dart"
  - "lib/shared/testing_keys/quantities_keys.dart"
---
```

### New sections to add (append to end of file):

```markdown
---

## MCP Testing Tools

### Dart MCP (`mcp__dart-mcp__*`)
Use for: launching app, running tests, getting logs, hot reload, analyzing files.

Key tools:
- `launch_app` — launch in debug mode, captures VM service URI
- `run_tests` — run flutter tests without launching app UI
- `get_app_logs` — retrieve console output
- `hot_reload` / `hot_restart` — reload after code changes
- `analyze_files` — static analysis on specific files
- `dart_format` — format Dart files

### Marionette MCP (`mcp__marionette__*`)
Use for: visual spot-checks, screenshots, UI interaction verification.

**Connection workflow:**
1. `dart-mcp launch_app` → captures VM service URI
2. `marionette connect` with the URI
3. `get_interactive_elements` → discover available UI elements
4. Interact via `tap`, `enter_text`, `scroll_to`
5. `take_screenshots` to verify state
6. `get_logs` to debug issues

**Element targeting**: Elements matched by `ValueKey<String>` or text content.
Keys are more reliable — add `key: ValueKey('my_key')` if element not found.

### MCP Stability Rules — CRITICAL
- **NEVER** `Stop-Process -Name 'dart'` — kills both `dart-mcp` and `marionette_mcp` servers, requires full Claude Code restart
- **SAFE kill**: `Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue`
- **If tools show "No such tool available"** → MCP servers were killed → restart Claude Code session
- **Marionette WebSocket drops during**: heavy rendering (PDF pipeline at 300 DPI), GC pauses, rapid sequential ops — Flutter platform limitation, no reconnect in current version
- **Marionette recovery**: relaunch app via `dart-mcp launch_app`, then `marionette connect` with new VM URI

### Marionette Usage Guidelines
- Use for **ad-hoc visual checks and screenshots only** — not full 340-step journeys
- Add delays between rapid operations (tap → wait → screenshot)
- **Never** trigger heavy rendering (PDF import) while Marionette is connected
- For stable, repeatable E2E regression → use `integration_test/` Dart files (no WebSocket dependency)

### Testing Strategy (Hybrid Approach — Session 402 Decision)
1. **Stable regression** → `integration_test/` Dart files (headless, no WebSocket fragility)
2. **Visual spot-checks** → Marionette for screenshots at key screens
3. **Unit coverage** → `test/` for models, repos, providers, services

### UI Test Journey Plan
Living document: `.claude/plans/2026-02-19-marionette-ui-test-journeys.md`
8 journeys · 23 screens · 30+ dialogs · ~340 interaction steps
Test findings: `.claude/test-results/`

---

## PDF Extraction Stage Trace Testing

### Springfield Fixture Workflow

**CRITICAL: Always regenerate fixtures before scorecard/stage trace work.**
Stale fixtures from older pipeline versions produce misleading results. Do NOT analyze failures against stale fixtures.

```powershell
pwsh -Command "flutter test integration_test/generate_golden_fixtures_test.dart -d windows --dart-define='SPRINGFIELD_PDF=C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf'"
```

Regeneration takes ~2-3 minutes. Run this whenever any pipeline stage code has changed.

### Stage Trace Commands
```powershell
# Run extraction diagnostic with diagnostics enabled
pwsh -Command "flutter test test/features/pdf/ --dart-define=PDF_PARSER_DIAGNOSTICS=true"

# Run single extraction test file
pwsh -Command "flutter test test/features/pdf/services/<test_file>.dart"

# Run all PDF tests
pwsh -Command "flutter test test/features/pdf/"
```

### Scorecard Display Format
When presenting scorecard results, ALWAYS use this table format:

| # | Stage | Metric | Expected | Actual | % | Status |
|---|-------|--------|----------|--------|---|--------|

**Bold rows where Status is LOW or BUG.**

### GT Item Trace Format
Each ground-truth item gets exactly 4 rows:

| Item# | Layer | Description | Unit | Qty | Price | Amount |
|-------|-------|-------------|------|-----|-------|--------|

Layers: `Ground Truth`, `Cell Grid 4D`, `Parsed 4E`, `Processed 5`

### Bogus Items Format

| Item# | Description | Unit | Qty | Price | Amount | Fields |
|-------|-------------|------|-----|-------|--------|--------|

**Never dump raw test output. Always format into tables.**

### Test Monitoring Rules
- Report total pass/fail counts from output
- Quote specific failure messages (assertion text, expected vs actual values)
- Group failures by feature/file
- Never say "tests passed" without reading the runner output
- If no output for 60s → kill the process and report as timeout
```

---

## Phase 5 — Rehome Critical Orphaned Root Content

### 5A. Key Packages → Move to `architecture.md`

**Rationale**: `architecture.md` loads for all `lib/**/*.dart` — perfect home for package choices. This is the "what do I use for X" reference agents need during implementation.

**Action**: Add a `## Key Packages` section to `architecture.md`:
```markdown
## Key Packages

| Package | Purpose |
|---------|---------|
| `provider` | State management (ChangeNotifier) |
| `go_router` | Navigation (shell routes, deep links) |
| `supabase_flutter` | Backend / Auth |
| `sqflite` | Local SQLite storage |
| `syncfusion_flutter_pdf` | PDF generation (template filling) |
| `pdfx` | PDF rendering to images |
| `printing` | PDF preview / rasterization (Windows primary path) |
| `flusseract` | Tesseract OCR via native binding (`packages/flusseract/`) |
| `syncfusion_flutter_pdfviewer` | PDF viewing / rendering |
| `image` | Image preprocessing (grayscale, contrast) |
| `opencv_dart` | Grid line removal via inpainting |
| `xml` | HOCR parsing |
```

### 5B. Context Efficiency Rules — Keep in Root

**Rationale**: Subagent caps, parallel Task preference, and context hygiene are meta-level behavioral rules that apply to every session regardless of what files are being edited. They belong in root CLAUDE.md. No change needed.

### 5C. MCP Stability + Scorecard Format → Phase 4 (Done)

Both moved to expanded `patrol-testing.md` in Phase 4.

---

## Phase 6 — Trim Root CLAUDE.md

After Phases 1-5 are complete, root CLAUDE.md should be trimmed to a navigation hub.

### Remove these sections from root CLAUDE.md:

| Section | Lines (approx) | Destination |
|---------|---------------|-------------|
| `@.claude/rules/architecture.md` eager import | ~1 | Remove — let `paths:` handle it |
| MCP Stability section | ~28 lines | Moved to `patrol-testing.md` (Phase 4) |
| Testing Strategy + UI Test Suite sections | ~42 lines | Moved to `patrol-testing.md` (Phase 4) |
| Platform Requirements tables | ~30 lines | Replaced with 2-line pointer (Phase 3A) |
| Reporting Preferences / Scorecard section | ~18 lines | Moved to `patrol-testing.md` (Phase 4) |
| Documentation System section (lines 163-200) | ~38 lines | Collapse to 4-line pointer |

### Collapse Documentation System to pointer:
```markdown
## Documentation System
`.claude/docs/` — Feature overviews + architecture docs (lazy-loaded by agents)
`.claude/architecture-decisions/` — Feature-specific constraints + shared rules
`.claude/state/` — JSON state files for project tracking
`.claude/hooks/` — Pre-flight + post-work validation scripts
Agents load feature docs on demand; see `state/feature-{name}.json` per feature.
```

### Keep in root CLAUDE.md:
- Project intro + Quick Reference (keep short)
- Project Structure tree + Key Files table
- Domain Rules path-trigger table (the routing map — unique, nowhere else)
- Agents table + Skills table
- Session section + Directory Reference
- Quick Reference Commands (core build/run/test/git commands only — remove test-specific commands, those move to `patrol-testing.md`)
- Key Packages → removed (moved to `architecture.md` in Phase 5A)
- Development Tools table (unique, nowhere else — keep)
- Data Flow diagram (keep as one-liner)
- Repositories table (keep)
- Audit System + Lint Suggestions (keep — no other home)
- Context Efficiency rules (keep — meta-level, always relevant)
- Common Mistakes table (keep — universal anti-patterns)

### Expected result: ~160-180 lines (from 360)

---

## Implementation Order

Execute phases in this order — each phase depends on the previous being complete:

1. **Phase 1** — Fix stale `pdf-generation.md` (highest risk: actively misleads agents)
2. **Phase 2** — Wire orphaned rules to agents (before Phase 3 removes duplication from agents)
3. **Phase 3** — Eliminate duplicates (depends on Phase 2 wiring being in place first)
4. **Phase 4** — Expand `patrol-testing.md` (content must exist before root removes it)
5. **Phase 5** — Rehome Key Packages to `architecture.md` (before Phase 6 removes from root)
6. **Phase 6** — Trim root CLAUDE.md (last — only safe after all content has a new home)

---

## Verification Checklist

After all phases complete:
- [ ] `pdf-generation.md` OCR section matches actual `image_preprocessor_v2.dart` code
- [ ] No mention of binarization in any rule file (except as "REMOVED" note)
- [ ] `backend-supabase-agent.md` loads `supabase-sql.md`, `sync-patterns.md` via `@`
- [ ] `backend-data-layer-agent.md` loads `schema-patterns.md` via `@`
- [ ] Platform Requirements appears in root CLAUDE.md as a 2-line pointer only
- [ ] Schema file tree appears in exactly one rule file (`data-layer.md`)
- [ ] Supabase Common Errors table exists only in `supabase-sql.md`
- [ ] `patrol-testing.md` covers: Patrol keys, MCP stability, Marionette connection, dart-mcp tools, Springfield fixture workflow, scorecard format, test monitoring rules
- [ ] Root CLAUDE.md has no `@.claude/rules/architecture.md` eager import
- [ ] `architecture.md` contains Key Packages table
- [ ] Root CLAUDE.md is ≤180 lines
- [ ] Every rule file is either: wired to an agent OR documented as path-trigger-only with explicit note

---

## Files Modified

| File | Change |
|------|--------|
| `.claude/rules/pdf/pdf-generation.md` | Rewrite OCR Integration section with actual V2 pipeline |
| `.claude/agents/backend-supabase-agent.md` | Add `@supabase-sql.md`, `@sync-patterns.md`; remove duplicated error table |
| `.claude/agents/backend-data-layer-agent.md` | Add `@schema-patterns.md` |
| `.claude/agents/auth-agent.md` | Thin out code blocks, reference rule file |
| `.claude/agents/frontend-flutter-specialist-agent.md` | Remove breakpoints table duplication |
| `.claude/rules/database/schema-patterns.md` | Remove file tree (keep in data-layer.md), add pointer |
| `.claude/rules/platform-standards.md` | Add clarifying comment block |
| `.claude/rules/testing/patrol-testing.md` | Expand with MCP, dart-mcp, stage trace, scorecard, Marionette sections |
| `.claude/rules/architecture.md` | Add Key Packages section |
| `.claude/CLAUDE.md` | Remove eager @import, trim 6 sections, collapse Documentation System, remove Platform Requirements tables |
