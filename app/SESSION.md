# Active Sprint Handoff

## Workspace Structure
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session AI/AJ — COMPLETE: Formalize Pages and Categories in Schema ✅**

## Active Files for Context (next session)
* @app/template_store.py
* @app/QMapp.py
* @app/templates/_builder_macros.html
* @app/static/js/builder.js

## What Was Completed — Session AJ (Part 2)
* **Backend Endpoint:** Built the unified atomic SQL swap endpoint (`/builder_beta/swap_order`) in `QMapp.py` handling `page`, `category`, and `question` scopes using strict neighbor lookup queries.
* **Schema IDs:** Updated `_get_li_categories_from_schema` and `builder_line_items_json` to supply the actual integer `id` from the database to track category scope instead of string names.
* **UI Controls:** Added Up/Down (▲/▼) buttons next to categories and questions in `_builder_macros.html` and wired them to the `/builder_beta/swap_order` endpoint using AJAX.

## Immediate Next Blocker
### Session AK — Page Ordering UI & Further Builder Refinements
1. Build the UI to display and reorder the high-level Pages using the new swap endpoint logic.
2. Create native creation and persistence mechanisms for adding new Pages and Categories via the UI.
