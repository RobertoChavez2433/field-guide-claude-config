# Sync Flows S04-S06: Forms + Todos + Calculator

> Compaction pause after S06 — checkpoint written, user prompted to continue.
> Every flow in this file must satisfy the framework proof standard:
> UI action, SQLite row, `change_log`, Supabase, receiver SQLite, receiver UI,
> and log review.

---

## S04: Forms

**Tables:** inspector_forms, form_responses
**Depends:** S02

**Admin (4948):**

1. Navigate to entry → add form:
   ```bash
   # Navigate to dashboard → tap entry card → wait for report screen
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"entry_card_<ctx.entryId>"}'
   sleep 2
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"report_add_form_button"}'
   sleep 1
   ```

2. Select 0582B form → fill header fields → save.

   Look for the form selection dialog that appears after tapping `report_add_form_button`. Tap the 0582B form entry in the list (key pattern likely `form_selection_item_<formId>` or a labeled list tile — identify the 0582B entry by its visible label). Then fill in any required header fields in the form editor and tap the save or confirm button to persist the form response.

3. Apply the framework cross-device sync protocol (6-step).

**Required verification:**
- sender SQLite: verify both `inspector_forms/<formId>` and
  `form_responses/<responseId>`
- sender queue: verify both tables drain after sync
- Supabase: verify both `inspector_forms` and `form_responses` rows by ID
- receiver SQLite: verify both rows exist after pull
- receiver UI: form visible in entry/report/forms UI

**Capture:** `ctx.formResponseIds` and any created `inspector_forms` IDs in notes

---

## S05: Todos

**Tables:** todo_items
**Depends:** S01

**Admin (4948):**

1. Navigate to toolbox → todos:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   # Toolbox is accessed via dashboard card, not bottom nav
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_toolbox_card"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"toolbox_todos_card"}'
   sleep 1
   ```

2. Create todo:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"todos_add_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"todos_title_field","text":"VRF-Check rebar spacing '"${RUN_TAG}"'"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"todos_save_button"}'
   sleep 1
   ```

3. Apply the framework cross-device sync protocol (6-step).

**Supabase Verify:** Query `todo_items` by project_id.

**Capture:** `ctx.todoIds`

---

## S06: Calculator

**Tables:** calculation_history
**Depends:** S01

**Admin (4948):**

1. Navigate to toolbox → calculator:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_nav_button"}'
   sleep 1
   # Toolbox is accessed via dashboard card, not bottom nav
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"dashboard_toolbox_card"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"toolbox_calculator_card"}'
   sleep 1
   ```

2. Select HMA tab → fill fields → calculate → save:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_tab"}'
   sleep 1
   # HMA inputs: area (sq ft), thickness (inches), density (lbs/cu ft)
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_area","text":"2400"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_thickness","text":"4"}'
   curl -s -X POST http://127.0.0.1:4948/driver/text -d '{"key":"calculator_hma_density","text":"145"}'
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_calculate_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -d '{"key":"calculator_hma_save_button"}'
   sleep 1
   ```

3. Apply the framework cross-device sync protocol (6-step).

**Supabase Verify:** Query `calculation_history` by project_id.

**Capture:** `ctx.calculationIds`

**--- COMPACTION PAUSE ---**
