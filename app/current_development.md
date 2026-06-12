# Current Development Status

## Completed Tasks
- Implemented the Nested "Fractal" UI for the editing builder mode canvas, mapping `Page Details`, `Category Details`, and `Line Item Details`. **[DONE]**
- Added structural breadcrumb navigation across the nested views. **[DONE]**
- Moved page-level control buttons to the bottom of the canvas in `app/templates/form.html`. **[DONE]**
- Formalized Pages and Categories in Schema (as per `SESSION.md`). **[DONE]**
- Bug Fixes & Schema Sync: Fixed `ModuleNotFoundError`, `builder_state` loading, `checkbox_data` arguments, and populated `page_templates` table. **[DONE]**
- Fixed the Category Broken state caused by DOM repositioning of the Questions List. Evaluated standard UI workflows, finished deleting redundant 'Add Question' blocks. **[DONE]**
- Fixed UI layout: adjusted `.li-save-btn` width, enabled proper inner scrolling using fixed `height` instead of `max-height` for `.li-3col-canvas`, and nested `+ Add Category` within `.li-sections-list` so it flows naturally. **[DONE]**
- Removed sticky footer overlap from the `SAVE CATEGORY` button view. **[DONE]**
- Created an empty `/edit_home` landing screen for builder mode safety state rendering after page deletion. **[DONE]**
- Created the "Save As Template" workflow. **[DONE]**

## Current State
The nested fractal UI is structurally sound, styled correctly to flow naturally without layout overlap breaks, and allows editing the schema properties at three distinct hierarchy levels: Pages, Categories, and Line Item questions.

## Immediate Next Task
Create a dedicated "Form Editor" view (Phase 1 of Form > Pages > Categories > Questions hierarchy).

## Active Files for Context
* @app/templates/_builder_macros.html
* @app/templates/index.html
* @app/templates/form_editor.html
* @app/static/js/builder.js
* @app/QMapp.py
* @app/template_store.py
* @app/SESSION.md
* @app/current_development.md

## Form Editor Implementation Plan

### 1. Overview
We need to create the uppermost level in the hierarchy: the Form. This involves creating a dedicated "Form Editor" page in Edit-Mode. This page will reuse the existing UI pattern (two-column canvas) to control Form Details (Title, Description, auto-generated Key) and Page Order (listing available pages with drag-and-drop reordering and a toggle for form visibility). We will also remove the redundant "Undo" button from the sidebar and replace it with a button that navigates directly to the Form Editor. 

Form level data is already stored correctly in the Database via `template_store.sqlite3` -> `form_templates`, we just need to provide the UI to edit these fields and manage the `page_templates` table.

### 2. Key Changes
- **`app/templates/index.html`**:
  - Remove the "Undo" button from the sidebar.
  - Add a "Form Editor" button (e.g. at the top of the Edit-Mode actions, pointing to `/edit_home` or `/form_editor`).
- **`app/QMapp.py`**:
  - Rename or refactor the `/edit_home` route to serve as the new "Form Editor" view (i.e. `/form_editor?edit=1`). Note: `edit_home` was added simply to act as an empty shell, but now it will serve this purpose directly.
  - Expose API endpoints for saving Form details (`/builder_beta/form/update`) and updating Page Order (`/builder_beta/page/reorder`), which will leverage the new Drag-and-Drop sequence in the JS.
- **`app/template_store.py`**:
  - Review that we have methods to modify `form_templates` properties, specifically updating `name` and `description` (using `template_key`). 
  - Ensure reordering capabilities exist for the `page_templates` table.
- **`app/templates/form_editor.html` (New)**:
  - This template will render the 3-column (or 2-column) canvas for Form editing. 
  - The left section contains two tabs: "Form Details" and "Page Order".
  - The right section will display the content dynamically via JavaScript when a tab is clicked.
- **`app/static/js/builder.js`**:
  - Add logic to initialize the Form view (tab switching logic).
  - Add drag-and-drop reordering specifically for the Page List using HTML5 drag API.
  - Add an API call to save form variables and save page ordering / visibility changes.

### 3. Implementation Steps
1. **Remove Undo / Add Form Editor Navigation**:
   - In `app/templates/index.html`, under `.edit-mode-actions`, delete Undo button.
   - Add `<a href="/form_editor?edit=1" class="btn btn-sidebar" style="width:100%;text-align:center;">Form Editor</a>`.
   - In `builder.js`, remove code referencing `btn-undo`, `btn-redo`, and the history arrays.
2. **Setup Routing (`QMapp.py`)**:
   - Replace or modify the `@app.route('/edit_home')` route to instead be `@app.route('/form_editor')`.
   - Fetch the current `form_templates` name and description using `template_store` functions.
   - Fetch all `page_templates` ordered by `display_order`.
   - Render a new template: `render_template('form_editor.html', ...)`
3. **Draft the Template (`form_editor.html`)**:
   - Build a layout derived from `form.html` Edit Mode components.
   - Left side: Tab 1 "Form Details" and Tab 2 "Page Order".
   - Right side: Render the Form Details block (Input for Form Title, Textbox for Description, read-only field for the Form Key) OR the Page Order Block.
   - Page Order block will render simple draggable rows containing a drag handle, Page Title, and a checkbox for `.is_form_visible` (or "Include in Output").
4. **API Integration (`QMapp.py` / `template_store.py`)**:
   - Add `update_form_details(...)` to `template_store.py` executing `UPDATE form_templates SET name = ?, description = ? WHERE key = ?`. 
   - Add backend route `POST /builder_beta/form/update` to trigger this.
   - Add backend route `POST /builder_beta/page/reorder_batch` accepting an array of ordered page payload data to batch update `display_order` (and flags) in the DB.
5. **Drag-and-Drop Scripting (`builder.js`)**:
   - Attach native drag-and-drop attribute `draggable="true"` to the page rows in the new view.
   - Using CSS transform, angle the dragging items dynamically for visual feedback as requested.
   - On drop, execute the `/builder_beta/page/reorder_batch` fetch command with the new index values.

### 4. Technical Considerations
- Navigation consistency: While deleting a page previously redirected to `/edit_home` (an empty view), deleting a Page should now redirect back to `/form_editor?edit=1` so the user remains in the application flow.
- Form Visibility: You mentioned form items having "a check box if they are to appear in 'Form Mode'". `page_templates` does *not* currently have a visibility flag in its schema (though line items do). I will need to verify if `display_order` or a JSON setting in metadata dictates if a page is actually "active/enabled". E.g., `enabled` flag inside `metadata_json` (or we add an `is_enabled` boolean column to the `page_templates` table). 
- History Array Cleanup: We will remove the Undo JS, which cleans up client side memory significantly.