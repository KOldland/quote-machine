# Active Sprint Handoff
## Workspace Structure
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session AI — COMPLETE: Formalize Pages and Categories in Schema ✅**
* **Session AK — COMPLETE: Bug Fixes & Schema Sync ✅**
* **Session AL — CURRENT: Builder QA & Further Polish**

## Active Files for Context (next session)
* @app/templates/builder_beta.html
* @app/templates/form.html
* @app/static/js/builder.js
* @app/template_store.py
* @app/templates/index.html
* @app/templates/_builder_macros.html
* @app/QMapp.py

## What Was Completed — Session AI (Formalize Pages and Categories in Schema)
* Defined a new table `category_templates` in `template_store.py`.
* Updated the JSON schema to define categories at the page level.
* Integrated the new structure as the source of truth for category existence and ordering.

## What Was Completed — Session AK (Bug Fixes & Schema Sync)
* Fixed `ModuleNotFoundError` in `QMapp.py`.
* Fixed issues with `builder_state` loading and `checkbox_data` arguments.
* Populated `page_templates` table using `force_sync_schema.py`.

## Immediate Next Blocker
1. Project details (index) page should not be in edit view.
2. Still in legacy 'block-view' for Category > questions.
3. Optional Extras page throws an undefined error.
4. The page movement in the sidebar is a) not working and b) ugly - we will have a different approach.
5. There is still no means of creating a category.
6. We have no UI options in category (potentially due to legacy view).