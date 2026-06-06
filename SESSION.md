# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session L: 3-Column Line Item Canvas** — Rebuild Edit Mode canvas with a 3-column layout: Left sidebar (existing) | Canvas Col 1 (sections/categories) | Canvas Col 2 (contextual — question list View One, or question editor View Two).

## Active Files for Context
* @app/QMapp.py
* @app/templates/builder_beta.html
* @app/templates/_builder_macros.html
* @app/static/js/builder.js
* @app/template_store.py
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session K**: Cleaned up deprecated standalone builder routes in `QMapp.py`. Updated `test_submit_production.py` and `ui_regression.sh`. All tests pass. Committed as `bf9d5ea`.
* **Session L planning**: Designed and documented the 3-column Edit Mode canvas architecture. Full plan committed to `current_development.md`.

## Exact Stopping Point
* `current_development.md` updated with Session L full plan (Layout, Data Source, Build Steps, Testing Checklist).
* No code changed yet — all Session L items are pending.

## Immediate Next Task (start here on reopen)
### Session L Build Steps (in order):
1. **L1** — Add two backend API routes to `QMapp.py`:
   - `GET /api/builder/line_items?page=<page_key>` → returns all line_items for that page as JSON, keyed by category
   - `POST /api/builder/line_item/<id>/save` → accepts JSON body with any subset of line_item fields; updates DB row; returns `{"ok": true}`
2. **L2** — Add `render_li_sections_panel()` macro to `_builder_macros.html`: server-renders a list of category buttons (one per category for the page). Active state managed via JS.
3. **L3** — Update `render_li_contextual_panel()` macro: Col 2 wrapper with View One (question list, empty until category clicked) and View Two (question editor, hidden until question clicked) containers.
4. **L4** — View One JS: on category click, fetch `/api/builder/line_items?page=X`, filter by category, render rows (line_code + output_title + item_role + form_visible badge).
5. **L5** — View Two JS: on question click, populate 5 collapsible sections (Description, Logic, Costs, Meta, Output) from row data already in memory.
6. **L6** — Wire save button to POST to `/api/builder/line_item/<id>/save`; on success return to View One with updated row.
