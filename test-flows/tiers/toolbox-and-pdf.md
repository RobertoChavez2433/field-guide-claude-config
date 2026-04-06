# Tier 4: Toolbox (T31-T40)

> Todos CRUD, forms lifecycle, calculator, gallery browsing.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T31 | Create Todo | todo_items | tap(toolbox_nav) → tap(todos_tile) → tap(add_todo_fab) → text(todo_title,"E2E Todo Item") → text(todo_desc,"Test description") → tap(todo_priority_high) → tap(todo_save) | sync,db | Depends: T05 |
| T32 | Edit Todo | todo_items | tap(todo_card) → text(todo_title,"E2E Todo Updated") → tap(todo_save) | sync,db | Depends: T31 |
| T33 | Complete Todo | todo_items | tap(todo_checkbox) → wait(todo_completed) | sync,db | Depends: T31 |
| T34 | Delete Todo | todo_items | tap(todo_delete_icon) → tap(delete_confirm) | sync,db | Depends: T31 |
| T35 | Create Form Response (0582B) | form_responses | tap(toolbox_nav) → tap(forms_tile) → tap(new_0582b_btn) → wait(mdot_hub_screen) | sync,db | Depends: T05 |
| T36 | Fill Form Fields | form_responses | text(form_structure_name,"E2E Structure") → text(form_test_density,"128.5") → text(form_test_moisture,"6.2") → tap(form_save) | sync,db | Depends: T35 |
| T37 | Submit Form | form_responses | tap(form_submit_btn) → tap(submit_confirm) → wait(form_submitted_status) | sync,db | Section-by-section submit, no global submit button |
| T38 | Calculator — HMA | calculation_history | tap(toolbox_nav) → tap(calculator_tile) → tap(hma_tab) → text(calc_width,"20") → text(calc_length,"100") → text(calc_depth,"4") → text(calc_density,"145") → tap(calculate_btn) → wait(result_card) → screenshot | db | Depends: T01 |
| T39 | Calculator — Concrete | calculation_history | tap(concrete_tab) → text(calc_width,"10") → text(calc_length,"50") → text(calc_depth,"6") → tap(calculate_btn) → wait(result_card) → screenshot | db | Depends: T01 |
| T40 | Gallery — Browse & Filter | N/A | tap(toolbox_nav) → tap(gallery_tile) → wait(gallery_grid) → tap(filter_btn) → tap(filter_today) → wait(gallery_filtered) → tap(clear_filters) → screenshot | nav | Depends: T22; needs photos to exist |

---

# Tier 5: PDF & Export (T41-T43)

> Export entries and forms as PDF.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T41 | Export Entry as PDF | N/A (local) | tap(entry_card) → tap(export_pdf_icon) → wait(pdf_actions_dialog) → tap(pdf_preview) → wait(pdf_ready) → screenshot | pdf | Depends: T15 |
| T42 | Export Entry Folder (with Photos) | N/A (local) | tap(entry_card) → tap(export_pdf_icon) → wait(pdf_actions_dialog) → tap(pdf_save) → wait(folder_saved) → screenshot | pdf | Depends: T22; entry must have photos |
| T43 | Form PDF Export | N/A (local) | tap(form_card) → tap(form_export_pdf) → wait(pdf_ready) → screenshot | pdf | Depends: T37 |

## Supplemental Pay App & Export Coverage

Detailed pay-application and exported-history validation now lives in:

- `test-flows/tiers/pay-app-and-exports.md`

Use that doc for:

- exported-artifact history visibility
- same-range replace with pay-app number preservation
- overlap-block behavior
- pay-app delete propagation
- contractor comparison import plus discrepancy PDF export
