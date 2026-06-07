# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session S** — Iterative: verify questions showing correctly on all 7 refactored pages.

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/page_schemas.json
* @app/template_store.sqlite3
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session P**: Refactored `summary_page` to unified schema-driven handler (commit `62533cb`).
* **Session Q**: Refactored `materials_page` — 231 lines removed (commit `5f676d3`).
* **Session Q (complete)**: Refactored `further_requirements_page` — 224 lines removed (commit `d7d6831`).
* **Session R**: Smoke test passed — all 6 refactored pages return 200/302. Zero 500 errors (commit `3df127c`).
* **Session R (fix)**: Fixed `UndefinedError: 'current_page'` on `materials_page` + `further_requirements_page` when admin hits `?edit=1` — added full edit-mode branch to both slim handlers (commit `5dc7c0b`).
* **Session S**: Refactored `additional_costs_page` GET path — 124 lines removed, 19 added, slim schema-driven handler. POST pricing calculation logic preserved 100% intact (commit `83143a9`).

## Exact Stopping Point
* All 7 target pages now on unified schema-driven GET handler.
* Next: iteratively verify each page is showing the correct questions in the 3-column editor.

## Immediate Next Task (start here on reopen)
### Session S continued — Question audit per page

For each page below, visit `/<page>?edit=1` as admin and verify questions appear in the 3-col editor:
1. `special_notes_page`
2. `summary_page`
3. `materials_page`
4. `further_requirements_page`
5. `additional_building_work_page`
6. `optional_extras_page`
7. `additional_costs_page`

If questions are missing, the likely cause is either:
- The `line_items` table in `template_store.sqlite3` is missing rows for that page's categories
- The `page_schemas.json` `config.categories` array has a mismatch vs the `category` column in `line_items`

Use `sqlite3 app/template_store.sqlite3 "SELECT page_id, category, COUNT(*) FROM line_items GROUP BY page_id, category;"` to audit.

### Known Potential Issues to Watch
* If `li_categories` is empty, canvas falls back to legacy block builder — by design
* **Never use `replace_in_file` on `QMapp.py`** — use write-to-temp-script pattern (see `context.md`)
* **Shell quote escaping**: Never `python3 -c "..."` for multiline edits — write a temp `.py` file and execute it
