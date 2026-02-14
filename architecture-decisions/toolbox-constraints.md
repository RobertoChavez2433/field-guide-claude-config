# Toolbox Constraints

**Feature**: Inspector Toolbox (Utilities & Quick Reference)
**Scope**: All code in `lib/features/toolbox/` and utility form generation

---

## Hard Rules (Violations = Reject)

### Complex Forms via Builder Pattern
- ✗ No hardcoding UI widgets in screens
- ✓ All toolbox forms built via builder pattern: Form definition → Widget rendering
- ✓ Form definition: JSON schema (type, label, validation, options)
- ✗ No conditional field logic in widgets (move to form definition)

**Why**: Builder pattern allows dynamic form generation and form reuse.

### Auto-Fill Engine
- ✗ No manual typing for repeated fields (e.g., inspector name appears 100 times in forms)
- ✓ Form engine includes auto-fill: Previously-entered values suggested as user types
- ✓ Auto-fill data stored in SQLite (toolbox_autofill table, per user)
- ✗ No auto-filling sensitive data (passwords, credentials)

**Why**: Improves inspector UX and reduces data entry errors.

### Form Validation
- ✓ All forms validated client-side before submission
- ✓ Validation rules defined in form schema (required, regex, numeric range, etc.)
- ✓ User sees validation errors immediately (no server roundtrip)
- ✗ No submitting invalid forms

**Why**: Instant feedback improves UX; reduces invalid submissions.

### No Data Persistence Required
- ✗ No saving toolbox form submissions to database by default
- ✓ Forms are ephemeral (user fills, submits, data used for immediate action)
- ✓ If results need persistence, explicitly integrate with target feature (e.g., save calculator result to notes)
- ✓ Optional: Export form results as PDF/CSV

**Why**: Toolbox is utility; persistence is optional per form.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Form load (100 fields): < 500ms
- Form validation: < 100ms per field
- Auto-fill suggestion: < 200ms (search 1000 historical values)
- Form rendering: 60fps scroll

### Form Library
- Recommend: Use provider for form state management
- Recommend: Generic FormBuilder widget to minimize boilerplate
- Recommend: Form schema validation in data layer (not widgets)

### Auto-Fill Limits
- Recommend: Keep top 10 suggestions per field
- Recommend: Age-out suggestions older than 1 year
- Limit: Max 1,000 auto-fill entries per user (warn if exceeded)

### Test Coverage
- Target: >= 85% for form builder and validation logic
- Lower for individual form UIs (builder handles rendering)

---

## Integration Points

- **Depends on**:
  - `settings` (theme applied to forms)
  - Optionally: any feature (forms can export results to feature-specific data)

- **Required by**:
  - None directly (standalone utility feature)

---

## Performance Targets

- Form load (100 fields): < 500ms
- Validation per field: < 100ms
- Auto-fill suggestions: < 200ms
- Scroll 60fps

---

## Testing Requirements

- >= 85% test coverage for form builder + validation logic
- Unit tests: Form schema parsing, validation rules, auto-fill matching
- Widget tests: FormBuilder renders fields correctly, validation displays errors
- Integration tests: Build 3+ complex forms with 50+ fields, auto-fill suggestions work
- Edge cases: Invalid schema (missing required fields), validation regex errors, auto-fill with special characters

---

## Reference

- **Architecture**: `docs/features/feature-toolbox-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
