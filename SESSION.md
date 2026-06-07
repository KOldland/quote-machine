# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session Q: Refactor `further_requirements_page` + Smoke Test** — Refactor the last legacy route to use the unified schema-driven system, then smoke test all pages end-to-end.

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
* **Tooling fix**: Added "Never Use `replace_in_file` on Large Files" pitfall to `context.md` with safe Python one-liner alternatives.

## Exact Stopping Point
* `materials_page` refactored and committed. `further_requirements_page` still uses legacy session-handling — not yet refactored.

## Immediate Next Task (start here on reopen)
### Session Q — Refactor `further_requirements_page` + Smoke Test

1. **Refactor `further_requirements_page`** in `app/QMapp.py`:
   - Find `@app.route('/further_requirements_page'` (currently around line 3009 pre-edit, adjust after materials_page removal)
   - Replace the entire function body with the slim unified pattern:
   ```python
   @app.route('/further_requirements_page', methods=['POST', 'GET'])
   def further_requirements_page():
       page_id = 'further_requirements_page'
       if request.method == 'POST':
           persist_schema_page_submission(page_id, request.form)
           return redirect(url_for('additional_building_work_page'))
       page_schema = compile_builder_beta_page_to_runtime_schema(page_id)
       sheet_data = get_catalog()
       return render_template(
           'form.html',
           page_schema=page_schema,
           schema_render_mode='full',
           previous_page='materials_page',
           next_page='additional_building_work_page',
           title=page_schema.get('title', 'Further Requirements') if page_schema else 'Further Requirements'
       )
   ```
   - **Use the Python line-index one-liner approach** (never `replace_in_file` on QMapp.py — see context.md pitfall).
   - Verify with `python3 -m py_compile app/QMapp.py 2>&1; echo "EXIT:$?"`

2. **Smoke test**: Start server with `env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003 --with-threads` and verify all pages render with the 3-column editor: `special_notes_page`, `summary_page`, `materials_page`, `further_requirements_page`, `additional_building_work_page`, `optional_extras_page`.

### Known Potential Issues to Watch
* If `li_categories` is an empty list, canvas falls back to legacy block builder — by design
* Jinja2 deprecation: `opt_pricing.get(...)` calls in `form.html` require Jinja2 ≥ 3.0
* CSRF token: JS reads `document.querySelector('[name=csrf_token]')` — works because hidden input is injected at top of 3-col canvas
* **Never use `replace_in_file` on `QMapp.py`** — use Python line-index one-liners instead (see `context.md` Agent Pitfalls)
