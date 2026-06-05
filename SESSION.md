# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* **Line Item Architecture Sprint — Session B**: Rework builder canvas for `line_items` — accordion view by category, properties panel with 9 editable fields, `pricing_visibility` toggle.

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
* **Session A — line_items table + CSV migration** ✅ — `line_items` table added to `template_store.py` `_create_schema()`. `scripts/migrate_line_items_from_csv.py` written and executed. 1022 rows seeded from CSV with correct suffix taxonomy (`auto_child: 245, guidance: 78, parent: 161, special: 188, standalone: 350`). Parent/child inference working.
* **Session B — Builder canvas wired** ✅ — `builder_beta.html` updated to mount `render_line_items_canvas()` + `render_line_item_properties()` macros and call `initLineItemsCanvas()` on DOMContentLoaded. Canvas now fetches categories from `/builder_beta/line_items_json`, renders accordion rows, and loads 9-field properties panel on row click. `pricing_visibility` toggle saves via `/builder_beta/line_item_save/<id>`.

## Known Issues / Bug Backlog
* None — all prior bugs resolved. Active sprint is a feature build.

## Immediate Next Task (start here on reopen)

### 🚀 Session C — `form.html` → Query `line_items` (IN PROGRESS — halted at budget)

**Context gathered:**
- DB confirmed: `form_page='3'` = materials (ew, er, id, dr, wp categories), `'3B'` = Demolition/FRC, `'3C'` = Additional Items
- `template_store.py` ends at line 743 — ready to append `get_line_items_for_page`
- `form.html` materials block approx lines 591–907; currently driven by `data['selected_ew']` / `data['selected_er']` etc. from Sheets

**Three deliverables (all described below):**

**1. `template_store.py` — append `get_line_items_for_page`**
Add at end of file (after line 743):
```python
def get_line_items_for_page(form_page: str, db_path: Optional[Path] = None) -> Dict[str, list]:
    """Return form-visible line_items for a page, grouped by category.
    Returns {category: [row_dicts]} ordered by sort_order.
    """
    path = db_path or _default_db_path()
    conn = _connect(path)
    rows = conn.execute(
        "SELECT id, line_code, category, internal_description, include_default, "
        "unit_cost, units, pricing_visibility, output_title, output_notes, output_guidance, "
        "parent_code, item_role, input_type, trigger_parent_code, form_visible, sort_order "
        "FROM line_items WHERE form_page=? AND form_visible=1 "
        "ORDER BY category ASC, sort_order ASC, line_code ASC",
        (form_page,)
    ).fetchall()
    conn.close()
    result: Dict[str, list] = {}
    for row in rows:
        cat = row["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(dict(row))
    return result
```

**2. `QMapp.py` — wire into routes**
In each form page route, call `get_line_items_for_page` and pass as `line_items_by_category`:
- `materials_page()` → `get_line_items_for_page('3')`
- `summary_page()` → `get_line_items_for_page('2')`
- `further_requirements_page()` → `get_line_items_for_page('3B')`

Add import at top of routes file if `get_line_items_for_page` is added to `template_store.py`:
```python
from template_store import get_line_items_for_page
```
Or call inline via `sqlite3` using the existing `DB_PATH` pattern already in use for builder routes.

**3. `form.html` — add line_items render block**
In the `{% if materials_page %}` section (line ~591), prepend before the existing accordion blocks:
```jinja
{# ── Session C: line_items-driven accordion rendering ── #}
{% if line_items_by_category %}
  {% for category, items in line_items_by_category.items() %}
  <div class="accordion-section">
    <button type="button" class="accordion-header"
            onclick="toggleAccordion('li_cat_{{ loop.index }}')">
      {{ category | title }}
    </button>
    <div id="li_cat_{{ loop.index }}" class="accordion-body">
      {% for item in items %}
        {% if item.item_role == 'parent' %}
        <label class="checkbox-label">
          <input type="checkbox" name="li_{{ item.form_page }}"
                 value="{{ item.line_code }}"
                 {% if item.include_default == 'Y' %}checked{% endif %}>
          <strong>{{ item.internal_description }}</strong>
        </label><br>
        {% else %}
        <label class="checkbox-label">
          <input type="checkbox" name="li_{{ item.form_page }}"
                 value="{{ item.line_code }}"
                 {% if item.include_default == 'Y' %}checked{% endif %}>
          {{ item.internal_description }}
        </label><br>
        {% endif %}
      {% endfor %}
    </div>
  </div>
  {% endfor %}
{% else %}
  {# Legacy Sheets-driven accordions below — remove once line_items data confirmed #}
```
Close the `{% else %}` block with `{% endif %}` after the final legacy accordion div (closing `{% endif %}` for materials_page).

**Next step on reopen:** Read `materials_page()` body in QMapp.py (look for `render_template` call), then make all three writes above.

### ~~Session B — Builder Canvas: `line_items` Accordions~~ ✅ COMPLETE

`builder_beta.html` reworked to mount `render_line_items_canvas()` + `render_line_item_properties()` and call `initLineItemsCanvas()` on DOMContentLoaded. Backend routes (`/builder_beta/line_items_json`, `/builder_beta/line_item_save/<id>`), JS (`initLineItemsCanvas`, `_renderAccordions`, `_selectItem`, `_renderProperties`), and macros were all pre-built; wiring was the missing piece.

### 🚀 Session C — `form.html` → Query `line_items`

Simplify `form.html` to query `line_items` by page + `form_visible=1` instead of `page_schemas.json`. Full spec in `current_development.md` under **NEW SPRINT: Line Item Architecture**, Session C.

---

### ~~Session A — `line_items` Table + CSV Migration Script~~ ✅ COMPLETE

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
