# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session Z** — Complete form-mode fix for all 7 refactored pages: run Bug 2 route swap script, audit remaining 2 routes, browser-verify all pages show labelled checkboxes.

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/scripts/fix_form_mode_routes.py
* @app/scripts/fix_li_dict_bug.py
* @app/page_schemas.json
* @app/template_store.sqlite3
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Sessions R–X**: All 7 DB migrations done; `line_items_by_category` wired to form + edit mode; smoke tests passed.
* **Session Y (this session)**:
  - Diagnosed two root-cause bugs for blank form-mode rendering.
  - Updated `SESSION.md`, `current_development.md`, `context.md` with full diagnosis + new "Duplicate Function" pitfall.
  - **Bug 1 fixed** — `_get_line_items_for_page` duplicate definition (line 2807 overwrites line 1122). Patched call at line 1207 with dict→list normalisation + key remapping (`line_code→value`, `internal_description→label`). `SYNTAX OK`. Browser showed headings + checkboxes rendering; label fix applied but not browser-confirmed before session close.
  - `fix_form_mode_routes.py` exists and is ready to run (Bug 2 — covers materials, further_requirements, additional_costs).

## Exact Stopping Point
* `special_notes_page` — ✅ DONE
* `summary_page` — ✅ DONE
* `further_requirements_page` — ✅ DB done; Bug 1 patch applied; ⚠️ Bug 2 route swap NOT yet run; labels unconfirmed
* `materials_page` — ✅ DB done; ❌ Bug 2 route swap NOT yet run
* `additional_costs_page` — ✅ DB done; ❌ Bug 2 route swap NOT yet run
* `additional_building_work_page` — ✅ DB done; ⚠️ route type unknown — needs audit
* `optional_extras_page` — ✅ DB done; ⚠️ route type unknown — needs audit

## Immediate Next Task (start here on reopen)
### Session Z — Apply Bug 2 + verify all pages

**Step 1 — Run existing route-swap script (3 pages):**
```bash
python3 app/scripts/fix_form_mode_routes.py
python3 -m py_compile app/QMapp.py && echo SYNTAX_OK
```

**Step 2 — Audit remaining 2 routes:**
```bash
grep -n "additional_building_work_page\|optional_extras_page" app/QMapp.py | grep "def \|compile_\|build_page_schema"
```
If they use `compile_builder_beta_page_to_runtime_schema` → add same `build_page_schema_context` prepend. If they use neither → check if `page_schema` is passed to template at all.

**Step 3 — Start server + browser-verify all 7 pages in form mode (no `?edit=1`):**
```bash
env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003 --with-threads
```
Each page should show labelled checkboxes grouped by category.

**Step 4 — git commit + push + Cmd+K**

### Known Pitfalls
* **Never `replace_in_file` on `QMapp.py`** — use write-to-temp-script pattern
* **Bug 1 already applied** — do NOT re-run `fix_li_dict_bug.py`; it will find no match and skip safely, but double-check first
* **Flask server on macOS** — foreground only, never `&`
* **`fix_form_mode_routes.py`** uses unique `previous_page=` anchors — safe to run once; idempotent (will print `!! anchor NOT FOUND` if already applied)
