# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Pivot to Database-Driven Unified Hierarchy (Session J)**: Refine issues post-schema migration, specifically stabilizing test suites after removing the standalone block builder UI.

## Active Files for Context
* @app/QMapp.py
* @app/tests/test_submit_production.py
* @app/scripts/ui_regression.sh
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed Recently
* **Session J**: Resolved `AttributeError` on `/special_notes_page` caused by calling legacy `get_page_schema`. Verified that the new `line_items` schema and migration accurately ingested 1,022 rows from the V2 CSV. Confirmed general smoke tests (`smoke_submit.py`) now pass.

## Exact Stopping Point
* Stopped after identifying that `ui_regression.sh` and `test_submit_production.py` are throwing numerous failures and errors because they still target removed routes (`/form_builder_demo`, `/builder_beta/render/`, etc.) from the deprecated standalone builder UI.

## Immediate Next Task (start here on reopen)
### Session K: Next Steps
1. Clean up deprecated standalone builder routes in `QMapp.py` (e.g. `/form_builder_demo`, `/form_builder_demo/page/<page_id>`, `/builder_beta/render/<page_id>`).
2. Update/remove deprecated test cases in `test_submit_production.py` to reflect the new inline-sidebar architecture and ensure unit tests pass.
3. Fix `ui_regression.sh` to remove checks against deprecated endpoints so automated UI regression passes cleanly.