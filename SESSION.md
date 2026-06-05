# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* Accordion Hierarchy Sprint — restoring the missing two-level structure (accordion container → sub-questions) across schema, builder canvas, and builder interactions.

## Active Files for Context
* @app/static/js/builder.js
* @app/templates/_builder_macros.html
* @app/templates/index.html
* @app/templates/form.html
* @app/static/css/main.css
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed (05/06/26 — Bug Squash Sprint)
* **P2 — Select Page width** ✅ — Removed `margin: 5px` horizontal bleed + `calc(100% - 10px)`; now `width: 100%` with vertical-only margin. Matches Add Question / Publish / Undo / Exit buttons exactly. Commit `2852f49`.
* **P2 — Select Page arrow direction** ✅ — `▼` when collapsed (`rotate(0deg)`), `▲` when expanded (`rotate(180deg)`). Commit `2852f49`.
* **P1 — Sidebar collapse in edit mode** ✅ — Root cause: `.sidebar.builder-edit-mode { min-width: 220px }` overrode `width: 0`. Fixed by adding `.sidebar.builder-edit-mode.collapsed` override with `width: 0 !important; min-width: 0 !important`. Commit `66abfb9`.
* **Testing checklist item #9** ✅ — Sidebar collapse/expand now works in both normal and edit modes. All 10 checklist items are now CLEAR.

## Known Issues / Bug Backlog
* None — all P1 and P2 bugs from the CRUD testing sprint resolved.

## Immediate Next Task (start here on reopen)

### 🚀 Accordion Hierarchy Sprint — Phase 1: Schema Migration

Full plan is in `@app/.continue/prompts/current_development.md`.

**Start here:**
1. Read `current_development.md` Phase 1 spec
2. Write `app/scripts/migrate_accordion_schema.py` — promotes any block with `standard.source_prefix` to `block_type: "accordion_group"` + adds `"sub_blocks": []`; updates both `page_schemas.json` and `page_schemas_published.json`
3. Run the migration script and verify app loads all 9 pages without errors
4. Commit: `feat: Phase 1 — promote source_prefix blocks to accordion_group type in schema`

**Do NOT change** `form.html`, `QMapp.py` routes, or `builder.js` in this phase — data migration only.

## Session Log Summary
| Date | Items | Result |
|------|-------|--------|
| 05/06/26 | #1–5, #7 | All CLEAR |
| 05/06/26 | #6, #8, #10 | All CLEAR |
| 05/06/26 | #9 | BUG — sidebar collapse broken in edit mode |
| 05/06/26 | P2 Select Page width + arrow direction | FIXED — commit `2852f49` |
| 05/06/26 | P1 Sidebar collapse in edit mode | FIXED — commit `66abfb9` |
