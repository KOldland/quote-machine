# Form Builder SOP

This guide explains how to use the Form Builder safely, validate changes, and ship updates with confidence.

## 1. Purpose

Use the Form Builder to manage:
- Page titles shown in the form flow
- Previous/next route links between pages
- Field labels and display order
- Pricing Rules used in Additional Costs calculations
- Payment Plan Rules used in quote stage splits

The builder writes to the active schema draft, so changes are live after save.

## 2. Access

1. Start the app locally:
   - `QM_TEST_MODE=1 PORT=5051 FLASK_DEBUG=0 python3 app/QMapp.py`
2. Open:
   - `http://127.0.0.1:5051/form_builder_demo`

## 3. Builder Layout

The page is split into:
- Form Flow: quick visual map of the step sequence
- Business Rules: pricing and payment logic
- Page Settings: title, navigation, labels, ordering per page

## 4. Editing Rules

### 4.1 Page titles

- Edit "Page Title" inside any Page Settings section.
- This updates the visible page heading and flow label.

### 4.2 Navigation endpoints

- Use Flask endpoint names only (for example: `materials_page`, `review`).
- Do not enter URL paths.
- Invalid endpoint names are rejected with a warning.

### 4.3 Field labels and order

- Change label text in the Label column.
- Adjust Order values to set render sequence.
- Keep IDs and Types unchanged unless code support is added.

### 4.4 Pricing Rules

Update per-unit values used in Additional Costs:
- Kitchen Light Rate
- Kitchen Point Rate
- Loft Light Rate
- Loft Point Rate
- Rounding Precision

### 4.5 Payment Plan Rules

- Set Deposit (%)
- Set each stage Name and Percent
- Deposit + all stage percentages must total 100%

The page shows a live warning if total is not 100%.

## 5. Save Process

1. Make changes
2. Click Save Draft
3. Confirm flash success message
4. Navigate through form pages to verify behavior

## 6. Validation Checklist (Required)

After each save, run this checklist:

1. Open all affected pages and confirm labels/titles render correctly.
2. Submit a sample through Additional Costs and confirm pricing math still works.
3. Confirm payment schedule totals 100% and displays expected stage names.
4. Confirm Next/Previous page navigation works with no dead-end routes.
5. Run tests:
   - `python3 -m unittest discover -s app/tests -v`
6. Run smoke flow:
   - `python3 app/scripts/smoke_submit.py --base-url http://127.0.0.1:5051`

## 6.1 Wave 1 Testing (Current Baseline)

Use this as the first-pass release gate for any builder change.

### Automated checks (agent-runnable)

1. Run one command:
   - `bash app/scripts/ui_regression.sh`
2. Expect all sections to print `PASS`:
   - endpoint checks
   - builder content checks
   - clone + listing checks
   - submit smoke flow
   - unittest run

### Manual checks (human sign-off)

1. Open `http://127.0.0.1:5051/form_builder_demo`
2. Expand each major section and verify readability/spacing:
   - Current Form Flow
   - Pricing Calculations
   - Business Rules
3. Make one harmless label change, save, refresh, and confirm persistence.
4. Walk one realistic quote path in browser and confirm:
   - page order feels logical
   - wording is client-safe
   - pricing behavior matches business intent

### Wave 1 pass criteria

All automated checks pass and manual checks show no blocking UX or business-rule issues.

## 7. Shipping Workflow (Builder + SOP Combined)

Use this sequence for every release candidate:

1. Builder change set
2. Local validation checklist
3. Update this SOP with any new behavior/constraints
4. Re-run tests + smoke
5. Peer sign-off (or self sign-off with notes)
6. Ship

## 8. Common Mistakes

- Using URL paths instead of endpoint names in navigation fields
- Changing many pricing/payment values at once without test checkpoints
- Forgetting to verify the full end-to-end submit flow
- Assuming visual changes are safe without running smoke

## 9. Quick Rollback Approach

If a builder update causes issues:

1. Re-open the builder and restore previous values
2. Save Draft
3. Re-run tests and smoke immediately
4. Log what changed and why

## 10. Current Scope Notes

At this stage, the builder controls schema-driven form behavior and business rules.
Document output/editor refinements are handled in the next phase.

## 11. Beta Builder Track (Parallel, Non-Production)

The beta block builder runs in parallel and does not replace production routes yet.

### 11.1 Beta routes

- Editor: `http://127.0.0.1:5051/builder_beta/page/special_notes_page`
- Runtime: `http://127.0.0.1:5051/builder_beta/render/special_notes_page`
- Runtime payload JSON: `http://127.0.0.1:5051/builder_beta/runtime_payload_json/special_notes_page`

### 11.2 Current beta payload behavior

- Runtime payload now supports cross-page aggregation across answered beta pages.
- Response includes:
  - `current_page`
  - `page_summaries`
  - aggregated `line_items`
  - global totals (`subtotal_before_percent`, `percent_adjustments`, `total_pricing_amount`)

### 11.3 Beta regression checks (required before UI sign-off)

1. Confirm all three beta routes above return `200`.
2. Run tests:
   - `python3 -m unittest discover -s app/tests -v`
3. Confirm tests include and pass:
   - `test_builder_beta_runtime_payload_preview_endpoint`
   - `test_builder_beta_runtime_payload_aggregates_across_answered_pages`
4. Confirm runtime payload JSON returns top-level keys:
   - `current_page`, `page_summaries`, `line_items`, `total_pricing_amount`

## 12. UI Testing Handoff Checklist

Use this checklist when moving from backend work into manual UI validation.

1. Start app in test mode:
   - `QM_TEST_MODE=1 QM_TEMPLATE_STORE_READ=1 PORT=5051 FLASK_DEBUG=0 python3 app/QMapp.py`
2. Validate form builder page loads:
   - `http://127.0.0.1:5051/form_builder_demo`
3. Validate beta editor/runtime pages load:
   - `/builder_beta/page/special_notes_page`
   - `/builder_beta/render/special_notes_page`
4. In beta editor, create or edit at least one block from each type in scope:
   - dropdown
   - text input
   - static heading
5. In beta runtime, submit values and refresh to confirm session persistence.
6. Open payload JSON and verify expected totals and line-item grouping.
7. Record any UI defects with:
   - exact route
   - block id/type
   - expected vs actual
   - screenshot

## 13. Session Close-Out Notes Template

Append this to daily notes before handing off:

- Build/test status: `PASS` or `FAIL`
- Unit tests: `<passed>/<total>`
- Beta routes (`page`, `render`, `runtime_payload_json`): `200/200/200` or actual
- Latest risk observed:
- Next UI test target:
