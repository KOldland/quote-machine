# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session R: Smoke Test** — All legacy routes refactored. Smoke test all 6 pages end-to-end.

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/page_schemas.json
* @app/scripts/smoke_routes.py
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session P**: Refactored `summary_page` to unified schema-driven handler (commit `62533cb`).
* **Session Q**: Refactored `materials_page` — 231 lines removed (commit `5f676d3`).
* **Session Q (complete)**: Refactored `further_requirements_page` — 224 lines of legacy session-handling removed, replaced with 17-line slim unified handler. py_compile EXIT:0 (commit `d7d6831`).
* **Tooling**: Added shell quote escaping pitfall to `context.md` — always write temp `.py` script file instead of `python3 -c "..."`.

## Exact Stopping Point
* All 6 target pages refactored. Smoke test not yet run. Session closed due to token bloat.

## Immediate Next Task (start here on reopen)
### Session R — Smoke Test

1. Start server: `env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003 --with-threads`
2. Verify all pages render with 3-column editor:
   - `special_notes_page`
   - `summary_page`
   - `materials_page`
   - `further_requirements_page`
   - `additional_building_work_page`
   - `optional_extras_page`
3. Use `app/scripts/smoke_routes.py` for automated route checking if available.

### Known Potential Issues to Watch
* If `li_categories` is empty, canvas falls back to legacy block builder — by design
* Jinja2 deprecation: `opt_pricing.get(...)` in `form.html` requires Jinja2 ≥ 3.0
* CSRF token: JS reads `document.querySelector('[name=csrf_token]')` — works via hidden input at top of 3-col canvas
* **Never use `replace_in_file` on `QMapp.py`** — use write-to-temp-script pattern (see `context.md`)
* **Shell quote escaping**: Never `python3 -c "..."` for multiline edits — write a temp `.py` file and execute it
