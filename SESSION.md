# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* Accordion Hierarchy Sprint — Phase 1: Schema Migration. Restoring the missing two-level structure (accordion container → sub-questions) across schema, builder canvas, and builder interactions.

## Active Files for Context
* @app/page_schemas.json
* @app/page_schemas_published.json
* @app/scripts/migrate_accordion_schema.py  ← to be created
* @app/QMapp.py
* @app/templates/form.html
* @app/static/js/builder.js
* @app/templates/_builder_macros.html
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed (05/06/26 — Session Closeout)
* **Architectural analysis** ✅ — Identified that `checkbox_group + source_prefix` blocks are accordion containers in the front-end but treated as flat blocks in the builder. Two hierarchy layers collapsed into one. Full 4-phase plan documented.
* **current_development.md archived** ✅ — Previous CRUD testing sprint saved as `current_development_comp2.md`. New `current_development.md` written with Accordion Hierarchy Sprint plan.
* **SESSION.md updated** ✅ — Reflects new sprint goal and Phase 1 entry point.
* **All previous P1/P2 bugs** ✅ — Sidebar collapse, Select Page width/arrow all resolved in prior sessions (commits `2852f49`, `66abfb9`).
* **All 10 CRUD checklist items** ✅ — CLEAR as of `978edf6`.

## Known Issues / Bug Backlog
* None — all prior bugs resolved. New sprint is a feature build, not a bug fix.

## Immediate Next Task (start here on reopen)

### 🚀 Phase 1 — Schema Migration (data only, no UI change)

Full spec in `@app/.continue/prompts/current_development.md` → Phase 1 section.

1. Write `app/scripts/migrate_accordion_schema.py`:
   - Read `page_schemas.json`
   - For every block in every page where `standard.source_prefix` is non-empty, set `block_type = "accordion_group"` and add `"sub_blocks": []`
   - Write updated data back to both `page_schemas.json` AND `page_schemas_published.json`
   - Script must be idempotent (safe to re-run)
2. Run the script: `cd app && python3 scripts/migrate_accordion_schema.py`
3. Start Flask (`env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003 --with-threads`) and verify all 9 pages load without 500 errors
4. Commit: `feat: Phase 1 — promote source_prefix blocks to accordion_group type in schema`

**Do NOT change** `form.html`, `QMapp.py` routes, or `builder.js` in Phase 1.

## Session Log Summary
| Date | Items | Result |
|------|-------|--------|
| 05/06/26 | #1–5, #7 | All CLEAR |
| 05/06/26 | #6, #8, #10 | All CLEAR |
| 05/06/26 | #9 | BUG — sidebar collapse broken in edit mode |
| 05/06/26 | P2 Select Page width + arrow direction | FIXED — commit `2852f49` |
| 05/06/26 | P1 Sidebar collapse in edit mode | FIXED — commit `66abfb9` |
| 05/06/26 | Accordion Hierarchy analysis | DONE — 4-phase plan written, Phase 1 ready to execute |
