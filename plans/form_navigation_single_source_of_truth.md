# Form Navigation Single Source of Truth

## Overview
The form flow currently uses three disconnected sources of truth:
1. **Sidebar order**: SQLite `page_templates.display_order`
2. **Form navigation**: `page_schemas.json` `navigation.next_endpoint`/`previous_endpoint`
3. **First page**: Alphabetical sort of `page_schemas.json` keys (buggy)

This causes drift between what the admin builds, what the sidebar shows, and how the form navigates.

**Goal**: Make `display_order` the single source of truth. Admin builder order = sidebar order = form navigation order.

---
## Phase 1: Fix First Step (Continue Button)

### 1.1 Fix `index()` Continue redirect
**File:** `app/QMapp.py:2542-2572`

Replace:
```python
dynamic_page_ids = [pid for pid in sorted(pages.keys()) if pid != 'index']
first_dynamic_page = dynamic_page_ids[0] if dynamic_page_ids else None
```

With logic that reads the first non-`index` page from `db_pages` (already injected into template context via `inject_ui_context()`).

**Approach**: In `index()`, call `get_all_pages()` directly to get the ordered list, or derive from `db_pages` passed through template context.

### 1.2 Validate behavior
- Confirm that when there are no dynamic pages, it falls back to `/review` (already implemented).

---
## Phase 2: Sync Navigation into Runtime State

### 2.1 Inject `display_order` into builder state
**File:** `app/QMapp.py:558-610` (`get_builder_beta_state()`)

After loading pages from schema/DB, enrich each page dict with `display_order` from SQLite `page_templates` table.

```python
# After populating pages
ordered_pages = get_all_pages(template_key=TEMPLATE_STORE_KEY)
for pg in ordered_pages:
    pid = pg['page_key']
    if pid in pages:
        pages[pid]['display_order'] = pg['display_order']
```

This keeps runtime page dicts self-contained for navigation logic.

### 2.2 Rewrite navigation resolution
**File:** `app/QMapp.py:995-1016` (`resolve_builder_beta_navigation_targets()`)

Remove dependency on `navigation.next_endpoint`/`previous_endpoint`.

New logic:
1. Build a list of all valid page IDs sorted by `display_order`
2. Find the index of `page_id`
3. `previous_page_id` = item at `index-1` if exists
4. `next_page_id` = item at `index+1` if exists
5. Fall back to `navigation.next_endpoint`/`previous_endpoint` only if `display_order` is missing (backward compatibility)

---
## Phase 3: Fix Dynamic Page Navigation

### 3.1 Fix `dynamic_page()` POST redirect
**File:** `app/QMapp.py:2457-2461`

Replace:
```python
nav = resolve_builder_beta_navigation_targets(page_id, page_schema)
next_page = nav.get('next_page_id')
if next_page and next_page in all_pages:
    return redirect(url_for('dynamic_page', page_id=next_page))
return redirect(url_for('review'))
```

With the updated `resolve_builder_beta_navigation_targets()` that uses `display_order`.

### 3.2 Fix hardcoded image upload navigation
**File:** `app/QMapp.py:3043-3044`

Replace hardcoded:
```python
previous_page='optional_extras_page',
next_page='review',
```

With values derived from the page's position in the `display_order` chain.

---
## Phase 4: Add Page Reorder Control for Admins

### 4.1 Add page reorder endpoint
**File:** `app/QMapp.py` (near `/builder_beta/swap_order` at line 2035)

Extend `/builder_beta/swap_order` with `scope=page`, or create a new endpoint:

```
POST /builder_beta/page/reorder
Body: {"page_key": "special_notes_page", "direction": "up"}
```

Logic:
- Find the target page's current `display_order`
- Find the adjacent page in that direction
- Swap their `display_order` values in SQLite `page_templates`
- Return success

### 4.2 Add reorder UI in admin sidebar
**File:** `app/templates/index.html` (edit-mode page list, around line 32-45)

Add up/down arrow buttons next to each page title:

```html
<div class="page-selector-item-wrapper">
  <a href="/{{ page.page_key }}?edit=1" class="page-selector-item">{{ page.title }}</a>
  <button class="page-reorder-btn" data-page="{{ page.page_key }}" data-dir="up">▲</button>
  <button class="page-reorder-btn" data-page="{{ page.page_key }}" data-dir="down">▼</button>
</div>
```

Add JS to call the reorder endpoint and reload the page on success.

---
## Phase 5: Auto-Sync Navigation Metadata (Optional Safety)

### 5.1 Regenerate `navigation` on reorder
**File:** `app/QMapp.py` (in reorder endpoint)

After swapping `display_order`, update `page_schemas['pages'][page_key]['navigation']` to reflect the new chain, and persist via `save_page_schemas()`.

This keeps the JSON schema consistent for any legacy code that still reads `navigation.next_endpoint`.

---
## Phase 6: Fix Hardcoded Builder References

### 6.1 Builder beta page editor navigation
**File:** `app/templates/_builder_macros.html` and related routes

Check if any builder preview/edit navigation uses hardcoded page keys instead of derived order.

---
## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `app/QMapp.py` | Modify | Fix `index()` continue redirect (1.1) |
| `app/QMapp.py` | Modify | Inject `display_order` into builder state (2.1) |
| `app/QMapp.py` | Modify | Rewrite `resolve_builder_beta_navigation_targets()` (2.2) |
| `app/QMapp.py` | Modify | Fix `dynamic_page()` POST redirect (3.1) |
| `app/QMapp.py` | Modify | Fix hardcoded image upload navigation (3.2) |
| `app/QMapp.py` | Modify | Add page reorder endpoint (4.1) |
| `app/QMapp.py` | Modify | Auto-sync navigation metadata (5.1) |
| `app/templates/index.html` | Modify | Add reorder buttons in edit-mode sidebar (4.2) |

---
## Implementation Order

1. **Phase 1**: Fix Continue button first — quickest win, validates `db_pages` ordering works
2. **Phase 2**: Inject `display_order` and rewrite navigation resolution — core fix
3. **Phase 3**: Fix `dynamic_page()` and image upload — complete form flow
4. **Phase 4**: Add page reorder UI/endpoint — give admin control
5. **Phase 5**: Auto-sync navigation metadata — safety net for legacy code
6. **Phase 6**: Fix any remaining hardcoded references

---
## Testing Checklist

- [ ] Continue button on `/` goes to first page by `display_order`
- [ ] Sidebar lists pages in `display_order` order
- [ ] Save/Continue on each page goes to next page by `display_order`
- [ ] Last page redirects to `/review`
- [ ] Image upload page navigation matches `display_order`
- [ ] Admin can reorder pages up/down in edit mode
- [ ] Reorder persists after server restart
- [ ] Form flow, sidebar, and builder mode all show identical page order
- [ ] No 404s or broken navigation after reorder
