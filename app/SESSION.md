## Current Goal
* **Quote Engine — Phase 0 complete: schema + CRUD for quotes, line items, adjustments. Phase 1 (output group mapping) next.**
## Completed Tasks This Session
* Wired up SAVE FORM DETAILS persistence in Form Editor view.
* Added Save Form As UI modal with dynamic duplication generation across the database linking `page_templates`, `category_templates`, and generating native `Q_xxxx` UUIDs for `line_items`.
* Corrected SQL schema conflicts around `sort_order` -> `display_order` during duplicate executions.
* Plumbed a completely new auto-switch context using a newly created `switch_form` route to handle session injection with Toast feedback upon saving to let a user remain entirely locked into the active state.
* Built full DB-stripping Delete Form routine dropping down to tables linked to the deleted key.
* Cleaned left sidebar: deprecated "Publish" in place of "Load Form" session switcher.
* **Phase 0 — Quote Schema + CRUD:**
  - Added `allow_user_override` (INTEGER DEFAULT 0) and `output_group` (TEXT DEFAULT 'General') columns to `line_items` table.
  - Created `quotes`, `quote_line_items`, and `quote_adjustments` tables in `_create_schema()`.
  - Added CRUD functions: `create_quote`, `save_quote_line_items`, `save_quote_adjustments`, `update_quote_totals`, `get_quote`, `list_quotes`, `delete_quote`.
  - Migrated live `template_store.sqlite3` database with new tables.

## Immediate Next Task
* **Phase 1: Output Group Mapping** — Backfill `output_group` from category/prefix patterns, wire into `/builder_beta/line_item_save` endpoint, add UI field in Form Editor.
* **Phase 2: Calculator Engine** — Create `app/calculator.py` with `calculate_quote()` function.
## Active Files for Context
* @app/templates/form.html
* @app/templates/index.html
* @app/QMapp.py
* @app/template_store.py
* @app/SESSION.md
* @app/.continue/prompts/calculator.md

