# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session T** — Question audit: verify all 7 refactored pages show their correct questions in the 3-col editor, migrating DB data as needed.

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/page_schemas.json
* @app/template_store.sqlite3
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session R**: Smoke test passed — all pages 200/302. Fixed `UndefinedError: 'current_page'` on `materials_page` + `further_requirements_page` edit mode (commits `3df127c`, `5dc7c0b`).
* **Session S**: Refactored `additional_costs_page` GET path — slim schema-driven handler, POST pricing logic preserved (commit `83143a9`).
* **Session S (content)**: `additional_costs_page` content migration — 206 line items re-tagged from legacy numeric `form_page` to `'additional_costs_page'`; categories normalised; `line_items_by_category` block added to `page_schemas.json` (commit `f30507c`).

## Exact Stopping Point
* `additional_costs_page` 3-col editor is now wired up with 6 categories (Electrics, Plumbing, Skylights, Velux, Aluminium Capping, Sliding Doors) and 206 questions.
* Remaining pages have NOT yet had their DB rows audited — `form_page` column likely still contains legacy numeric values for most pages.

## Immediate Next Task (start here on reopen)
### Session T — Question audit + DB migration per page

Run this to see the full DB state before starting:
```bash
sqlite3 app/template_store.sqlite3 "SELECT form_page, category, COUNT(*) as n FROM line_items GROUP BY form_page, category ORDER BY form_page, category;"
```

For each page below, check that `line_items` rows exist with `form_page = '<page_id>'` and that category names match the `config.categories` array in `page_schemas.json`:
1. `special_notes_page` — likely OK (was migrated in Session P)
2. `summary_page` — audit needed
3. `materials_page` — audit needed
4. `further_requirements_page` — audit needed
5. `additional_building_work_page` — audit needed
6. `optional_extras_page` — audit needed
7. `additional_costs_page` — ✅ DONE (206 items, 6 categories)

**Pattern for fixing missing pages:** write a temp `.py` script (never `python3 -c "..."`), update `form_page` in DB + add `line_items_by_category` block to `page_schemas.json` if missing. Verify in browser at `/<page>?edit=1`.

### Known Pitfalls
* **Never use `replace_in_file` on `QMapp.py`** — use write-to-temp-script pattern
* **Never `python3 -c "..."` for multiline** — write a temp `.py` file
* **`form_page` column uses string values** — legacy rows have numeric strings (`'7'`, `'8'` etc.), new rows use page ID names
* **Category name case must match exactly** between `page_schemas.json` and `line_items.category`
