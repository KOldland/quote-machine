# Active Sprint Handoff

## Current Goal
* Integrate the form builder into existing pages as an inline sidebar, replacing the standalone `/builder_beta` page. Admin users see an "Edit Page" button; clicking it stays on the same page but replaces the sidebar with the builder editor (question palette + block properties panel).

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/templates/_builder_macros.html (NEW)
* @app/static/js/builder.js (NEW)
* @app/templates/builder_beta.html

## What Works
* Flask-based quote generation system with robust session management.
* Comprehensive multi-step form workflow from project details to review and production.
* Production-ready, schema-driven form builder with a live field editor and configurable pricing rules.
* **New Inline Builder Integration**:
  * `_builder_macros.html` created with reusable Jinja2 macros (`render_question_palette`, `render_properties_panel`, `render_canvas_content`)
  * `form.html` updated to conditionally render the builder sidebar when `edit_mode` is True, importing the macros
  * `builder_beta.html` simplified to extend index.html and use the canvas macro only
  * `builder.js` created with full drag-and-drop, block CRUD operations, undo/redo, properties panel management, and keyboard shortcuts
  * `app/QMapp.py` `index` route updated with `edit_mode` support
  * `app/QMapp.py` `special_notes_page` route: copy-paste bug FIXED — `build_page_schema_context` now correctly passes `'special_notes_page'` instead of `'summary_page'`
  * `app/QMapp.py` `special_notes_page` route: `edit_mode` branch fully wired
  * `app/QMapp.py` `summary_page` route: `edit_mode` branch fully wired (confirmed present and correct)

## Immediate Next Blocker / Task
1. **Checkbox visibility**: User reported checkboxes are not visible in the builder sidebar. Investigate CSS in `_builder_macros.html` and `form.html` for checkbox styling — likely a z-index or display issue within the sidebar panel.
2. **Extend edit_mode to remaining routes**: `materials_page`, `further_requirements_page`, `additional_costs_page`, `image_upload_page`, etc. all need the same `if edit_mode: ... else: ...` pattern applied.
3. **SESSION.md accuracy review**: User flagged possible corruption in this file — re-validate the blocker list against actual code state at start of next session.

## Known Issues
* Repeated `replace_in_file` failures on `app/QMapp.py` due to search block mismatches — the file is very large (~4500 lines). Prefer **smaller, more precise search blocks** (2-3 lines) or use `write_to_file` for large changes.

## Session History
* Initialized the Layered Memory System. Old chat histories cleared to optimize token budgets and prevent IDE lag.
* Implemented the core visual drag-and-drop form builder in `app/templates/builder_beta.html` and integrated backend routes in `app/QMapp.py`.
* Debugged and resolved CSRF token issues, Jinja2 template assertion errors (`No filter named 'keys'`), and server connection issues to make the new builder fully accessible and functional on `http://127.0.0.1:5052/builder_beta`.
* **Previous session**: Created `_builder_macros.html`, `builder.js`, refactored `form.html` and `builder_beta.html`, and began integrating `edit_mode` into `app/QMapp.py` routes.
* **Current session**: Fixed copy-paste bug in `special_notes_page` — `build_page_schema_context` was incorrectly passing `'summary_page'` instead of `'special_notes_page'`. Confirmed `summary_page` edit_mode branch is already fully wired.
