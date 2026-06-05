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

### ✅ Phase 1 COMPLETE — Schema Migration (data only, no UI change)

- `app/scripts/migrate_accordion_schema.py` written and run — 17 blocks promoted to `accordion_group` in both `page_schemas.json` and `page_schemas_published.json`. All have `sub_blocks: []`. Committed `feat: Phase 1 — promote source_prefix blocks to accordion_group type in schema`.

### 🚀 Phase 2 — Sub-question Discovery & Migration (schema + template audit)

Full spec in `@app/.continue/prompts/current_development.md` → Phase 2 section.

1. Audit `app/templates/form.html` and `app/QMapp.py` for any hardcoded sub-question fields logically nested inside an accordion section (e.g. Metres/Centimetres inside External Walls)
2. Add discovered sub-questions to the relevant `sub_blocks[]` in `page_schemas.json`
3. Update Jinja template rendering to read `sub_blocks` from schema rather than hardcoded HTML
4. Verify front-end form still renders and submits correctly

**Do NOT change** `builder.js` or the builder canvas in Phase 2.

## Session Log Summary
| Date | Items | Result |
|------|-------|--------|
| 05/06/26 | #1–5, #7 | All CLEAR |
| 05/06/26 | #6, #8, #10 | All CLEAR |
| 05/06/26 | #9 | BUG — sidebar collapse broken in edit mode |
| 05/06/26 | P2 Select Page width + arrow direction | FIXED — commit `2852f49` |
| 05/06/26 | P1 Sidebar collapse in edit mode | FIXED — commit `66abfb9` |
| 05/06/26 | Accordion Hierarchy analysis | DONE — 4-phase plan written, Phase 1 ready to execute |
