# Migration to 3-Column Editor

This document tracks the migration of legacy form pages to the new 3-column editor.

## Migration Status

- [x] `special_notes_page`
- [x] `summary_page` (Refactored backend/frontend for unification)
- [x] `additional_building_work_page`
- [x] `optional_extras_page`
- [x] Unified schema-driven rendering in `form.html`
- [x] `materials_page` — legacy session-handling code removed; refactored to slim unified handler using `compile_builder_beta_page_to_runtime_schema` + `persist_schema_page_submission` (commit `5f676d3`)
- [ ] `further_requirements_page` — still uses legacy session-handling; refactor pending (Session Q)

## DB Sync
- [x] `template_store.sqlite3` synced with `page_schemas.json` via `sync_schemas.py` (commit `62533cb`) — fixes `special_notes_page` 3-column render

## Agent Tooling Fix
- [x] `context.md` updated with "Never Use replace_in_file on Large Files" pitfall — safe Python one-liner alternatives documented
