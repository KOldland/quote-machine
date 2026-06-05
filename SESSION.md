# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* **Line Item Architecture Sprint — Session D**: Build output generator — reads Y-flagged `line_items` per submission, groups by category, emits title / notes / guidance + pricing totals.

## Active Files for Context
* @app/template_store.py
* @app/QMapp.py
* @app/templates/form.html
* @app/static/js/builder.js
* @app/templates/_builder_macros.html
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

## Known Issues / Bug Backlog
* None — all prior bugs resolved. Active sprint is a feature build.

## Immediate Next Task (start here on reopen)

### 🚀 Session D — Output Generator

**Goal:** When a form is submitted, read the user-selected `li_sel[]` values from POST, look up their `line_items` rows, group by `category`, and emit structured output (title / notes / guidance + pricing totals) alongside existing output.

**Deliverables:**

**1. `template_store.py` — add `get_line_items_by_codes(codes: list)`**
```python
def get_line_items_by_codes(codes: list, db_path=None) -> list:
    """Return full line_item rows for a list of line_codes, ordered by category + sort_order."""
    path = db_path or _default_db_path()
    conn = _connect(path)
    placeholders = ','.join('?' * len(codes))
    rows = conn.execute(
        f"SELECT * FROM line_items WHERE line_code IN ({placeholders}) "
        "ORDER BY category ASC, sort_order ASC, line_code ASC",
        codes
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

**2. `QMapp.py` — collect `li_sel` in POST handlers**
In `materials_page()` POST branch (and `further_requirements_page()`), collect:
```python
li_sel = request.form.getlist('li_sel')
session['li_sel'] = li_sel
```

**3. `QMapp.py` — wire into output/review route**
In `review_page()` (or wherever output is built), call:
```python
from template_store import get_line_items_by_codes
li_codes = session.get('li_sel', [])
li_output_rows = get_line_items_by_codes(li_codes) if li_codes else []
# group by category for template rendering
li_by_category = {}
for row in li_output_rows:
    li_by_category.setdefault(row['category'], []).append(row)
```
Pass `li_by_category` to `render_template('review.html', ...)`.

**4. `review.html` — render line_items output section**
Add a section that loops `li_by_category` and renders output_title / output_notes / unit_cost grouped by category.

---

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
