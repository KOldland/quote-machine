# ClientZero Testing Workflow — End-to-End Demo

## Overview

This document defines the testing workflow for the clientzero demo — a viable working product that serves as both a demo and a platform to build the SaaS version to completion.

---

## Prerequisites

1. Flask app running: `cd /Volumes/Document Drive/sites/Quote_Machine/QM_web_app && python3 -m app.QMapp`
2. Template store populated: `app/template_store.sqlite3` (already seeded with 784 line items)
3. Demo images available: `app/demo_images/` (14 images, 7 pairs landscape/portrait)
4. Form template key: `builder_beta` (First Client Template V1)

---

## Test 1: Full Form Setup (Client Data from DB)

**Goal:** Verify the form is fully configured from the DB data for clientzero.

### Steps
1. Navigate to `/` — should show "Project Details" page (index)
2. Verify the form template key is `builder_beta`
3. Check that all 9 pages are accessible:
   - `index` → Project Details
   - `special_notes_page` → Special Notes
   - `summary_page` → Summary Page
   - `materials_page` → Materials and Details
   - `further_requirements_page` → Further Requirements and Considerations
   - `additional_building_work_page` → Additional Building Works
   - `additional_costs_page` → Additional Costs
   - `optional_extras_page` → Optional Extras
   - `image_upload_page` → Image Upload
4. Verify 784 line items are loaded across categories
5. Verify navigation links between pages work (next_endpoint / previous_endpoint)

### Expected Result
- All 9 pages render correctly
- Line items load from DB for each page
- Navigation flows: index → special_notes_page → summary_page → materials_page → further_requirements_page → additional_building_work_page → additional_costs_page → optional_extras_page → image_upload_page

---

## Test 2: Editor Fully Working End-to-End

**Goal:** Client should be able to change any page, section, or question fully.

### Steps
1. Log in as admin (set `QM_ADMIN_PASSWORD` env var, then POST to `/admin/promote`)
2. Navigate to builder editor (e.g., `/builder_beta/` or edit mode)
3. Test page-level edits:
   - Add a new page
   - Delete a page
   - Reorder pages
4. Test section/category-level edits:
   - Add a new category to a page
   - Delete a category
   - Reorder categories
5. Test question-level edits:
   - Add a new question (line item) to a category
   - Edit question label, description, pricing
   - Delete a question
   - Reorder questions within a category
6. Test block-level edits on the index page:
   - Add/delete/reorder blocks
   - Change block types (text_input, checkbox_group, line_items_by_category, etc.)
7. Save changes and verify they persist across page reload

### Expected Result
- All CRUD operations work for pages, categories, questions, and blocks
- Changes persist in the template_store.sqlite3 database
- UI reflects changes immediately after save

---

## Test 3: Calculator Logic

**Goal:** Calculator logic is set up per client directions and easy to reconfigure.

### Steps
1. Check `app/calculator.py` — verify `calculate_quote()` function at line 27
2. Verify calculator reads from template_store.sqlite3 for line items
3. Test calculator with sample form data:
   - Submit form with known line item selections
   - Verify subtotals, percent adjustments, and grand total compute correctly
4. Test override functionality:
   - Set session overrides for output groups
   - Verify overrides are applied on top of calculated subtotals
5. Test reconfiguration:
   - Change a line item's pricing mode (fixed, entered, quantity_rate, percent_subtotal)
   - Verify calculator picks up the change

### Expected Result
- Calculator produces correct totals based on selected line items
- Overrides are applied correctly
- Reconfiguring line items immediately affects calculations

---

## Test 4: Form Mode Running End-to-End

**Goal:** Form should run from beginning to end for a job.

### Steps
1. Start at `/` (Project Details page)
2. Fill in client address and date
3. Click "Continue" → navigate to first dynamic page
4. Fill in checkboxes/inputs on each page
5. Navigate through all pages using next/previous buttons
6. Land on `/review` page
7. Verify all submitted data is displayed correctly on review page
8. Verify line items are shown grouped by category
9. Verify pricing totals are correct

### Expected Result
- Complete form flow works without errors
- Data persists across page navigation
- Review page displays all submitted data correctly
- Pricing totals match expected calculations

---

## Test 5: Image Upload and Automatic Alignment

**Goal:** Images should be easily uploaded and alignment should happen automatically.

### Steps
1. Navigate to `image_upload_page`
2. Upload an image (use demo images from `app/demo_images/`)
3. Verify image is saved to `static/uploads/`
4. Test image alignment:
   - Upload landscape image → verify it renders in landscape orientation
   - Upload portrait image → verify it renders in portrait orientation
   - Upload multiple images → verify they align correctly in the output
5. Test image display in review/export:
   - After upload, navigate to review page
   - Verify uploaded images appear in the review
   - Export to PDF → verify images are embedded correctly

### Expected Result
- Images upload successfully
- Orientation is detected and preserved (landscape vs portrait)
- Images display correctly in review and export
- Multiple images align properly in the output document

---

## Test 6: Review Mode

**Goal:** Review mode should run correctly.

### Steps
1. Complete the form flow (Test 4)
2. Land on `/review` page
3. Verify all 4 template variables are populated:
   - `review_data` — form answers grouped by section
   - `li_by_category` — selected line items grouped by category
   - `totals_by_group` — pricing breakdown per group
   - `TITLE_MAPPING` — human-readable field names
4. Verify the accordion UI works (expand/collapse sections)
5. Verify the cost matrix table displays correctly
6. Test POST on review page — make checkbox changes and verify they persist
7. Verify grand total recalculates after overrides

### Expected Result
- Review page renders all sections correctly
- Accordion UI is functional
- Cost matrix shows correct pricing
- Checkbox changes on review page persist
- Grand total is accurate

---

## Test 7: Quote Editor Mode

**Goal:** Quote Editor Mode should allow the user to make changes to the quote directly within the app.

### Steps
1. After completing the form and reaching review page
2. Look for quote editing controls (inline editing of line items, quantities, costs)
3. Test editing a line item's quantity → verify total recalculates
4. Test editing a line item's unit cost → verify total recalculates
5. Test adding a custom line item not from the catalog
6. Test removing a line item from the quote
7. Verify changes persist when navigating away and back to review
8. Verify changes are reflected in export (PDF/DOCX)

### Expected Result
- Quote can be edited inline within the app
- All edits trigger recalculation of totals
- Changes persist across navigation
- Export reflects edited quote data

---

## Test 8: Export Function (PDF and Word)

**Goal:** Export should work as PDF or Word doc.

### Steps
1. Complete the form and reach the review page
2. Verify `session['form_key']` is set (should be `builder_beta`)
3. Verify `session['form_data']` is populated
4. Test PDF export:
   - Navigate to `/api/export-pdf`
   - Verify PDF is downloaded with correct content
   - Verify images are embedded in the PDF
   - Verify pricing totals are correct in the PDF
5. Test Word export:
   - Navigate to `/api/export-docx`
   - Verify DOCX is downloaded with correct content
   - Verify line items table is populated
   - Verify subtotals and grand total are correct
   - Verify payment schedule section is present
6. Test export after quote edits (Test 7) — verify edited data is reflected

### Expected Result
- PDF export generates a valid PDF with all quote data
- DOCX export generates a valid Word document with all quote data
- Both exports include images, line items, pricing, and payment schedule
- Edited quote data is reflected in exports

---

## Test Execution Order

| Order | Test | Duration | Depends On |
|-------|------|----------|------------|
| 1 | Full Form Setup | 15 min | None |
| 2 | Editor End-to-End | 30 min | Test 1 |
| 3 | Calculator Logic | 15 min | Test 1 |
| 4 | Form Mode End-to-End | 20 min | Tests 1, 3 |
| 5 | Image Upload & Alignment | 15 min | Test 4 |
| 6 | Review Mode | 10 min | Test 4 |
| 7 | Quote Editor Mode | 20 min | Test 6 |
| 8 | Export Function | 15 min | Tests 6, 7 |

**Total estimated time:** ~2.5 hours

---

## Quick Smoke Test (5 minutes)

For a quick verification that the core flow works:

1. Start the app: `python3 -m app.QMapp`
2. Open browser to `http://localhost:5000/`
3. Fill in Project Details (address, date)
4. Click Continue → navigate through pages
5. Reach `/review` — verify data displays
6. Open new tab: `http://localhost:5000/api/export-pdf` — verify PDF downloads
7. Open new tab: `http://localhost:5000/api/export-docx` — verify DOCX downloads

---

## Known Issues / Blockers

| Issue | Status | Notes |
|-------|--------|-------|
| get_builder_beta_state() bug | ✅ Fixed | Schema pages preserved, state.get('pages') only used as fallback |
| Review route missing | ✅ Fixed | Route exists at QMapp.py:2747 |
| form_key not set in session | ✅ Fixed | Added in index() route |
| form_data not populated for export | ✅ Fixed | Added in review() route |
| export_routes fallbacks | ✅ Fixed | Improved to use session data |

---

## Rollback Plan

If any test fails critically:
1. Restore `QMapp.py` from backup: `QMapp.py.bak.py`
2. Restore `template_store.sqlite3` from backup if needed
3. Revert `export_routes.py` changes
4. Restart the Flask app

---

## Sign-Off Criteria

- [ ] Test 1: Full Form Setup passes
- [ ] Test 2: Editor End-to-End passes
- [ ] Test 3: Calculator Logic passes
- [ ] Test 4: Form Mode End-to-End passes
- [ ] Test 5: Image Upload & Alignment passes
- [ ] Test 6: Review Mode passes
- [ ] Test 7: Quote Editor Mode passes
- [ ] Test 8: Export Function passes

**All 8 tests must pass before clientzero demo is considered ready.**