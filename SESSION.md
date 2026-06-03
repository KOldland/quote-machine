# Active Sprint Handoff

## Workspace Structure (Updated 03/06/26)
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/` — all git commands must be run from here
* **Branch**: `master`
* **Remote**: `heroku` → `https://git.heroku.com/quote-machine.git`
* **Context archive**: `app/context_archive/` (old .md docs archived here)
* **No GitHub `origin` remote** — push target is Heroku only

## Current Goal
* Integrate the form builder into existing pages as an inline sidebar, replacing the standalone `/builder_beta` page. Admin users see an "Edit Page" button; clicking it stays on the same page but replaces the sidebar with the builder editor (question palette + block properties panel).

## Active Files for Context
All paths are relative to the VS Code workspace root (`QM_web_app/`):
* `app/QMapp.py`
* `app/templates/form.html`
* `app/templates/_builder_macros.html`
* `app/static/js/builder.js`
* `app/static/css/main.css`
* `app/templates/builder_beta.html`

## What Works
* Flask-based quote generation system with robust session management.
* Comprehensive multi-step form workflow from project details to review and production.
* Production-ready, schema-driven form builder with a live field editor and configurable pricing rules.
* **Inline Builder Integration**:
  * `_builder_macros.html` — Jinja2 macros (`render_question_palette`, `render_properties_panel`, `render_canvas_content`)
  * `form.html` — conditionally renders builder sidebar when `edit_mode` is True
  * `builder.js` — drag-and-drop, block CRUD, undo/redo, properties panel
  * `QMapp.py` `index` route — `edit_mode` branch fully wired
  * `QMapp.py` `special_notes_page` — copy-paste bug FIXED (`build_page_schema_context` now passes `'special_notes_page'`)
  * `QMapp.py` `summary_page` — `edit_mode` branch fully wired

## Immediate Next Blocker / Task
1. ~~**Fix unclosed `<form>` tag in `form.html` edit_mode block**~~ ✅ **DONE (03/06/26)**
2. ~~**Extend edit_mode to remaining routes**~~ ✅ **DONE (03/06/26)** — Added `if edit_mode: ... return render_template(..., builder_state=..., current_page=...) / return render_template(...)` pattern to `materials_page`, `further_requirements_page`, `additional_costs_page`, `image_upload_page`.
3. **CSS checkbox audit**: `main.css` has `.hidden-checkbox { display: none; }` — verify no global rule is clipping builder sidebar checkboxes.
4. **Fix `index` route missing local `edit_mode` variable** — `index` route uses `if edit_mode:` but never computes `edit_requested`/`edit_mode` locally (context_processor injects it into templates but Python function body needs it as a local var). Add `edit_requested`/`edit_mode` lines before the `if edit_mode:` block in `index`.

## Known Issues
* `QMapp.py` is very large (~4500 lines). Use **small, precise `replace_in_file` search blocks** (2-3 lines) to avoid mismatches.
* Git remote is Heroku only. No GitHub `origin` — do not attempt `git push origin`.

## Session History
* Initialized the Layered Memory System.
* Implemented core drag-and-drop form builder; debugged CSRF, Jinja2 filter errors, server issues.
* Created `_builder_macros.html`, `builder.js`; refactored `form.html` and `builder_beta.html`.
* Integrated `edit_mode` into `index`, `special_notes_page`, `summary_page` routes.
* Fixed `special_notes_page` copy-paste bug (`build_page_schema_context` page_id).
* **Workspace restructured** — git repo root moved to `app/` directory, branch renamed `master`, Heroku-only remote. SESSION.md updated to reflect new layout.
