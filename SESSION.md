# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Pivot to Database-Driven Unified Hierarchy (Session I)**: Move away from standalone block builder and Google Sheets towards a fully database-driven, nested schema architecture mapped to the new V2 CSV.

## Active Files for Context
* @app/scripts/migrate_line_items_from_csv.py
* @app/template_store.py
* @app/QMapp.py
* @app/SESSION.md
* @app/.continue/prompts/current_development.md
* @app/context_archive /Plus Rooms Live input in doc formatting (back up) - Sheet1v2.csv

## What Was Completed Recently
* **Session H**: Added `line_items_by_category` blocks to schemas with pre-seeded categories, updated `QMapp.py` for schema-driven filtering and saving via POST endpoint.

## Exact Stopping Point
* Prepared to begin mapping the new V2 CSV to the DB hierarchy, but have not yet made modifications to the import script or DB schema.

## Immediate Next Task (start here on reopen)
### Session I: Pivot to Database-Driven Unified Hierarchy
1. Map the new CSV (`app/context_archive /Plus Rooms Live input in doc formatting (back up) - Sheet1v2.csv`) headers to the DB schema.
2. Update `migrate_line_items_from_csv.py` to ingest the new V2 CSV data structure, explicitly breaking out description and cost columns.
3. Update UI to enforce strict User Mode and Edit Mode.
