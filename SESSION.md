# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* **Line Item Architecture Sprint — Session H (continued)**: Builder canvas UI for `line_items_by_category` category management. Non-dev admins can open `/builder_beta/page/materials_page`, see the `line_items_by_category` block, and toggle which DB categories appear on that page.

## Active Files for Context
* @app/template_store.py
* @app/QMapp.py
* @app/templates/form.html
* @app/templates/review.html
* @app/templates/_builder_macros.html
* @app/static/js/builder.js
* @app/templates/builder_beta.html
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed

### Session H — Steps H1 + H2 (06/06/26) — commit `970cc35`
* **H1** ✅ — `line_items_by_category` block entries added to `page_schemas.json` for `materials_page` (8 categories from form_page `'3'`) and `further_requirements_page` (2 categories from form_page `'3B'`). Each block has `config.categories` array pre-seeded from DB.
* **H2** ✅ — `QMapp.py` 5 targeted edits:
  1. `_get_line_items_for_page(form_page_key, categories=None)` — optional `AND category IN (...)` SQL filter
  2. `_get_li_categories_from_schema(page_id)` — reads `config.categories` from the block in `page_schemas.json`; returns `None` = show all
  3. Both `materials_page` and `further_requirements_page` routes updated to pass schema-driven category filter
  4. `compile_builder_beta_page_to_runtime_schema` — `elif block_type == 'line_items_by_category'` branch forwards `config` to compiled field
  5. New `POST /builder_beta/block_config_save/<page_id>/<block_id>` endpoint — patches `config` in `page_schemas.json` in-place

### Earlier Sessions (summary)
* Sessions A–G fully complete — see `current_development.md` for detail.

## Known Issues / Bug Backlog
* Pre-existing Pylance warning: `description_column_includes` possibly unbound in `submit()` (~line 4738). Not blocking.

## Immediate Next Task (start here on reopen)

### 🚀 Session I: Pivot to Database-Driven Unified Hierarchy

**Goal**: Move away from the standalone block builder concept and Google Sheets API towards a fully database-driven, nested schema architecture.

**Hierarchy Map:**
```
Page
|-------Section (accordian) 
------------- Question (checkbox) 
------------------------- Logic
-------------------------------------Secondary Question (Text entry/Numerical/Checkbox/dropdown)
----------------------------Output 
------------------------------------ Title
------------------------------------ Description
------------------------------------ Guidance Note
----------------------------Meta 
------------------------------------ Parent Page (automatically created)
------------------------------------ Parent Section (automatically created)
------------------------------------ Line Code (automatically created)
------------------------------------ Internal description (pull from Output>Title but make it editible)
--------------------------Costs 
------------------------------------ Unit Cost
------------------------------------ Unit Amount Allow Input Toggle (if off default to 1) 
------------------------------------ Cost Group (allows us to root the cost to the right section)
```

**Next Steps**:
1. Map the new CSV (`app/context_archive /Plus Rooms Live input in doc formatting (back up) - Sheet1v2.csv`) to the new hierarchy.
2. Update the import script (`migrate_line_items_from_csv.py` or new script) and DB schema to ingest this new data structure, explicitly breaking out the description and cost columns.
3. Update UI to enforce two strict modes: User Mode (completing the form to generate a quote) and Edit Mode (admin managing the schema directly from the DB).

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
| 05/06/26 | Session G — auto_child filter + smoke test | ✅ |
| 06/06/26 | Session H (H1+H2) — schema blocks + backend filter + save endpoint | ✅ `970cc35` |
