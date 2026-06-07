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
* @app/templates/_builder_macros.html
* @app/page_schemas.json
* @app/template_store.sqlite3
* @app/scripts/migrate_further_requirements_page.py
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session R**: Smoke test passed — all pages 200/302. Fixed `UndefinedError: 'current_page'` on `materials_page` + `further_requirements_page` edit mode (commits `3df127c`, `5dc7c0b`).
* **Session S**: Refactored `additional_costs_page` GET path — slim schema-driven handler, POST pricing logic preserved (commit `83143a9`).
* **Session S (content)**: `additional_costs_page` content migration — 206 line items re-tagged from legacy numeric `form_page` to `'additional_costs_page'`; categories normalised; `line_items_by_category` block added to `page_schemas.json` (commit `f30507c`).
* **Session T**: `summary_page` DB migration — Planning Permission (8 items, `pp%`) + Council (3 items, `cs%`) re-tagged from legacy `form_page='2'` to `'summary_page'`; category case normalised to match schema (commit `76e0912`).
* **Session U**: `materials_page` DB migration — 42 line items across 8 categories (`dr`, `id`, `wp`, `dm`, `er`, `ew`, `fs`, `ps`) re-tagged from legacy `form_page='3'` to `'materials_page'`; `Internal Doors` → `Internal doors` case fix; 4 stray `dm%` rows normalised.
* **Session V**: `further_requirements_page` DB migration — `dw%` (9 items, `Demolition Works`) + `frc%` (53 items, `Further Requirements & Considerations`) re-tagged from legacy `form_page='3B'` to `'further_requirements_page'`; schema block already existed with correct category names (commit `70542f0`).
* **Session V (UI fix)**: `.li-3col-canvas` viewport gap fixed — swapped `height: calc(100vh - 120px)` for `min-height: 400px` + `max-height: calc(100vh - 120px)` (commit `258ff27`). Follow-up: added `min-height:0` to flex columns + direct `max-height: calc(100vh - 170px)` on `#li-question-list` to cap overflow on long lists (commit `47de853`).
* **Session W**: `additional_building_work_page` (51 items, ab%) + `optional_extras_page` (132 items) DB migration complete (commit `5e4d7ba`). Fixed `/?edit=1` crash — index route `edit_mode` forced to `False` since page has no editor UI (commit `85ab737`). Passed `edit_mode=False` + `current_page=None` explicitly to index render (commit `4bca092`).
* **Session X**: Wired `line_items_by_category` to normal form view (commit `405ca00`) — added `_get_line_items_for_page()` helper, `'type': block_type` on all builder_beta field entries, `elif line_items_by_category` branch in `build_builder_beta_runtime_context` + `persist_schema_page_submission`, and accordion rendering block in `form.html`. Fixed `TypeError: string indices must be integers` — replaced unsafe nested listcomp with defensive isinstance-guarded for-loop (commit `a8c1911`).

## Exact Stopping Point
* `additional_costs_page` — ✅ DONE (206 items, 6 categories)
* `summary_page` — ✅ DONE: Planning Permission (8) + Council (3) migrated, verified via DB count
* `materials_page` — ✅ DONE: 42 items, 8 categories migrated from form_page='3'
* `further_requirements_page` — ✅ DONE: 9 dw% + 53 frc% items migrated from form_page='3B'; verified at browser
* `additional_building_work_page` — ✅ DONE: 51 items (ab%) re-tagged from form_page='3C'; category renamed 'Additional Building Items' → 'Additional Building Works' to match schema (Session W)
* `optional_extras_page` — ✅ DONE: 132 items (oe%/op%/ex%) re-tagged from form_page=NULL to 'optional_extras_page'; category 'Optional Extras' already matched schema (Session W)

## Immediate Next Task (start here on reopen)
### Session X — Browser verification + final smoke test

1. Start server: `env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003 --with-threads`
2. Verify all 7 refactored pages show correct questions in 3-col editor:
   - `/additional_building_work_page?edit=1` — expect 51 items under "Additional Building Works"
   - `/optional_extras_page?edit=1` — expect 130 items under "Optional Extras"
   - Spot-check previously migrated pages still show correctly
3. All 7 pages ✅ → Session T goal ("Question audit") complete.

### Known Pitfalls
* **Never use `replace_in_file` on `QMapp.py`** — use write-to-temp-script pattern
* **Never `python3 -c "..."` for multiline** — write a temp `.py` file
* **`form_page` column uses string values** — legacy rows have numeric strings (`'7'`, `'8'` etc.), new rows use page ID names
* **Category name case must match exactly** between `page_schemas.json` and `line_items.category`
* **Flask server on macOS** — never start in background with `&`; always foreground with `env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003 --with-threads`
