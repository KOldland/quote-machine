# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* Accordion Hierarchy Sprint — **Phase 2: Sub-question Discovery & Migration**. Auditing `form.html` and `QMapp.py` for hardcoded sub-questions; migrating them into `sub_blocks[]` in the schema.

## Active Files for Context
* @app/page_schemas.json
* @app/page_schemas_published.json
* @app/scripts/migrate_accordion_schema.py
* @app/QMapp.py
* @app/templates/form.html
* @app/static/js/builder.js
* @app/templates/_builder_macros.html
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed

### Previous sessions
* **All 10 CRUD checklist items** ✅ — CLEAR as of `978edf6`
* **P1 Sidebar collapse in edit mode** ✅ — commit `66abfb9`
* **P2 Select Page width + arrow direction** ✅ — commit `2852f49`
* **Accordion Hierarchy architectural analysis** ✅ — 4-phase plan written

### This session (05/06/26)
* **Phase 1 — Schema Migration** ✅ — `scripts/migrate_accordion_schema.py` written and run. 17 `checkbox_group` blocks with `source_prefix` promoted to `accordion_group` with `sub_blocks: []` in both `page_schemas.json` and `page_schemas_published.json`. — commit `07a9811`

## Known Issues / Bug Backlog
* None — all prior bugs resolved. Active sprint is a feature build.

## Immediate Next Task (start here on reopen)

### 🚀 Phase 2 — Sub-question Discovery & Migration

Full spec in `@app/.continue/prompts/current_development.md` → Phase 2 section.

1. Audit `app/templates/form.html` and `app/QMapp.py` for hardcoded sub-question fields logically nested inside an accordion section (e.g. Metres/Centimetres inside External Walls)
2. Add discovered sub-questions to the relevant `sub_blocks[]` in `page_schemas.json`
3. Update Jinja rendering to read `sub_blocks` from schema rather than hardcoded HTML
4. Verify front-end form still renders and submits correctly

**Do NOT change** `builder.js` or the builder canvas in Phase 2.

## Session Log
| Date | Items | Result |
|------|-------|--------|
| 05/06/26 | CRUD #1–10 | All CLEAR |
| 05/06/26 | P1 Sidebar collapse | FIXED — `66abfb9` |
| 05/06/26 | P2 Select Page width + arrow | FIXED — `2852f49` |
| 05/06/26 | Accordion analysis | 4-phase plan written |
| 05/06/26 | Phase 1 schema migration | ✅ COMPLETE — `07a9811` |
