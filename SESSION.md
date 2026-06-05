# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* **Line Item Architecture Sprint — Session F**: Verify whether the `line_items_by_category` accordion renders visibly on the Materials page runtime form, vs being hidden behind/inside the existing legacy `accordion_group` schema blocks. Determine architecture for coexistence or replacement.

## Active Files for Context
* @app/template_store.py
* @app/QMapp.py
* @app/templates/form.html
* @app/templates/review.html
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed

### Previous sessions
* **All 10 CRUD checklist items** ✅ — CLEAR as of `978edf6`
* **P1 Sidebar collapse in edit mode** ✅ — commit `66abfb9`
* **P2 Select Page width + arrow direction** ✅ — commit `2852f49`
* **Accordion Hierarchy architectural analysis** ✅ — 4-phase plan written
* **Phase 1 — Schema Migration** ✅ — 17 `checkbox_group` blocks promoted to `accordion_group` — commit `07a9811`
* **Phase 2 — Sub-block Discovery & Schema Population** ✅ — 8 hardcoded sub-questions migrated to schema (ew/er/id/dr)

### This session (05/06/26)
* **Architecture pivot** ✅ — Full end-to-end review. Agreed to engineer from output backwards. Google Sheet CSV (~950 rows) uploaded and analysed. Full `line_items` DB architecture defined and documented in `current_development.md`. — commit `cf49fae`
* **Session A — line_items table + CSV migration** ✅ — `line_items` table added to `template_store.py`. `scripts/migrate_line_items_from_csv.py` written and executed. 1022 rows seeded (`auto_child: 245, guidance: 78, parent: 161, special: 188, standalone: 350`). Parent/child inference working.
* **Session B — Builder canvas wired** ✅ — `builder_beta.html` updated to mount `render_line_items_canvas()` + `render_line_item_properties()` macros and call `initLineItemsCanvas()` on DOMContentLoaded. Canvas fetches categories from `/builder_beta/line_items_json`, renders accordion rows, loads 9-field properties panel on row click. `pricing_visibility` toggle saves via `/builder_beta/line_item_save/<id>`.
* **Session C — form.html queries line_items** ✅ — `template_store.py` gained `get_line_items_for_page(form_page)`. `QMapp.py` wired `_get_line_items_for_page()` into `materials_page` (`form_page='3'`) and `further_requirements_page` (`form_page='3B'`). `form.html` renders category-grouped accordion checkboxes (`name="li_sel"`) when `line_items_by_category` is present; legacy Sheets path preserved in `{% else %}` fallback. — commit `91f26e9`
* **Session D — Output Generator** ✅ — `template_store.py` gained `get_line_items_by_codes(codes)`. `QMapp.py`: `materials_page()` POST saves `session['li_sel_3']`; `further_requirements_page()` POST saves `session['li_sel_3b']`; `review()` merges both, calls `get_line_items_by_codes`, groups by category into `li_by_category`. `review.html` renders "Selected Line Items" accordion with output_title / output_notes / output_guidance / unit_cost.
* **Session E — Integration Test** ✅ — Server confirmed running (200 OK). Code audit confirmed all template variables and routes are wired correctly. Identified that the Materials page already has legacy `accordion_group` blocks in the schema (from Phase 1/2), so the new `line_items_by_category` block may not be visually distinguishable — this is Session F's blocker.

## Known Issues / Bug Backlog
* Pre-existing Pylance warning: `description_column_includes` possibly unbound in `submit()` (line ~4738). Not blocking.
* **Session F blocker**: The Materials & Details page runtime form already renders legacy `accordion_group` schema blocks (External Walls, Roofs, etc.). The new `line_items_by_category` section in `form.html` renders AFTER these, but it's unclear if it's visually distinct or duplicating content. Architecture decision needed: (a) remove legacy ACCORDION_GROUP blocks from schema for pages 3/3B, or (b) keep both and ensure the li_sel section is clearly labelled separately.

## Immediate Next Task (start here on reopen)

### 🚀 Session F — Resolve line_items vs legacy schema block overlap on Materials page

**Goal:** Determine whether `line_items_by_category` accordion is rendering on the runtime form, and whether it conflicts with existing `accordion_group` schema blocks.

**Step 1 — Diagnose what the runtime form renders:**
```bash
cd /Users/krisoldland/Documents/QM_web_app
env QM_DISABLE_SHEETS=1 python3 -m flask --app app/QMapp.py run --port=5003 --with-threads
# In another terminal:
curl -s http://localhost:5003/materials_page | grep -c "li_sel"
curl -s http://localhost:5003/materials_page | grep -i "li_sel\|line-items\|Selected Line" | head -20
```

**Step 2 — Read `form.html` around the `{% if line_items_by_category %}` block** to confirm whether it sits inside or outside `{% for field in page_schema.fields %}`.

**Step 3 — Architecture decision:**
- If `line_items` data covers the same content as the ACCORDION_GROUP schema blocks → mark those schema blocks `hidden=true` via the builder for pages 3/3B
- If they cover different content → keep both, ensure `line_items_by_category` section has a visible heading to distinguish it

---

### ~~Session E — Integration Test & Polish~~ ✅ COMPLETE

### ~~Session D — Output Generator~~ ✅ COMPLETE

### ~~Session C — form.html queries line_items~~ ✅ COMPLETE — commit `91f26e9`

### ~~Session B — Builder Canvas: line_items Accordions~~ ✅ COMPLETE

### ~~Session A — line_items Table + CSV Migration Script~~ ✅ COMPLETE

## Session Log
| Date | Items | Result |
|------|-------|--------|
| 05/06/26 | CRUD #1–10 | All CLEAR |
| 05/06/26 | P1 Sidebar collapse | FIXED — `66abfb9` |
| 05/06/26 | P2 Select Page width + arrow | FIXED — `2852f49` |
| 05/06/26 | Accordion analysis | 4-phase plan written |
| 05/06/26 | Phase 1 schema migration | ✅ COMPLETE — `07a9811` |
| 05/06/26 | Phase 2 sub-block discovery + schema population | ✅ COMPLETE |
| 05/06/26 | Architecture pivot — line_item model defined | ✅ COMPLETE — `cf49fae` |
| 05/06/26 | Session A — line_items table + CSV migration | ✅ COMPLETE |
| 05/06/26 | Session B — builder canvas wired | ✅ COMPLETE |
| 05/06/26 | Session C — form.html queries line_items | ✅ COMPLETE — `91f26e9` |
| 05/06/26 | Session D — output generator | ✅ COMPLETE |
| 05/06/26 | Session E — integration test | ✅ COMPLETE — server 200 OK, blocker identified → Session F |
