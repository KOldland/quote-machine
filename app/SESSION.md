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
* @force_sync_schema.py

## What Was Completed — Session AK (Page Ordering & Creation)
* **Creation Endpoints & DB Helpers:** Built `add_page` and `add_category` logic using atomic max display order increments in `template_store.py` and exposed them via POST endpoints in `QMapp.py`.
* **Sidebar Page Ordering:** Updated the left-hand navigation sidebar in `index.html` to dynamically render `db_pages` exposed globally via `inject_ui_context`, integrating up/down order manipulation leveraging the `swap_order` API.
* **Builder Canvas UI:** Added Add Category and Add Page prompt-driven JS creation buttons in `_builder_macros.html` and `index.html`.

## What Was Completed — Current Session (Bug Fixes & Schema Sync)
*   **Fixed `ModuleNotFoundError`:** Corrected import statements in `QMapp.py` from `app.template_store` to `template_store`.
*   **Fixed Legacy View/Empty Pages:** Identified and corrected issues with `builder_state` loading from session instead of `get_builder_beta_state()` in `QMapp.py` routes. Also fixed missing `checkbox_data` arguments in `persist_schema_page_submission` calls.
*   **Populated `page_templates` table:** Created and executed `force_sync_schema.py` to insert missing page entries into the `page_templates` table, resolving the issue of only two pages showing in the UI.

## Immediate Next Blocker
### Session AL — Builder QA & Further Polish
1.  Project details (index) page should not be in edit view.
2.  Still in legacy 'block-view' for Category > questions.
3.  Optional Extras page throws an undefined error.
4.  The page movement in the sidebar is a) not working and b) ugly - we will have a different approach.
5.  There is still no means of creating a category.
6.  We have no UI options in category (might be the result of legacy view).