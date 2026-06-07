# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session Q: Smoke Test** — Refactor of `further_requirements_page` complete. Smoke test all pages end-to-end.

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/page_schemas.json
* @app/scripts/sync_schemas.py
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session P**: Refactored `summary_page` to unified schema-driven handler. Removed legacy session-handling code.
* **Session P (fix)**: Ran `sync_schemas.py` to sync `template_store.sqlite3` with `page_schemas.json` — fixes `special_notes_page` 3-column render (commit `62533cb`).
* **Session Q (partial)**: Refactored `materials_page` — removed 231 lines of legacy dead code, replaced with slim unified handler using `compile_builder_beta_page_to_runtime_schema` + `persist_schema_page_submission` (commit `5f676d3`). File compiles cleanly (EXIT:0).
* **Session Q (complete)**: Refactored `further_requirements_page` — removed 224 lines of legacy session-handling code, replaced with 17-line slim unified handler. py_compile EXIT:0 confirmed. Used write-to-temp-script pattern to avoid shell quote escaping issues.

## Exact Stopping Point
* `further_requirements_page` refactored and committed. Smoke test not yet run.

## Immediate Next Task (start here on reopen)
### Session Q — Smoke Test

Run smoke test: Start server with `env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003 --with-threads` and verify all pages render with the 3-column editor:
- `special_notes_page`
- `summary_page`
- `materials_page`
- `further_requirements_page`
- `additional_building_work_page`
- `optional_extras_page`

Use `app/scripts/smoke_routes.py` if available for automated route checking.

### Known Potential Issues to Watch
* If `li_categories` is an empty list, canvas falls back to legacy block builder — by design
* Jinja2 deprecation: `opt_pricing.get(...)` calls in `form.html` require Jinja2 ≥ 3.0
* CSRF token: JS reads `document.querySelector('[name=csrf_token]')` — works because hidden input is injected at top of 3-col canvas
* **Never use `replace_in_file` on `QMapp.py`** — use write-to-temp-script pattern instead (see `context.md` Agent Pitfalls)
* **Shell quote escaping**: Never use `python3 -c "..."` for multiline edits — always write a temp `.py` script file and execute it
