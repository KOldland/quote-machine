# Migration to 3-Column Editor

This document tracks the migration of legacy form pages to the new 3-column editor.

## Migration Status

- [x] `special_notes_page`
- [x] `summary_page` (Refactored backend/frontend for unification)
- [x] `additional_building_work_page`
- [x] `optional_extras_page`
- [x] Unified schema-driven rendering in `form.html`
- [x] `materials_page` — legacy session-handling code removed; refactored to slim unified handler using `compile_builder_beta_page_to_runtime_schema` + `persist_schema_page_submission` (commit `5f676d3`)
- [x] `further_requirements_page` — legacy session-handling removed; refactored to 17-line slim unified handler. 224 lines removed. py_compile EXIT:0. (commit `d7d6831`, Session Q)
- [x] `additional_costs_page` — GET path refactored to slim schema-driven handler. POST pricing logic preserved. 124 lines removed. (commit `83143a9`, Session S)

## DB Sync
- [x] `template_store.sqlite3` synced with `page_schemas.json` via `sync_schemas.py` (commit `62533cb`) — fixes `special_notes_page` 3-column render
- [x] `additional_costs_page` content migration — 206 line items re-tagged from legacy numeric `form_page` values to `'additional_costs_page'`; category names normalised (skylights→Skylights, velux→Velux, etc.); `line_items_by_category` block added to schema (commit `f30507c`, Session S)
- [x] `summary_page` content migration — Planning Permission (8 items, `pp%`) + Council (3 items, `cs%`) re-tagged from legacy `form_page='2'` to `'summary_page'`; category case normalised to title case matching schema (commit `76e0912`, Session T)

## Agent Tooling Fix
- [x] `context.md` updated with "Never Use replace_in_file on Large Files" pitfall — safe Python one-liner alternatives documented
- [x] `context.md` updated with shell quote escaping pitfall — never use `python3 -c "..."` for multiline edits; always write a temp `.py` script file and execute it

## Bug Fixes
- [x] `UndefinedError: 'current_page'` on `materials_page` + `further_requirements_page` when admin hits `?edit=1` — both slim handlers updated with full edit-mode branch passing `current_page`/`li_categories` (commit `5dc7c0b`, Session R)

## Smoke Test
- [x] Smoke test passed — all 7 refactored pages return 200/302. Zero 500 errors. (commit `3df127c`, Session R)

## Remaining
- [x] `summary_page` question audit — Planning Permission + Council confirmed visible after migration (Session T)
- [x] `materials_page` question audit — 42 items across 8 categories migrated from `form_page='3'`; `Internal Doors` case fix; 4 stray `dm%` rows normalised. Verified via DB count (commit `170d20f`, Session U).
- [x] `further_requirements_page` question audit — dw% (9 items) + frc% (53 items) migrated from form_page='3B'; schema block already correct (commit `70542f0`, Session V)
- [ ] `additional_building_work_page` question audit — not yet done
- [ ] `optional_extras_page` question audit — not yet done

## UI Fixes
- [x] `.li-3col-canvas` viewport gap — swapped fixed `height` for `min-height: 400px` + `max-height: calc(100vh - 120px)` (commit `258ff27`, Session V)
- [x] Long list overflow cap — `min-height:0` on flex columns + direct `max-height: calc(100vh - 170px)` on `#li-question-list` (commit `47de853`, Session V)
