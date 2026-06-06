# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session M: Verify + Stabilise 3-Column Canvas** — Boot the server, confirm `/materials_page?edit=1` and `/further_requirements_page?edit=1` render the 3-column canvas, click through the section list, View One question list, and View Two editor; fix any rendering issues found.

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/templates/_builder_macros.html
* @app/static/js/builder.js
* @app/template_store.py
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session K**: Cleaned up deprecated standalone builder routes in `QMapp.py`. All tests pass. Committed as `bf9d5ea`.
* **Session L**: Full 3-column line-item editor canvas implemented. Committed as `6afd05c`.
  - `QMapp.py`: `/builder_beta/line_items_json` now accepts `?page=` and `?category=` query params; `materials_page` and `further_requirements_page` edit_mode renders pass `form_page_key` + `li_categories` to template
  - `_builder_macros.html`: two new macros — `render_li_sections_panel` (col 1 category nav) + `render_li_question_panel` (col 2 with full JS state machine: View One question list, View Two 5-tab editor with CSRF-aware save, Back button)
  - `form.html`: edit_mode block now branches — 3-col canvas when `li_categories` is set, otherwise falls through to legacy schema block builder

## Exact Stopping Point
* All Session L code committed (`6afd05c`). Server **not yet started** — canvas behaviour **not yet verified** in the browser.
* The `line_items` table needs at least one row with `form_page='3'` or `form_page='3B'` for categories to appear in the sections panel.

## Immediate Next Task (start here on reopen)
### Session M — Verify & Stabilise
1. Start Flask in test mode: `QM_TEST_MODE=1 python3 QMapp.py` (or `bash start_flask.sh`)
2. Login as admin, navigate to `/materials_page?edit=1`
3. Confirm 3-column canvas renders (sections panel on left, empty state in question panel)
4. Click a section button → confirm View One question list populates via XHR
5. Click a question row → confirm View Two editor shows with correct field values
6. Edit a field, click SAVE → confirm `line_item_save/<id>` POST returns `{"ok": true}` and View Two title updates
7. Click Back → confirm View Two collapses, View One re-renders the cached list
8. Fix any CSS/JS issues found, commit as `fix(SessionM):`

### Known Potential Issues to Watch
* If `li_categories` is an empty list (no `line_items_by_category` block configured in `page_schemas.json`), the canvas will show the legacy block builder — not a bug, by design
* Jinja2 deprecation: `opt_pricing.get(...)` calls in `form.html` require Jinja2 ≥ 3.0 (mapping `.get()` method)
* CSRF token: JS reads `document.querySelector('[name=csrf_token]')` — works because `<input type="hidden" name="csrf_token">` is injected at top of 3-col canvas
