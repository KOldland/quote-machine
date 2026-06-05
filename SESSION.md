# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* **Line Item Architecture Sprint — Session A**: Add `line_items` table to `template_store.py` and write `scripts/migrate_line_items_from_csv.py` to seed ~950 rows from the Google Sheet CSV using the suffix taxonomy. Previous accordion sprint phases 1 & 2 schema work is preserved but superseded by this new data model.

## Active Files for Context
* @app/page_schemas.json
* @app/page_schemas_published.json
* @app/scripts/migrate_phase2_sub_blocks.py
* @app/QMapp.py
* @app/templates/form.html
* @app/static/js/builder.js
* @app/templates/_builder_macros.html
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed

### Previous sessions
* **All 10 CRUD checklist items** ✅ — CLEAR as of `978edf6`
* **P1 Sidebar collapse in edit mode** ✅ — commit `66abfb9`
* **P2 Select Page width + arrow direction** ✅ — commit `2852f49`
* **Accordion Hierarchy architectural analysis** ✅ — 4-phase plan written

### This session (05/06/26)
* **Phase 1 — Schema Migration** ✅ — `scripts/migrate_accordion_schema.py` written and run. 17 `checkbox_group` blocks with `source_prefix` promoted to `accordion_group` with `sub_blocks: []` in both `page_schemas.json` and `page_schemas_published.json`. — commit `07a9811`
* **Phase 2 — Sub-block Discovery & Schema Population** ✅ — Audited `form.html` and `QMapp.py`. Found 8 hardcoded sub-questions across 4 materials-page accordions. Migration script `scripts/migrate_phase2_sub_blocks.py` written and run. Sub-blocks now registered in schema:
  - `materials_page__selected_ew` → `wall_height_metres`, `wall_height_centimetres`
  - `materials_page__selected_er` → `pitched_roof_option`, `other_roofing_description`
  - `materials_page__selected_id` → `fire_doors_number`, `non_fire_doors_number`
  - `materials_page__selected_dr` → `drainage_other_input`, `drainage_other_cost`

## Known Issues / Bug Backlog
* None — all prior bugs resolved. Active sprint is a feature build.

## Immediate Next Task (start here on reopen)

### 🚀 Line Item Architecture — Session A

Full architecture is defined in `app/.continue/prompts/current_development.md` under **NEW SPRINT: Line Item Architecture**.

**Two deliverables for Session A:**

1. **Add `line_items` table** to `template_store.py` — using the SQL schema defined in `current_development.md`. Add it inside `_create_schema()` alongside existing tables.

2. **Write `scripts/migrate_line_items_from_csv.py`** — reads the CSV at:
   `app/context_archive/Plus Rooms Live input in doc formatting (back up) - Sheet1.csv`
   
   For each row:
   - Parse `line_code` suffix to determine `item_role` and `form_visible` using the taxonomy in `current_development.md`
   - Infer `parent_code` by stripping trailing suffix chars and finding the `#` base code
   - Clean `unit_cost` (strip `£`, commas, handle blanks/`-`)
   - Map CSV columns: `description` → `output_title`, `Description3` → `output_notes`, `Description4` → `output_guidance`
   - Insert into `line_items`
   
   Run script and verify ~950 rows inserted with correct `item_role` distribution.

**Source CSV columns** (0-indexed):
`template page(0) | Line Code(1) | Category(2) | Internal Description(3) | Include(4) | Unit Cost(5) | Unit(6) | Total Cost(7) | Summed_Totals(8) | Dimension(9) | description(10) | Calculations(11) | Description3(12) | Description4(13) | Description5(14)`

## Session Log
| Date | Items | Result |
|------|-------|--------|
| 05/06/26 | CRUD #1–10 | All CLEAR |
| 05/06/26 | P1 Sidebar collapse | FIXED — `66abfb9` |
| 05/06/26 | P2 Select Page width + arrow | FIXED — `2852f49` |
| 05/06/26 | Accordion analysis | 4-phase plan written |
| 05/06/26 | Phase 1 schema migration | ✅ COMPLETE — `07a9811` |
| 05/06/26 | Phase 2 sub-block discovery + schema population | ✅ COMPLETE — this commit |
| 05/06/26 | Phase 2 Jinja rendering update — form.html sub_blocks dynamic | ✅ COMPLETE — this commit |
