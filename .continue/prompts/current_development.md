# Current Development: Session M — Verify 3-Column Canvas

## Session L ✅ COMPLETE (commit 6afd05c, 06/06/26)

All Session L build steps delivered:
- `QMapp.py` — `/builder_beta/line_items_json` accepts `?page=` + `?category=` filters; `materials_page` and `further_requirements_page` edit_mode renders pass `form_page_key` + `li_categories`
- `_builder_macros.html` — `render_li_sections_panel` (col 1) + `render_li_question_panel` (col 2 JS state machine: View One list, View Two 5-tab editor, CSRF save, Back btn)
- `form.html` — edit_mode branches to 3-col canvas when `li_categories` set; legacy block builder otherwise

## Session M Goal
Boot the server and verify the 3-column canvas end-to-end. Fix any rendering / XHR issues found.

### Steps
1. `bash start_flask.sh` (or `QM_TEST_MODE=1 python3 QMapp.py`)
2. Login as admin → `/materials_page?edit=1`
3. Confirm 3-col canvas renders (sections panel, question panel with empty state)
4. Click a section button → View One question list populates via XHR
5. Click a question row → View Two editor shows with field values
6. Edit + SAVE → `{"ok": true}`, title updates
7. Back → View One re-renders cached list
8. Repeat for `/further_requirements_page?edit=1`
9. Commit any fixes as `fix(SessionM):`

### Known Potential Issues
- If `li_categories` is `[]` (no `line_items_by_category` block in `page_schemas.json`), legacy canvas shown — by design
- `line_items` DB table needs rows with `form_page='3'` / `'3B'` for sections to appear
- CSRF: JS reads `document.querySelector('[name=csrf_token]')` — injected at top of 3-col canvas

---

# Previous Sprint Reference: Accordion Hierarchy Sprint

## Phase Status

**Phase 1 ✅ COMPLETE. Phase 2 — schema population ✅ COMPLETE. Next: Phase 2 Jinja rendering update (form.html).**

The previous testing sprint (archived in `current_development_comp2.md`) confirmed all 10 CRUD checklist items CLEAR. The new sprint addresses a fundamental architectural gap: the builder treats every question block as a flat item, but the front-end renders them as **accordion containers** with nested sub-questions. We are restoring that missing hierarchy layer.

---

## The Problem

The current data model in `page_schemas.json` is flat:

```json
{ "blocks": [
  { "id": "materials_page__selected_ew", "block_type": "checkbox_group",
    "standard": { "label": "External Walls", "source_prefix": "ew" } }
]}
```

But the front-end renders a two-level structure:

```
Page
  └── Accordion: "External Wall Options"       ← container with title
        ├── ☑ checkbox items (from Sheets)     ← dynamic choices via source_prefix
        ├── [Metres] dropdown                  ← sub-question (hardcoded in template; not in schema)
        └── [Centimetres] dropdown             ← sub-question (hardcoded in template; not in schema)
  └── Accordion: "Roofing Options"
  └── ...
```

Two hierarchy layers are collapsed into one. The builder cannot see or manage sub-questions within accordions.

---

## Target Data Model

```json
{ "blocks": [
  {
    "id": "materials_page__ew",
    "block_type": "accordion_group",
    "standard": { "label": "External Wall Options", "source_prefix": "ew" },
    "sub_blocks": [
      {
        "id": "materials_page__ew_metres",
        "block_type": "dropdown_select",
        "standard": { "label": "Metres", "name": "ew_metres",
                      "dropdown_choices": ["1m","2m","3m"], "required": false }
      },
      {
        "id": "materials_page__ew_centimetres",
        "block_type": "dropdown_select",
        "standard": { "label": "Centimetres", "name": "ew_cm",
                      "dropdown_choices": ["10cm","20cm","30cm"], "required": false }
      }
    ]
  }
]}
```

---

## AI Behaviour Rules (this sprint)

- Do not touch `form.html` front-end rendering until Phase 2 is fully complete and verified in the schema.
- Never rename or remove `source_prefix` — it drives Google Sheets data loading for checkbox choices.
- Keep migration scripts idempotent (safe to re-run).
- Never rewrite `QMapp.py` wholesale — only localised `replace_in_file` blocks.

---

## 4-Phase Plan

### Phase 1 — Schema Migration (data only, zero UI change)

**Goal:** Rename `checkbox_group` → `accordion_group` for all blocks that carry a `source_prefix`. Add `sub_blocks: []` to each. The front-end templates and backend routes are not changed yet — they continue to work off the existing fields.

**Tasks:**
- Write a one-time migration script (`scripts/migrate_accordion_schema.py`)
- Script reads `page_schemas.json`, for each page iterates blocks, promotes any block with `standard.source_prefix` to `block_type: "accordion_group"` and adds `"sub_blocks": []`
- Script writes updated schema back to `page_schemas.json` (and `page_schemas_published.json` for parity)
- Verify app still loads all pages correctly after migration (no 500s)
git push 
**Exit criteria:** All pages load. `block_type` for source-prefix blocks is now `accordion_group`. `sub_blocks` key exists (empty array) on each. No front-end visible change.

---

### Phase 2 — Sub-question Discovery & Migration (schema + template audit)

**Goal:** Find all hardcoded sub-questions currently living in Jinja templates (`form.html`, `materials_page` template logic) and migrate them into the schema as `sub_blocks` under their parent accordion.

**Tasks:**
- Audit `form.html` and `QMapp.py` for any hardcoded question fields that are logically nested inside an accordion section (e.g. Metres/Centimetres inside External Walls)
- Add discovered sub-questions to the relevant `sub_blocks[]` in `page_schemas.json`
- Update the Jinja template rendering path to read `sub_blocks` from schema rather than hardcoded HTML
- Verify front-end form still renders and submits correctly

**Exit criteria:** No hardcoded sub-questions remain in templates. All sub-questions are schema-driven. Front-end form submission and output is unchanged.

---

### Phase 3 — Builder Canvas: Accordion Rendering

**Goal:** The builder canvas visually mirrors the front-end accordion hierarchy. Accordion blocks render as expandable containers with their sub-blocks indented inside.

**Tasks:**
- Update `renderCanvas()` in `builder.js` to render `accordion_group` blocks as containers
- Accordion container shows: drag handle, accordion title, source_prefix badge, expand/collapse toggle
- Sub-blocks render indented inside the accordion with their own drag handles and edit/delete buttons
- Clicking the accordion header selects it → Block Properties panel shows: Label (accordion title) + Source Prefix field
- Clicking a sub-block selects it → Block Properties panel shows existing Question Fields, Logic, Pricing, Output sections
- Update `_builder_macros.html` canvas macro to support accordion container rendering (Jinja server-side path)

**Exit criteria:** Builder canvas matches front-end accordion structure. Correct properties panel loads for both accordion header and sub-blocks.

---

### Phase 4 — Builder Interactions: Manage Sub-blocks

**Goal:** Full CRUD for sub-blocks within accordions via the builder interface.

**Tasks:**
- "＋ Add sub-question" button appears inside each accordion container in the canvas
- Clicking it triggers the existing type-picker modal; selected type creates a new sub-block under the parent accordion
- Sub-blocks can be reordered within their accordion via drag handle
- Sub-block delete button removes it from `sub_blocks[]`
- Backend `save_block` / `add_block` / `delete_block` routes in `QMapp.py` handle nested block path (`page → accordion → sub_blocks[]`)
- Accordion blocks themselves can be reordered at the top level (existing drag behaviour)

**Exit criteria:** An admin can add, reorder, and delete sub-questions within any accordion directly in the builder. Changes persist to `page_schemas.json` and render correctly on the live form.

---

## Testing Checklist

1. [x] Phase 1 — Schema migration runs without error; 17 blocks promoted, JSON valid in both schema files
2. [x] Phase 1 — All `source_prefix` blocks are now `accordion_group` type with `sub_blocks: []`
3. [x] Phase 2 — All hardcoded sub-questions found and audited (8 sub-questions across 4 accordions)
4. [x] Phase 2 — Sub-questions migrated to schema (`migrate_phase2_sub_blocks.py`); sub_blocks populated in both JSON files
5. [ ] Phase 2 — Jinja rendering updated in form.html to read sub_blocks dynamically; form renders identically and submits correctly
6. [ ] Phase 3 — Builder canvas renders accordion containers with indented sub-blocks
7. [ ] Phase 3 — Clicking accordion header → correct properties panel (title + source prefix)
8. [ ] Phase 3 — Clicking sub-block → correct properties panel (full question fields)
9. [ ] Phase 4 — "＋ Add sub-question" creates new sub-block inside correct accordion
10. [ ] Phase 4 — Sub-block reorder and delete work; changes persist

---

## Session Log

| Date | Phase | Session | Result |
|------|-------|---------|--------|
| 05/06/26 | Planning | Architectural gap identified — accordion hierarchy missing from builder | Plan agreed — 4 phases defined |
| 05/06/26 | Phase 1 | `migrate_accordion_schema.py` written & run — 17 blocks promoted to `accordion_group` with `sub_blocks: []` in both JSON files | ✅ COMPLETE — commit `07a9811` |
| 05/06/26 | Phase 2 (schema) | Audited form.html + QMapp.py — 8 hardcoded sub-questions found. `migrate_phase2_sub_blocks.py` written & run — sub_blocks populated for ew/er/id/dr accordions in both JSON files | ✅ COMPLETE — this session |
| 05/06/26 | Architecture pivot | Reconsidered form structure end-to-end. Agreed to engineer from output backwards. Google Sheet CSV uploaded and analysed (~950 line items). Full `line_items` DB architecture defined — see new section below. | ✅ Architecture agreed — handoff committed |
| 06/06/26 | Phase 2 (schema) | Session J | Resolved AttributeError on `/special_notes_page` caused by legacy `get_page_schema`. Smoke test (`smoke_submit.py`) now passing. Tests and routes for removed standalone builder are failing and need to be cleaned up. | ✅ COMPLETE — ready for cleanup |

---

## Known Issues / Notes

- `source_prefix` must be preserved on `accordion_group` blocks at all times — it is the key that drives Google Sheets data loading for checkbox choices.
- Pages that have **flat questions** (no accordion parent, e.g. Project Details `index` page) should keep `block_type: "checkbox_group"` or other existing types. Only blocks with `source_prefix` are promoted to `accordion_group` in Phase 1.
- The `page_schemas_published.json` file mirrors `page_schemas.json`; both must be updated in the migration.

---

## NEW SPRINT: Line Item Architecture — Engineer From Output Backwards

### Overview

This supersedes Phase 2 Jinja rendering and replaces the `page_schemas.json` accordion approach with a first-class `line_items` DB table. The key insight: every selectable element in the system is a **line item** with a canonical 9-field data model derived directly from the original Google Sheet structure.

---

### The Source CSV

`app/context_archive/Plus Rooms Live input in doc formatting (back up) - Sheet1.csv`

Contains ~950 rows. Columns:
`template page | Line Code | Category | Internal Description | Include | Unit Cost | Unit | Total Cost | Summed_Totals | Dimension | description | Calculations | Description3 | Description4 | Description5`

Output columns: `description` = output_title, `Description3` = output_notes, `Description4` = output_guidance.

---

### Line Code Suffix Taxonomy

| Suffix | Role | Form visible? | Output? |
|---|---|---|---|
| `#` | Parent heading — accordion checkbox with auto-children | ✅ | ✅ header |
| `^` | Selectable standalone checkbox | ✅ | ✅ |
| `a`, `b`, `c` (no `*`) | Auto-child — output only, shown under parent | ❌ | ✅ |
| `*` | Guidance child — *PLEASE NOTE... text | ❌ | ✅ as note |
| `@` | Special — dimensions, total markers, image refs | varies | varies |

Parent relationship is inferred algorithmically: strip trailing letters from code, find `#` entry with same base.

---

### `line_items` DB Table Schema

```sql
CREATE TABLE line_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    line_code           TEXT NOT NULL UNIQUE,
    form_page           TEXT,
    category            TEXT NOT NULL,
    internal_description TEXT,
    include_default     TEXT NOT NULL DEFAULT 'N',

    unit_cost           REAL DEFAULT 0.0,
    units               REAL DEFAULT 0.0,
    pricing_visibility  TEXT NOT NULL DEFAULT 'admin_only',
                        -- admin_only | user_view | user_edit

    output_title        TEXT,
    output_notes        TEXT,
    output_guidance     TEXT,

    parent_code         TEXT,
    item_role           TEXT NOT NULL DEFAULT 'standalone',
                        -- standalone | parent | auto_child | guidance | special | manual_child

    input_type          TEXT,               -- NULL | text | number | dropdown (manual_child only)
    trigger_parent_code TEXT,

    form_visible        INTEGER NOT NULL DEFAULT 1,
    sort_order          INTEGER NOT NULL DEFAULT 0,

    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

`pricing_visibility` allows admin to control per-question whether unit/cost/total is hidden, view-only, or user-editable in the form.

---

### Build Order (4 sessions)

1. **Session A** — Add `line_items` table to `template_store.py` + write `scripts/migrate_line_items_from_csv.py` that seeds from the CSV using suffix taxonomy. Verify row count ~950.
2. **Session B** — Rework builder canvas (`_builder_macros.html` + `builder.js`) so accordions = categories from `line_items`, each row = one line item, all 9 fields editable in properties panel.
3. **Session C** — Simplify `form.html` to query `line_items` by page + `form_visible=1` instead of `page_schemas.json`.
4. **Session D** — Build output generator: reads Y-flagged items per submission, groups by category, emits title/notes/guidance + pricing totals.

---

### Testing Checklist (this sprint)

- [x] A1 — `line_items` table added to `template_store.py`; migration script runs without error
- [x] A2 — 1022 rows seeded from CSV; suffix taxonomy correctly sets `item_role` and `form_visible` (auto_child: 245, guidance: 78, parent: 161, special: 188, standalone: 350)
- [x] A3 — Parent/child relationships correctly inferred (e.g. `sn1a` → parent `sn1#`)
- [x] B1 — Builder canvas renders category accordions from `line_items`
- [x] B2 — Clicking a line item row loads all 9 fields in properties panel
- [x] B3 — `pricing_visibility` toggle works per item
- [x] C1 — `form.html` queries `line_items` for form-visible items; category-grouped accordions render from SQLite (`form_page='3'` / `'3B'`); legacy Sheets path preserved in `{% else %}` fallback — commit `91f26e9`
- [x] D1 — Output generator reads Y items grouped by category, emits correct text + pricing — `review.html` renders "Selected Line Items" accordion with output_title / output_notes / output_guidance / unit_cost ✅ COMPLETE
- [x] E1 — [Session F] ✅ COMPLETE — 9 legacy `accordion_group` blocks marked `hidden: true` in `builder_beta.pages` for `materials_page` (ew/er/id/dr/wp) + `further_requirements_page` (frc/dw/fs/gv). `compile_builder_beta_page_to_runtime_schema` bugfix: `'hidden'` flag now propagates to `form.html`. Builder canvas shows red HIDDEN badge + opacity + strikethrough on suppressed blocks. — commits `4cd3b01` + `a56ef73`
- [x] G1 — [Session G] ✅ COMPLETE — `AND item_role != 'auto_child'` added to both query functions. End-to-end smoke test passed: no legacy blocks visible, `line_items_by_category` renders + submits, review shows grouped output by category.
- [x] H1 — [Session H] ✅ COMPLETE — `line_items_by_category` blocks added to `page_schemas.json` for `materials_page` + `further_requirements_page` with `config.categories` pre-seeded from DB (page '3': 8 categories; page '3B': 2 categories) — commit `970cc35`
- [x] H2 — [Session H] ✅ COMPLETE — `_get_line_items_for_page(categories=None)` filter wired; `_get_li_categories_from_schema()` helper reads block config; routes updated to pass categories; `compile_builder_beta_page_to_runtime_schema` handles `line_items_by_category` block type; `/builder_beta/block_config_save/<page_id>/<block_id>` POST endpoint added — commit `970cc35`
### Session I: Pivot to Database-Driven Unified Hierarchy
- [x] I1 — Map new `Plus Rooms Live input in doc formatting (back up) - Sheet1v2.csv` headers to DB schema (`output_title`, `output_notes`, `output_guidance`, etc.)
- [x] I2 — Update `migrate_line_items_from_csv.py` to ingest the V2 CSV format
- [x] I3 — Remove old standalone block builder UI and ensure strict 2-mode approach (User/Edit)

### Session K: Post-Schema Migration
- [x] K1 — Clean up deprecated standalone builder routes in `QMapp.py`
- [x] K2 — Update/remove deprecated test cases in `test_submit_production.py` to reflect the new inline-sidebar architecture
- [x] K3 — Fix `ui_regression.sh` to remove checks against deprecated endpoints so automated UI regression passes cleanly

---

## Session L: 3-Column Line Item Canvas (Edit Mode Rebuild)

### Goal

Replace the current flat canvas (accordion list + floating properties panel) with a **3-column Edit Mode UI** that gives full visibility and control over every field in the `line_items` DB, without leaving the live page.

### Layout

```
[ LEFT SIDEBAR     ]  [ CANVAS COL 1 — SECTIONS ]  [ CANVAS COL 2 — CONTEXTUAL ]
  Page selector          Section One                    View One: Question list
  Publish                Section Two                      (when section selected)
  Undo / Exit            Section Three                  ──────────────────────────
                                                         View Two: Question editor
                                                           (when question clicked)
                                                           - Description fields
                                                           - Logic / secondary Qs
                                                           - Costs options
                                                           - Meta data
                                                           - Output options
```

### Data Source

- **Sections (Col 1)** = distinct `category` values from `line_items` for the current page (queried from SQLite via existing `get_line_items_for_page`)
- **Questions (Col 2 View One)** = all line_items rows for the selected category (filtered by `form_page` + `category`); includes all roles (parent, standalone, auto_child, guidance, special)
- **Question editor (Col 2 View Two)** = full set of `line_items` DB fields, grouped into 5 collapsible sections:
  1. **Description** — `output_title`, `output_notes`, `output_guidance`, `internal_description`
  2. **Logic / secondary questions** — `item_role`, `parent_code`, `trigger_parent_code`
  3. **Costs** — `unit_cost`, `units`, `pricing_visibility`
  4. **Meta** — `line_code`, `category`, `form_page`, `sort_order`, `form_visible`, `include_default`
  5. **Output** — `output_title`, `output_notes`, `output_guidance` (confirmed output view)

### Build Steps

1. **L1 — Backend API endpoint**: `GET /api/builder/line_items?page=X` returns all line items for a page as JSON (grouped by category). `POST /api/builder/line_item/<id>/save` saves all fields from View Two form.
2. **L2 — `render_li_sections_panel()` macro**: Renders category list in Col 1. Each category button is clickable. Active state highlights selected category.
3. **L3 — `render_li_contextual_panel()` macro**: Col 2 wrapper with two view states (View One / View Two), both initially hidden until a category is selected.
4. **L4 — View One (question list)**: Populated via JS fetch from L1 API. Shows line_code, output_title/internal_description, item_role, form_visible flag for each row. Clicking a row switches to View Two.
5. **L5 — View Two (question editor)**: 5 collapsible sections rendered via JS from row data. Save button POSTs to L1 save endpoint and returns to View One.
6. **L6 — `builder.js` state machine**: Manages activeCategory, activeItemId, and the View One/Two toggle entirely client-side (no full page reload).

### What Does NOT Change
- Left sidebar (page selector, Publish, Undo, Exit Edit Mode) — untouched
- Schema-based builder for non-line-item pages (Project Details, Special Notes) — untouched
- `form.html` live form rendering — no changes

### Testing Checklist (Session L)

- [ ] L1 — `GET /api/builder/line_items?page=3` returns correct JSON grouped by category
- [ ] L1 — `POST /api/builder/line_item/<id>/save` updates DB and returns 200
- [ ] L2 — Section list renders in Col 1; active state highlights on click
- [ ] L3 — Contextual panel renders empty state correctly before any selection
- [ ] L4 — Click category → View One populates with correct question rows for that category
- [ ] L4 — All item roles visible in question list (parent, standalone, auto_child, guidance, special)
- [ ] L5 — Click question → View Two opens with correct pre-populated field values
- [ ] L5 — All 5 collapsible sections render (Description, Logic, Costs, Meta, Output)
- [ ] L5 — Save button POSTs correctly; DB field updated; return to View One
- [ ] L6 — Full state machine works: category select → question list → question editor → save → back to list
