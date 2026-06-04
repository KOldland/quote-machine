# Current Development: Inline Drag-and-Drop Form Builder

## Objective
Bring the inline drag-and-drop form builder to completion. When an admin user enters **edit mode**, the main site sidebar dynamically swaps from page navigation to the question builder palette — mirroring the Elementor/SurveyMonkey pattern.

---

## Architecture Decision

- **Sidebar swap on edit_mode**: `index.html` renders `{% if edit_mode %}` block showing the question palette in the main sidebar, instead of the page nav links
- **Single-page-at-a-time canvas** (Elementor-style, not SurveyMonkey multi-page scroll)
- **Three-panel layout**: Left sidebar (palette + controls) | Center (canvas / page blocks) | Right (properties panel)

---

## Implementation Plan

### Step 1 — Sidebar Swap in `index.html`
**File:** `app/templates/index.html`

Wrap the sidebar nav in a conditional:
- `{% if edit_mode %}` — render question palette (`render_question_palette`), page selector, "+ Add Question" button
- `{% else %}` — render the existing page navigation links

This makes the sidebar dynamically switch its role based on mode.

### Step 2 — Remove Duplicate Builder Sidebar from `form.html`
**File:** `app/templates/form.html`

Remove the `<div class="builder-sidebar">` block (lines 30-32) from inside `.builder-container`, since the palette now lives in the main sidebar via `index.html`. The `.builder-container` will then only contain `.builder-canvas` and `.builder-properties`.

### Step 3 — Inject Builder Controls Into Main Sidebar
**File:** `app/templates/index.html`

In the `{% if edit_mode %}` sidebar block, render:
- Page selector / page list (switch between pages)
- Question type palette (`render_question_palette`)
- Quick-action buttons: "+ Add Question"
- Page navigation controls (prev/next page within editor)

### Step 4 — CSS Restructuring for Sidebar Swap
**File:** `app/static/css/main.css`

- `.builder-edit-mode .sidebar` — wider, different padding, palette-optimized layout
- `.builder-container` without an internal sidebar — adjust `.builder-canvas` and `.builder-properties` to fill the space
- Clean visual separation for the three-panel layout
- Ensure `.main-content` margin/width adjusts correctly in edit mode

### Step 5 — Fix "Add Question" Button
**File:** `app/static/js/builder.js`

Investigate and fix `#btn-add-block`:
- Ensure the button element exists in the DOM after sidebar reorganization
- Ensure the event listener is attached to the correct element ID
- If no listener is found, add one calling `addBlock(getBlockTemplate('checkbox_group'))` or showing a type picker

### Step 6 — Pass Builder State to All Routes in Edit Mode
**File:** `app/QMapp.py`

Audit all page routes (index, special_notes_page, summary_page, materials_page, further_requirements_page, additional_costs_page, image_upload_page) to confirm they pass `builder_state`, `blocks`, `current_page`, `selected_block_id` correctly in the `if edit_mode:` branch.

### Step 7 — Foundation Visual Polish
**File:** `app/static/css/main.css`

Add enough CSS to make the three-panel layout recognizable:
- Left sidebar: palette items styled as a proper tool panel
- Center: canvas prominent and clear
- Right: properties panel visible with clean sections
- Visual "edit mode" indicator

---

## Files to Modify

| File | Changes |
|---|---|
| `app/templates/index.html` | Conditional sidebar: nav vs palette (+ page selector, controls) |
| `app/templates/form.html` | Remove `.builder-sidebar` from builder-container |
| `app/templates/_builder_macros.html` | Possibly add a page-list macro for the edit sidebar |
| `app/static/css/main.css` | Sidebar swap styles, builder layout adjustments |
| `app/static/js/builder.js` | Fix "Add Question" button, ensure drag/drop works with new DOM |
| `app/QMapp.py` | (Possibly) ensure routes pass builder state in edit mode |

---

## Testing Checklist (Post-Implementation)

1. Log in as admin, navigate to any form page
2. Click "Edit Page" — verify the sidebar changes from nav links to question palette
3. Verify the canvas still shows the current page's blocks
4. Verify the properties panel still shows on the right when a block is selected
5. Drag a question type from the sidebar palette onto the canvas
6. Click "+ Add Question" — verify a new default block appears
7. Click "Save Block" in properties — verify save works
8. Click "Exit Edit Mode" — verify sidebar reverts to page nav
9. Toggle sidebar collapse/expand in both modes
10. Navigate between pages in edit mode via the page selector