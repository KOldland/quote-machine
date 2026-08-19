# Unified Data Flow Plan: Single Source of Truth for Page/Category/Question Order

## Current State

### BUILD MODE (correct)
- Sidebar categories: `QMapp.py:186` → `get_line_items_for_page()` (`template_store.py:1173`) queries `category_templates` ordered by `display_order ASC`
- Page navigation: `resolve_builder_beta_navigation_targets()` (`QMapp.py:1015`) sorts pages by DB `display_order`
- Question order: `line_items.sort_order` in DB

### FORM MODE (partial)
- Navigation: uses `resolve_builder_beta_navigation_targets()` → DB order → correct
- Review page: iterates `state_pages.items()` from `get_builder_beta_state()` → JSON dict insertion order → **wrong**
- Field order within page: `compile_builder_beta_page_to_runtime_schema()` (`QMapp.py:829`) uses JSON `blocks` list order

### QUOTE MODE (wrong)
- Page order: `build_quote_editor_blocks_for_all_pages()` (`quote_editor_routes.py:852`) iterates `pages.items()` → JSON dict insertion order → **wrong**
- Category order: `_build_page_blocks()` partially fixed to use DB order, but `add_form_block()` (`quote_editor_routes.py:416`) still uses JSON `sort_order` → **wrong**
- Question order: DB `sort_order` → correct

---

## Discrepancies

1. **Page order**: BUILD uses DB `page_templates.display_order`. QUOTE and FORM review use JSON dict insertion order.
2. **Category order**: BUILD uses DB `category_templates.display_order`. QUOTE `add_form_block()` uses JSON `sort_order`.
3. **Question order**: All modes use DB `line_items.sort_order` → already unified.

---

## Proposed Fixes

### Step 1: Sort `get_builder_beta_state()` pages by DB `display_order`
**File**: `app/QMapp.py:612`
- After injecting `display_order` from DB, sort `pages` dict by `display_order` before returning
- Impact: Fixes FORM MODE review page and all other consumers of `get_builder_beta_state()`

### Step 2: Sort QUOTE MODE pages by DB `display_order`
**File**: `app/quote_editor_routes.py:852` (`build_quote_editor_blocks_for_all_pages`)
- Sort `pages` by DB `display_order` before iterating
- Alternative: reuse `get_builder_beta_state()` which will already be sorted after Step 1

### Step 3: Fix `add_form_block()` to use DB category order
**File**: `app/quote_editor_routes.py:467`
- Replace `page.get('categories', [])` JSON sort with `_get_page_category_order(page_key)` DB query
- Add `category_sort_order` to generated blocks, matching `_build_page_blocks()`

### Step 4: Prefer fresh blocks on quote load
**File**: `app/static/js/user_output_editor.js:1291` (`loadQuotesList()`)
- Prefer `d.fresh_blocks` over `quote.blocks_json`, same as `autoLoadLastSession()` at line 2616

### Step 5: Backfill `category_sort_order` for old blocks
**File**: `app/static/js/user_output_editor.js` (`addBlock()`)
- If `blockData.category_sort_order` missing, leave as `null` (stable sort preserves `fresh_blocks` order)

### Step 6: Make `_build_page_blocks()` the canonical generator
**File**: `app/quote_editor_routes.py:699`
- Refactor `add_form_block()` to call `_build_page_blocks()` or share its sorting logic

---

## Target Data Flow

```
DB (page_templates.display_order)
  └─► get_builder_beta_state()  [FORM MODE, REVIEW MODE]
        └─► pages sorted by display_order

DB (category_templates.display_order)
  └─► _get_page_category_order()  [QUOTE MODE]
        └─► _build_page_blocks() sorts items by display_order
        └─► add_form_block() sorts items by display_order

DB (line_items.sort_order)
  └─► get_line_items_by_codes()  [all modes]
        └─► items sorted by sort_order
```

---

## Files to modify

1. `app/QMapp.py` — sort pages in `get_builder_beta_state()`
2. `app/quote_editor_routes.py` — sort pages in `build_quote_editor_blocks_for_all_pages()`, fix `add_form_block()` category order
3. `app/static/js/user_output_editor.js` — prefer fresh blocks on load
