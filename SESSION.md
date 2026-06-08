# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session Z** — Complete form-mode fix for remaining pages: run Bug 2 route swap script, audit remaining 2 routes, browser-verify all pages show labelled checkboxes.

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/scripts/migrate_summary_page.py
* @app/page_schemas.json
* @app/template_store.sqlite3
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session Y-2 (this session)**:
  - Fixed `summary_page` hidden categories by updating and running `app/scripts/migrate_summary_page.py` (activates core pp%, bs%, dm%, an% rows).
  - Resolved extraneous Jinja tags in `app/templates/form.html` and removed the legacy hardcoded summary questionnaire, eliminating the stray empty accordion bar.
  - Verified `special_notes_page` and `summary_page` are 100% active, clean, and database-wired.

## Exact Stopping Point
* `special_notes_page` — ✅ DONE
* `summary_page` — ✅ DONE
* `further_requirements_page` — ✅ DB done; ⚠️ Bug 2 route swap NOT yet run
* `materials_page` — ✅ DB done; ❌ Bug 2 route swap NOT yet run
* `additional_costs_page` — ✅ DB done; ❌ Bug 2 route swap NOT yet run
* `additional_building_work_page` — ✅ DB done; ⚠️ route audit pending
* `optional_extras_page` — ✅ DB done; ⚠️ route audit pending

## Immediate Next Task (start here on reopen)
### Session Z — Apply Bug 2 + verify all pages

**Step 1 — Run existing route-swap script (3 pages):**
```bash
python3 app/scripts/fix_form_mode_routes.py
python3 -m py_compile app/QMapp.py && echo SYNTAX_OK
```

**Step 2 — Audit & fix remaining 2 routes:**
`additional_building_work_page` and `optional_extras_page` routes in `QMapp.py`. Ensure they use `build_page_schema_context`.

**Step 3 — Start server + browser-verify:**
`env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003`
Verify all 7 pages show labelled checkboxes grouped by category without any empty bars.

## Known Pitfalls
* **Never `replace_in_file` on `QMapp.py`** — use scripts.
* **Bug 1 already applied** — `_get_line_items_for_page` normalization patched at line 1207.
