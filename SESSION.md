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
* **Session I**: Mapped the new V2 CSV to the DB hierarchy. Updated `migrate_line_items_from_csv.py` to ingest the new V2 CSV data structure. Removed old standalone block builder UI and enforced strict User Mode and Edit Mode via inline sidebar.

## Exact Stopping Point
* Completed Session I goals.

## Immediate Next Task (start here on reopen)
### Session J: Next Steps
1. Review and refine any remaining issues with the new database-driven unified hierarchy.
2. Clean up removed standalone builder routes (e.g., `/form_builder_demo`) and fix/remove deprecated test cases in `test_submit_production.py` and `ui_regression.sh` since the standalone builder was removed in Session I.
