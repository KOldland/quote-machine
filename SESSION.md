# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* **Line Item Architecture Sprint — Session A**: Add `line_items` table to `template_store.py` and write `scripts/migrate_line_items_from_csv.py` to seed ~950 rows from the Google Sheet CSV using the suffix taxonomy.

## Active Files for Context
* @app/template_store.py
* @app/scripts/migrate_line_items_from_csv.py  ← to be created
* @app/context_archive/Plus Rooms Live input in doc formatting (back up) - Sheet1.csv
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
* **Phase 1 — Schema Migration** ✅ — 17 `checkbox_group` blocks promoted to `accordion_group` — commit `07a9811`
* **Phase 2 — Sub-block Discovery & Schema Population** ✅ — 8 hardcoded sub-questions migrated to schema (ew/er/id/dr)

### This session (05/06/26)
* **Architecture pivot** ✅ — Full end-to-end review. Agreed to engineer from output backwards. Google Sheet CSV (~950 rows) uploaded and analysed. Full `line_items` DB architecture defined and documented in `current_development.md`. — commit `cf49fae`

## Known Issues / Bug Backlog
* None — all prior bugs resolved. Active sprint is a feature build.

## Immediate Next Task (start here on reopen)

### 🚀 Session A — `line_items` Table + CSV Migration Script

Full architecture spec is in `app/.continue/prompts/current_development.md` under **NEW SPRINT: Line Item Architecture**.

**Two deliverables:**

**1. Add `line_items` table to `template_store.py`**
Add inside `_create_schema()` alongside existing tables:

```sql
CREATE TABLE IF NOT EXISTS line_items (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    line_code            TEXT NOT NULL UNIQUE,
    form_page            TEXT,
    category             TEXT NOT NULL,
    internal_description TEXT,
    include_default      TEXT NOT NULL DEFAULT 'N',
    unit_cost            REAL DEFAULT 0.0,
    units                REAL DEFAULT 0.0,
    pricing_visibility   TEXT NOT NULL DEFAULT 'admin_only',
    output_title         TEXT,
    output_notes         TEXT,
    output_guidance      TEXT,
    parent_code          TEXT,
    item_role            TEXT NOT NULL DEFAULT 'standalone',
    input_type           TEXT,
    trigger_parent_code  TEXT,
    form_visible         INTEGER NOT NULL DEFAULT 1,
    sort_order           INTEGER NOT NULL DEFAULT 0,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**2. Write `scripts/migrate_line_items_from_csv.py`**
Source CSV: `app/context_archive/Plus Rooms Live input in doc formatting (back up) - Sheet1.csv`

Suffix taxonomy for `item_role` + `form_visible`:
- `#` suffix → `item_role=parent`, `form_visible=1`
- `^` suffix → `item_role=standalone`, `form_visible=1`
- trailing `a/b/c` (no `*`) → `item_role=auto_child`, `form_visible=0`
- `*` suffix → `item_role=guidance`, `form_visible=0`
- `@` suffix → `item_role=special`, `form_visible=0`
- no suffix → `item_role=standalone`, `form_visible=1`

Parent inference: strip trailing suffix chars, look for `#` code with same base (e.g. `sn1a` → `sn1#`).

CSV column mapping (0-indexed):
`form_page(0) | line_code(1) | category(2) | internal_description(3) | include_default(4) | unit_cost(5) | units(6) | total_cost(7) | [skip 8,9,11] | output_title(10) | output_notes(12) | output_guidance(13)`

Clean `unit_cost`: strip `£`, commas, handle blank/`-` → 0.0

Verify ~950 rows inserted with correct `item_role` distribution printed as summary.

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
