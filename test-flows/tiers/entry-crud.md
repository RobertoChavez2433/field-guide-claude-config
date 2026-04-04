# Tier 2: Daily Entry Creation (T15-T23)

> Full entry creation with all sub-entities attached.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T15 | Create Daily Entry (Draft) | daily_entries | tap(calendar_nav) → tap(add_entry_fab) → tap(location_dropdown) → tap(location_select_a) → tap(weather_dropdown) → tap(weather_sunny) → text(temp_low,"45") → text(temp_high,"72") → text(activities,"E2E test activities") → tap(save_draft) | sync,db | Depends: T06 |
| T16 | Add Entry Safety Fields | daily_entries | tap(entry_card) → tap(report_safety_section) → wait(report_site_safety_field) → text(report_site_safety_field,"E2E safety notes") → text(report_sesc_field,"E2E SESC") → text(report_traffic_field,"E2E traffic") → text(report_visitors_field,"E2E visitor") | sync,db | Depends: T15; tap safety card to enter edit mode first |
| T17 | Add Contractor to Entry | entry_contractors | tap(entry_card) → tap(contractors_section_add) → tap(select_contractor_prime) → tap(contractor_entry_save) | sync,db | Depends: T08,T15 |
| T18 | Add Personnel Count | entry_personnel_counts | tap(personnel_add) → text(personnel_count,"5") → tap(personnel_save) | sync,db | Depends: T17 |
| T19 | Add Equipment Usage | entry_equipment | tap(equipment_usage_add) → tap(select_equipment_excavator) → tap(equipment_usage_save) | sync,db | Depends: T10,T15 |
| T20 | Log Quantity | entry_quantities | tap(quantities_section_add) → tap(select_bid_item) → text(quantity_value,"10.5") → text(quantity_notes,"E2E qty note") → tap(quantity_save) | sync,db | Bid item autocomplete keys working |
| T21 | Use Quantity Calculator (HMA) | entry_quantities | tap(quantities_section_add) → tap(calculator_launch) → text(calc_width,"20") → text(calc_length,"100") → text(calc_depth,"4") → text(calc_density,"145") → tap(calculate_btn) → tap(use_result) | sync,db | Calculator not wired from entry screen; use standalone calculator (T38) instead |
| T22 | Attach Photo (inject-photo) | photos | tap(photos_section_add) → inject-photo(test.jpg) → text(photo_caption,"E2E test photo") → tap(photo_save) → wait(photo_thumbnail) | sync,photo | Depends: T15 |
| T23 | Attach Second Photo | photos | tap(photos_section_add) → inject-photo(test2.jpg) → text(photo_caption,"E2E photo 2") → tap(photo_save) → wait(photo_thumbnail) | sync,photo | Depends: T15; needed for gallery tests |

---

# Tier 3: Entry Lifecycle (T24-T30)

> Review, submit, edit, undo, delete entries. Multi-day operations.

| ID | Flow | Table(s) | Driver Steps | Verify-Logs | Notes |
|----|------|----------|--------------|-------------|-------|
| T24 | Edit Entry Inline (Location) | daily_entries | tap(entry_card) → tap(location_chip) → tap(location_select_b) → wait(location_updated) | sync,db | Location dropdown keys working |
| T25 | Edit Entry Inline (Weather) | daily_entries | tap(entry_card) → tap(weather_chip) → tap(weather_cloudy) → wait(weather_updated) | sync,db | Weather dropdown keys working |
| T26 | Create Second Entry (Day 2) | daily_entries | tap(calendar_nav) → tap(calendar_next_day) → tap(add_entry_fab) → tap(location_dropdown) → tap(location_select_a) → text(activities,"Day 2 activities") → tap(save_draft) | sync,db | Depends: T06; creates entry on different date |
| T27 | Review Drafts → Mark Ready | daily_entries | tap(dashboard_nav) → tap(review_drafts_card) → tap(select_all) → tap(review_selected) → tap(mark_ready) → tap(mark_ready) → wait(review_summary) | sync,db | Depends: T15,T26 |
| T28 | Submit Entries (Batch) | daily_entries | tap(submit_entries_btn) → tap(submit_confirm) → wait(dashboard_screen) | sync,db | Depends: T27 |
| T29 | Undo Submission | daily_entries | tap(calendar_nav) → tap(entry_card) → tap(undo_submission_btn) → tap(undo_confirm) → wait(draft_status) | sync,db | Depends: T28 |
| T30 | Delete Entry | daily_entries | tap(entry_card) → tap(overflow_menu) → tap(delete_entry) → tap(delete_confirm) → wait(calendar_screen) | sync,db | Depends: T26; deletes Day 2 entry |
