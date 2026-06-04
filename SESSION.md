# Active Sprint Handoff

## Workspace Structure (Updated 04/06/26)
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/` — all git commands must be run from here
* **Branch**: `master`
* **Context archive**: `app/context_archive/` (old .md docs archived here)
* **GitHub Repository**: Linked to `https://github.com/KOldland/quote-machine` as primary `origin` remote.

## Current Goal
* Complete the inline drag-and-drop form builder by implementing the sidebar swap when entering edit mode. Admin users clicking "Edit Page" see the main sidebar switch from page navigation to the question builder palette — the full plan is documented in `app/current_development.md`.

## Active Files for Context
All paths are relative to the VS Code workspace root (`QM_web_app/`):
* `app/QMapp.py`
* `app/templates/form.html`
* `app/templates/_builder_macros.html`
* `app/static/js/builder.js`
* `app/static/css/main.css`
* `app/templates/builder_beta.html`
* `app/templates/index.html`

## What Works
* Flask-based quote generation system with robust session management.
* Comprehensive multi-step form workflow from project details to review and production.
* Production-ready, schema-driven form builder with a live field editor and configurable pricing rules.
* **Inline Builder Integration**:
  * `_builder_macros.html` — Jinja2 macros (`render_question_palette`, `render_properties_panel`, `render_canvas_content`)
  * `form.html` — conditionally renders builder sidebar when `edit_mode` is True
  * `builder.js` — drag-and-drop, block CRUD, undo/redo, properties panel
  * `QMapp.py` `index` route — `edit_mode` branch fully wired + **FIXED missing `edit_requested`/`edit_mode` local vars (03/06/26)**
  * `QMapp.py` `special_notes_page` — copy-paste bug FIXED (`build_page_schema_context` now passes `'special_notes_page'`)
  * `QMapp.py` `summary_page` — `edit_mode` branch fully wired
  * **Step 1: Sidebar Swap in `index.html`** ✅ **DONE (04/06/26)**: Added `{% if edit_mode %}` / `{% else %}` conditional around the sidebar nav block. In edit-mode branch: renders question palette via `render_question_palette(builder_state)`, page selector list from `builder_state.pages`, "+ Add Question" button, Exit Edit Mode button. Normal mode preserved. Sidebar gets `.builder-edit-mode` CSS class when in edit mode.
* **Git Infrastructure Upgraded (03/06/26)**: Obsolete Heroku remote scrubbed. Local tracking branch successfully synchronized and pushed up to GitHub `origin master` (510 objects).
* **End-to-End Smoke Test Complete**: Successfully tested all 7 app routes with `?edit=1` parameter. Verified that the inline builder appears correctly on each page, and that drag-and-drop functionality, property checkboxes, and save states work consistently across all pages.

## Immediate Next Blocker / Task
1. ~~**Fix unclosed `<form>` tag in `form.html` edit_mode block**~~ ✅ **DONE (03/06/26)**
2. ~~**Extend edit_mode to remaining routes**~~ ✅ **DONE (03/06/26)**
3. ~~**CSS checkbox audit**~~ ✅ **DONE (03/06/26)**
4. ~~**Fix `index` route missing local `edit_mode` variable**~~ ✅ **DONE (03/06/26)**
5. ~~**Fix Jinja2 `unexpected char '\\'` compiler crash**~~ ✅ **DONE (03/06/26)**
6. ~~**End-to-End Smoke Test of Inline Builder**~~ ✅ **DONE (03/06/26)**
7. ~~**Step 1 — Sidebar Swap in `index.html`**~~ ✅ **DONE (04/06/26)**
   - Added `{% if edit_mode %}` / `{% else %}` conditional around the sidebar nav block
   - In edit-mode branch: renders question palette (`render_question_palette`), page selector (from `builder_state.pages`), "+ Add Question" button, Exit Edit Mode button
   - In normal mode: existing page navigation links preserved
   - Sidebar div gets `.builder-edit-mode` CSS class when in edit mode
8. **Next: Step 2 — Remove Duplicate Builder Sidebar from `form.html`**
   - Remove `<div class="builder-sidebar">` block from `.builder-container` in `app/templates/form.html`
   - The `.builder-container` will then only contain `.builder-canvas` and `.builder-properties`

## Known Issues
* `QMapp.py` is very large (~4500 lines). Use **small, precise `replace_in_file` search blocks** (2-3 lines) to avoid mismatches.
* Port 5000 is hijacked by macOS AirPlay Receiver — use port 5002+ for local testing.

## Session History (04/06/26)
* **Step 1 Complete**: Implemented sidebar swap in `index.html`. The main sidebar now conditionally renders builder palette and controls when `edit_mode` is True, or the standard page navigation links when not in edit mode. Uses `render_question_palette` macro from `_builder_macros.html`, page selector iterating `builder_state.pages`, and a "+ Add Question" button. Exit Edit Mode button navigates to index without `?edit=1` parameter.
* **Template Resolution**: Manually hotfixed line 58 in `_builder_macros.html`. Swapped `join("\n")` to single quotes `join('\n')` to fix the underlying backslash text character escaping issue that was causing 500 errors on 6 out of 7 application routes.
* Fixed `form.html` unclosed `{% if edit_mode %}` at line 28 — added closing `{% endif %}` after normal form rendering block.
* Fixed `form.html` import path: `._builder_macros.html` → `_builder_macros.html` (stray leading dot).
* Test server running on port 5003 with `QM_TEST_MODE=1`. Login succeeds (admin/admin123).
* Committed: `fix: repair form.html template syntax — unclosed {% if edit_mode %} and _builder_macros import path` (4 files, a4cf68e)
* Initialized the Layered Memory System.
* Implemented core drag-and-drop form builder; debugged CSRF, Jinja2 filter errors, server issues.
* Created `_builder_macros.html`, `builder.js`; refactored `form.html` and `builder_beta.html`.
* Integrated `edit_mode` into `index`, `special_notes_page`, `summary_page` routes.
* Fixed `special_notes_page` copy-paste bug (`build_page_schema_context` page_id).
* **Workspace restructured** — git repo root moved to `app/` directory, branch renamed `master`.
* **Remote Cleaned** — Removed obsolete Heroku remote pointers. Configured and validated global `origin` link to GitHub repository to securely sync all session logs moving forward.
* **Smoke Test Complete**: Successfully tested all 7 app routes with `?edit=1` parameter. Verified that the inline builder appears correctly on each page.