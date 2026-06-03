# Active Sprint Handoff

## Workspace Structure (Updated 03/06/26)
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/` — all git commands must be run from here
* **Branch**: `master`
* **Context archive**: `app/context_archive/` (old .md docs archived here)
* **GitHub Repository**: Linked to `https://github.com/KOldland/quote-machine` as primary `origin` remote.

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
  * `QMapp.py` `index` route — `edit_mode` branch fully wired + **FIXED missing `edit_requested`/`edit_mode` local vars (03/06/26)**
  * `QMapp.py` `special_notes_page` — copy-paste bug FIXED (`build_page_schema_context` now passes `'special_notes_page'`)
  * `QMapp.py` `summary_page` — `edit_mode` branch fully wired
* **Git Infrastructure Upgraded (03/06/26)**: Obsolete Heroku remote scrubbed. Local tracking branch successfully synchronized and pushed up to GitHub `origin master` (510 objects).

## Immediate Next Blocker / Task
1. ~~**Fix unclosed `<form>` tag in `form.html` edit_mode block**~~ ✅ **DONE (03/06/26)**
2. ~~**Extend edit_mode to remaining routes**~~ ✅ **DONE (03/06/26)** — Added `if edit_mode: ... return render_template(..., builder_state=..., current_page=...) / return render_template(...)` pattern to `materials_page`, `further_requirements_page`, `additional_costs_page`, `image_upload_page`.
3. ~~**CSS checkbox audit**~~ ✅ **DONE (03/06/26)** — `.hidden-checkbox` class found nowhere in codebase; no clipping risk. Removed from active concerns.
4. ~~**Fix `index` route missing local `edit_mode` variable**~~ ✅ **DONE (03/06/26)** — Added `edit_requested`/`edit_mode` computation before `if edit_mode:` block in `index`, matching all other routes.
5. **Fix Jinja2 `unexpected char '\\' at 2962`** — `form.html` edit_mode JS block contains a stray backslash character causing 500 on 6/7 routes. `image_upload_page` returns 200 (confirmed working). Need to locate the `\` in lines ~1638-1966 and remove it. After fix, re-test all 7 routes end-to-end.

## Known Issues
* `QMapp.py` is very large (~4500 lines). Use **small, precise `replace_in_file` search blocks** (2-3 lines) to avoid mismatches.
* `form.html` has a Jinja2 compilation error (`unexpected char '\\' at 2962`) in the edit_mode JS block — causes 500 on `/`, `/special_notes_page`, `/summary_page`, `/materials_page`, `/further_requirements_page`, `/additional_costs_page`.
* Port 5000 is hijacked by macOS AirPlay Receiver — use port 5002+ for local testing.

## Session History (03/06/26)
* Fixed `form.html` unclosed `{% if edit_mode %}` at line 28 — added closing `{% endif %}` after normal form rendering block.
* Fixed `form.html` import path: `._builder_macros.html` → `_builder_macros.html` (stray leading dot).
* Test server running on port 5003 with `QM_TEST_MODE=1`. Login succeeds (admin/admin123). `image_upload_page?edit=1` returns 200. 6 other routes return 500 due to `unexpected char '\\' at 2962`.
* Committed: `fix: repair form.html template syntax — unclosed {% if edit_mode %} and _builder_macros import path` (4 files, a4cf68e)
* **Next**: locate and remove the stray `\` in the edit_mode JS block (~line 1638-1966) causing Jinja2 `unexpected char` error.
* Initialized the Layered Memory System.
* Implemented core drag-and-drop form builder; debugged CSRF, Jinja2 filter errors, server issues.
* Created `_builder_macros.html`, `builder.js`; refactored `form.html` and `builder_beta.html`.
* Integrated `edit_mode` into `index`, `special_notes_page`, `summary_page` routes.
* Fixed `special_notes_page` copy-paste bug (`build_page_schema_context` page_id).
* **Workspace restructured** — git repo root moved to `app/` directory, branch renamed `master`. 
* **Remote Cleaned** — Removed obsolete Heroku remote pointers. Configured and validated global `origin` link to GitHub repository to securely sync all session logs moving forward.