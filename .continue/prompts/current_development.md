# Current Development: Accordion Hierarchy Sprint

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

---

## Known Issues / Notes

- `source_prefix` must be preserved on `accordion_group` blocks at all times — it is the key that drives Google Sheets data loading for checkbox choices.
- Pages that have **flat questions** (no accordion parent, e.g. Project Details `index` page) should keep `block_type: "checkbox_group"` or other existing types. Only blocks with `source_prefix` are promoted to `accordion_group` in Phase 1.
- The `page_schemas_published.json` file mirrors `page_schemas.json`; both must be updated in the migration.
