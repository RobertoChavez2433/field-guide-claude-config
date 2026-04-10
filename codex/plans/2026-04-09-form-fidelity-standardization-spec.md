# 2026-04-09 Form Export Fidelity + Shared Workflow Standardization Spec

## Summary

Standardize the forms stack around one reusable, open, section-based workflow
shell, using 0582B's openness as the interaction baseline, while fixing the
two current fidelity problems in parallel:

- IDR / daily-entry export fidelity is still wrong against the canonical PDF.
- MDOT 1126 has both export/capture drift and a one-off wizard UX that no
  longer fits the direction of the app.

Locked intent:

- Future forms use a shared shell, with freedom only where the form genuinely
  needs it.
- The default feel should be more like 0582B: open, visible, section-driven.
- Typed-only validated signatures are the standard.
- The Forms gallery should be split by mode, not one dense mixed list.
- 1174R Concrete should be phased into the same rollout, after the shell is
  proven on IDR/1126.

## Key Changes

### 1. Canonical export fidelity closure

#### IDR / daily-entry export

- Keep `assets/templates/idr_template.pdf` as the canonical runtime template
  and verify it against the clean source PDF already identified.
- Correct the IDR writer against the real AcroForm layout, with these
  corrections:
  - treat day as an autofilled text field, not a user-facing dropdown
    interaction
  - remove any planned product work around the record drawings uploaded
    checkbox; leave it unused/off
  - write to the real signature target, not placeholder legacy fields
  - add deterministic contractor/equipment row ordering before field assignment
  - map equipment-use visibility honestly, including the real checkbox fields
    where the template expects them
  - clear unused rows and checkbox states cleanly
- Extend tests to prove:
  - canonical field inventory is preserved
  - day autofill is correct
  - contractor/equipment row ordering is stable
  - checkbox state matches selected equipment
  - exported PDF remains editable

#### MDOT 1126 export

- Audit `assets/templates/forms/mdot_1126_form.pdf` the same way, but treat the
  main issue as missing capture surface, not checkbox complexity.
- Keep `fillMdot1126PdfFields` as the export seam, but align it to the real
  template and the actual UI contract.
- Expose and validate the fields the filler already expects or should expect:
  - control section
  - report number
  - route/location
  - construction engineer / maintenance coordinator
  - storm water operator number
  - training number
  - date of last inspection
  - weekly reporting period
  - average temperature
  - high temperature
  - remarks
- Verify signature stamping targets the real 1126 signature area and stays
  editable after export.
- Remove remaining drawn-signature assumptions from 1126 specs/comments/tests.

#### 1174R Concrete

- Add `1174R Concrete.pdf` to the canonical template inventory now.
- Perform the same first-pass audit:
  - field inventory
  - field types
  - likely header/row/remarks/signature seams
- Do not implement 1174 UI first; use the audit to shape its later onboarding
  onto the shared shell.

### 2. Shared form workflow shell

Create one reusable form workflow shell for non-pay-app forms.

#### Shared shell contract

- Common shell owns:
  - app bar/title
  - dirty-state / leave-confirm handling
  - section navigation
  - section completion/error badges
  - preview/export status/actions
  - attachment status
  - typed-signature status
- Form-specific logic lives inside pluggable section widgets and controllers,
  not bespoke top-level screens.

#### Shared building blocks

- Standardize reusable section blocks for:
  - header/project metadata
  - context/date/report metadata
  - repeatable rows/tables
  - remarks/notes
  - typed signature
  - attach-to-entry
  - export state/actions
- Add a section-definition model:
  - section id
  - label
  - completion state
  - error state
  - widget builder
- Keep preview/export/attach mutations behind the existing approved owners.

### 3. MDOT 1126 refit

Move 1126 from a narrow forced-step wizard to the shared open editor model.

#### New 1126 shape

- Refit 1126 into visible sections:
  - Header
  - Inspection context
  - Rainfall
  - SESC measures
  - Remarks
  - Signature
  - Attach / export
- Preserve weekly-specific behavior:
  - carry-forward
  - report numbering
  - date-of-last-inspection logic
  - reminder anchoring
- But surface that behavior inside visible sections, not hidden step
  transitions.

#### Product behavior

- First-week and carry-forward fills still work, but in the same shell.
- Attach/create-entry behavior remains shared and entry-owned.
- Editing a signed 1126 still clears the signature immediately.
- 1126 should no longer feel like a different product from 0582B.

### 4. Forms gallery redesign

Replace the current dense mixed gallery with a split-by-mode surface.

#### Modes

- `Create`
  - form-type cards first
  - easy to start a new workflow
- `Saved`
  - editable responses grouped by form type
  - lighter cards, less vertical intimidation
- `History`
  - export artifact history only

#### Gallery goals

- Reduce cognitive load.
- Make “start a form” and “resume a form” separate mental models.
- Keep export history out of the editable-work surface.

### 5. 1174R onboarding after shell proof

Once IDR fidelity and 1126 shell refit are stable:

- register 1174R against the shared shell
- define its canonical field mapping
- define its section set using the same building blocks
- verify preview/export/attachment behavior according to the same contract as
  other non-pay-app forms

## Interface / Contract Changes

- Add a shared non-pay-app form workflow shell.
- Add a reusable section-definition contract for form editors.
- Replace 1126's bespoke top-level wizard with the shared shell.
- Update the Forms gallery IA to `Create / Saved / History`.
- Expand the canonical PDF audit contract to include 1174R.
- Make typed signature the explicit forms standard in specs/comments/tests.

## Test Plan

### PDF fidelity

- IDR:
  - field inventory preserved
  - day autofill correct
  - stable contractor/equipment row mapping
  - checkbox state correct
  - signature target correct
  - unused rows/checkboxes clear
- 1126:
  - all mapped fields exist in shipped template
  - newly exposed fields round-trip to export
  - carry-forward values export correctly
  - signature area and editable export behavior remain correct
- 1174R:
  - inventory test only in this phase
  - implementation tests added when its shell work starts

### Workflow shell / UI

- shared shell renders section states consistently
- 1126 first-week and carry-forward flows both work inside the new shell
- signed-edit invalidation still works
- shared attach-to-entry flow still works
- preview/export remain owner-driven

### Gallery

- Create mode shows available workflows clearly
- Saved mode groups responses by form type
- History mode remains export-only
- dense mixed-list behavior is retired

### Device validation

- S21 proof for:
  - IDR export fidelity
  - 1126 fill/edit/export/attach/reopen flows
  - typed-signature path
  - daily-entry bundle export with attached 1126
  - gallery usability after mode split

## Execution Order

1. Close IDR canonical mapping fidelity.
2. Close 1126 template audit + missing capture surface.
3. Extract the shared form workflow shell.
4. Refit 1126 onto that shell.
5. Redesign the Forms gallery into `Create / Saved / History`.
6. Audit and register 1174R onto the new standardization backlog, then
   implement it after the shell is proven.
7. Re-run targeted tests and S21 end-to-end verification.

## Assumptions

- Shared shell is the default, not a prison; unusually complex forms can keep
  specialized internals if they still use the shared
  shell/action/signature/attachment contracts.
- 0582B is the interaction reference, not the literal implementation template.
- Typed signatures are the only supported form-signature mode unless a future
  legal requirement forces a new contract.
- Pay apps stay outside attach-to-entry, but remain part of the broader export
  architecture.
- The record-drawings checkbox on IDR is deliberately out of scope and left
  unused/off.
