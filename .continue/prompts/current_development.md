# Form-Mode Questions Not Rendering (7 Pages)

## Context

All 7 refactored form pages render their questions correctly in **edit mode** (3-col builder), but show an **empty card** (title + PREVIOUS/NEXT only) in the normal **user-facing form mode**.

Previous work in `current_development_3.md` covers the DB migration and 3-col editor work. That is complete.

---

## Root Cause

Every refactored page's non-edit GET path calls:

```python
page_schema = compile_builder_beta_page_to_runtime_schema(page_id)
```

`compile_builder_beta_page_to_runtime_schema` only builds the **schema skeleton** (block structure, field types) — it does **not** query the DB, populate `li_groups`, set `value`, or do any runtime data resolution.

The correct function for form-mode rendering is:

```python
page_schema = build_page_schema_context(page_id, sheet_data, session.get('checkbox_data', {}))
```

`build_page_schema_context` calls `build_builder_beta_runtime_context` which:
1. Queries `line_items` table via `_get_line_items_for_page(page_id)` → populates `field['li_groups']`
2. Calls `get_preselected()` → populates `field['value']` (default-checked from `include_default='Y'`)
3. Handles `checkbox_group`, `dropdown_select`, `text_input`, and `line_items_by_category` field types

Without this, `field.li_groups` is Undefined in `form.html` and no items render.

---

## Page Status

| Page | Form-mode status | Fix needed |
|------|-----------------|-----------|
| `special_notes_page` | ✅ fixed | None |
| `summary_page` | ✅ fixed | None |
| `materials_page` | ✅ fixed | None |
| `further_requirements_page` | ✅ fixed | None |
| `additional_costs_page` | ✅ fixed | None |
| `additional_building_work_page` | ✅ fixed | None |
| `optional_extras_page` | ✅ fixed | None |

---

## Fix Pattern

For each broken route, the non-edit `return render_template(...)` block needs ONE line prepended:

```python
# BEFORE (broken):
return render_template(
    'form.html',
    page_schema=page_schema,   # ← compiled skeleton, no li_groups
    schema_render_mode='full',
    ...
)

# AFTER (fix):
page_schema = build_page_schema_context(page_id, sheet_data, session.get('checkbox_data', {}))
return render_template(
    'form.html',
    page_schema=page_schema,   # ← fully populated with li_groups + value
    schema_render_mode='full',
    ...
)
```

`sheet_data = get_catalog()` is already computed in each route before this point.

The edit-mode paths keep using `compile_...` (the 3-col builder only needs the schema structure, not live data).

---

## Implementation Plan

### Step 1 — Fix `materials_page`, `further_requirements_page`, `additional_costs_page`
- Write `app/scripts/fix_form_mode_routes.py`
- 3 targeted string replacements (unique anchors per route)
- Verify syntax with `python3 -m py_compile app/QMapp.py`
- Manual browser test each page
- [x] DONE

### Step 2 — Audit `additional_building_work_page` + `optional_extras_page`
- Grep route body — identify if `compile_...`, `build_page_schema_context`, or neither
- If neither: check if route passes `page_schema` to template at all
- Apply appropriate fix
- [x] DONE

### Step 3 — Commit + update SESSION.md
- [x] DONE

---

## Additional Bug Found (Session Y)

### Duplicate `_get_line_items_for_page` definition in QMapp.py

There are **two definitions** of `_get_line_items_for_page` in `QMapp.py`:

- **Line 1122** — `def _get_line_items_for_page(page_id)` — returns a **list** `[{'category': ..., 'items': [...]}, ...]`
- **Line 2807** — `def _get_line_items_for_page(form_page_key, categories=None)` — returns a **dict** `{category_name: [row_dict, ...]}`

Python silently uses the **second** definition, discarding the first. So when `build_builder_beta_runtime_context` at line 1207 calls `_get_line_items_for_page(page_id)`, it gets a **dict** back. The template at `form.html:302` iterates `field.li_groups` — iterating a dict yields only string keys, so no content renders.

**Fix**: Patch the call at line 1207 using a temp script:

```python
# Replace line 1207 (0-indexed: 1206):
_li_raw = _get_line_items_for_page(page_id)
li_groups = [{'category': c, 'items': v} for c, v in _li_raw.items()] if isinstance(_li_raw, dict) else _li_raw
```

This must be fixed **before** or **alongside** the route fix — otherwise even the corrected routes still render blank.

---

## Implementation Tracking

- [x] `_get_line_items_for_page` duplicate — dict→list normalisation + key remapping (line_code→value, internal_description→label) patched at line 1207 — SYNTAX OK (Session Y, verified)
- [x] `materials_page` — form-mode fix applied + verified
- [x] `further_requirements_page` — form-mode fix applied + verified
- [x] `additional_costs_page` — form-mode fix applied + verified
- [x] `additional_building_work_page` — route audited + fix applied
- [x] `optional_extras_page` — route audited + fix applied (Session Z.1)
- [x] All 7 pages verified in browser showing correct questions
- [x] Session committed

---

## Key Files

- `app/QMapp.py` — routes to fix
- `app/templates/form.html` — `{% elif field.type == 'line_items_by_category' %}` render block (added Session X)
- `app/template_store.sqlite3` — `line_items` table queried by `_get_line_items_for_page()`
- `app/scripts/fix_form_mode_routes.py` — patch script (to be written)
