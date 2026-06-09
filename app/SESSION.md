# Active Sprint Handoff

## Workspace Structure
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session AI — COMPLETE: Formalize Pages and Categories in Schema ✅**

## Active Files for Context (next session)
* @app/template_store.py
* @app/QMapp.py
* @app/templates/_builder_macros.html
* @app/static/js/builder.js

## What Was Completed — Session AJ (Part 1)
* **Backend Refactor:** Consolidated duplicate `_get_line_items_for_page` definitions in `QMapp.py`.
* **Schema Integration:** Updated data retrieval in both `QMapp.py` and `template_store.py` to query the formal `category_templates` table, ensuring empty categories are preserved and items are strictly sorted by `display_order`.

## Immediate Next Blocker
### Session AJ (Part 2) — Reordering Endpoint & UI Controls
1. Build the unified atomic SQL swap endpoint (`/builder_beta/swap_order`) in `QMapp.py` handling `page`, `category`, and `question` scopes via `display_order` or `sort_order`.
2. Add the Up/Down buttons to the Builder UI in `_builder_macros.html` and wire them up in `builder.js`.
