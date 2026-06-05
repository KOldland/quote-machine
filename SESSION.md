# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* **Line Item Architecture Sprint — Session G**: End-to-end smoke test. Navigate Materials → Further Requirements → Review in browser to confirm: (1) no legacy accordion_group blocks visible, (2) `line_items_by_category` checkboxes render + submit, (3) `review.html` shows selected line items grouped by category.

## Active Files for Context
* @app/template_store.py
* @app/QMapp.py
* @app/templates/form.html
* @app/templates/review.html
* @app/templates/_builder_macros.html
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed

### Line Item Architecture Sprint (05/06/26)
* **Architecture pivot** ✅ — Agreed to engineer from output backwards. CSV (~950 rows) analysed. `line_items` DB architecture defined — commit `cf49fae`
* **Session A** ✅ — `line_items` table in `template_store.py`. `migrate_line_items_from_csv.py` run. 1022 rows seeded (auto_child:245, guidance:78, parent:161, special:188, standalone:350).
* **Session B** ✅ — Builder canvas wired: `builder_beta.html` mounts `render_line_items_canvas()` + `render_line_item_properties()`. Canvas fetches `/builder_beta/line_items_json`, renders category accordions, saves via `/builder_beta/line_item_save/<id>`.
* **Session C** ✅ — `form.html` queries `line_items` via `_get_line_items_for_page()` for `materials_page` (`form_page='3'`) + `further_requirements_page` (`form_page='3B'`). Legacy Sheets path in `{% else %}` fallback. — commit `91f26e9`
* **Session D** ✅ — Output generator: `review()` merges `li_sel_3` + `li_sel_3b`, calls `get_line_items_by_codes`, groups by category into `li_by_category`. `review.html` renders "Selected Line Items" accordion.
* **Session E** ✅ — Integration test: server 200 OK. Blocker identified — legacy `accordion_group` blocks render alongside `line_items_by_category` on Materials page.
* **Session F** ✅ — **Three fixes:**
  1. 9 legacy `accordion_group` blocks marked `hidden: true` in `builder_beta.pages` of `page_schemas.json` for `materials_page` (ew/er/id/dr/wp) + `further_requirements_page` (frc/dw/fs/gv) — commit `4cd3b01`
  2. `QMapp.py` bugfix: `compile_builder_beta_page_to_runtime_schema` now includes `'hidden': block.get('hidden', False)` in `common_payload` so flag propagates to `form.html` — commit `a56ef73`
  3. `_builder_macros.html`: hidden blocks show red HIDDEN badge + 0.45 opacity + strikethrough in builder canvas — commit `a56ef73`

## Known Issues / Bug Backlog
* Pre-existing Pylance warning: `description_column_includes` possibly unbound in `submit()` (~line 4738). Not blocking.

## Immediate Next Task (start here on reopen)

### 🚀 Session H cont. — Builder canvas UI for `line_items_by_category` categories

**Steps H1 + H2 ✅ COMPLETE:**
- `page_schemas.json`: `line_items_by_category` block added to `materials_page` (8 categories) + `further_requirements_page` (2 categories) with `config.categories` arrays pre-seeded from DB
- `QMapp.py`:
  - `_get_line_items_for_page(form_page_key, categories=None)` — category filter via `AND category IN (...)`
  - `_get_li_categories_from_schema(page_id)` — helper reads `config.categories` from schema
  - Both routes updated: `_get_line_items_for_page('3', _get_li_categories_from_schema('materials_page'))` + `'3B'` equivalent
  - `compile_builder_beta_page_to_runtime_schema`: `elif block_type == 'line_items_by_category'` branch passes `config` through
  - `/builder_beta/block_config_save/<page_id>/<block_id>` POST endpoint added — patches `page_schemas.json` in-place

**Next: Steps H3–H5**

### Step H3 — Builder canvas UI

**Goal:** Non-dev admins can open `/builder_beta/page/materials_page`, see the `line_items_by_category` block, and configure which DB categories appear on that page.

**Step H3 — Builder canvas UI**
In `builder_beta.html` or `_builder_macros.html`: properties panel for `line_items_by_category` block shows checklist of all available categories (from `/builder_beta/line_items_json`) with on/off toggles. Saves via `POST /builder_beta/block_config_save/<page_id>/<block_id>` with `{"config": {"categories": [...]}}`.

Key files:
- `_builder_macros.html` — add properties panel section for `block_type == 'line_items_by_category'`
- `builder.js` — fetch category list from `/builder_beta/line_items_json`, render checkboxes, POST on change

**Step H4 — Smoke test:** toggle a category off in builder → reload `/materials_page` → confirm that category's items are hidden.

**Step H5 — SESSION.md + commit**

## Session Log
| Date | Session | Result |
|------|---------|--------|
| 05/06/26 | CRUD #1–10 | All CLEAR |
| 05/06/26 | P1 Sidebar collapse | FIXED — `66abfb9` |
| 05/06/26 | P2 Select Page width + arrow | FIXED — `2852f49` |
| 05/06/26 | Accordion Phase 1 | ✅ `07a9811` |
| 05/06/26 | Accordion Phase 2 schema | ✅ |
| 05/06/26 | Architecture pivot | ✅ `cf49fae` |
| 05/06/26 | Session A — line_items table + CSV | ✅ |
| 05/06/26 | Session B — builder canvas | ✅ |
| 05/06/26 | Session C — form.html wired | ✅ `91f26e9` |
| 05/06/26 | Session D — output generator | ✅ |
| 05/06/26 | Session E — integration test | ✅ blocker → Session F |
| 05/06/26 | Session F — hidden flag + builder badge | ✅ `4cd3b01` + `a56ef73` |
| 05/06/26 | Session G — auto_child filter + smoke test | ✅ — `AND item_role != 'auto_child'` in both query funcs |
| 06/06/26 | Session H (steps 1–2) — schema + backend wiring | ✅ — `page_schemas.json` blocks added, `_get_line_items_for_page(categories)` + `_get_li_categories_from_schema()` + `block_config_save` endpoint |
