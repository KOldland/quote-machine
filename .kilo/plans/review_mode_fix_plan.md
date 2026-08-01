# Plan: Fix Review Mode (strip calculator, fix review_data, align to UX flow)

## Context

**Intended user workflow:**
Login → Load saved template/form → Complete form → **Review entries** → **Calculator Mode** (confirm/adjust pricing) → Image Upload → (future) Quote Builder.

**Current reality:**
- `GET /review` (QMapp.py:3082) eagerly calls `calculator.calculate_quote('builder_beta', ...)` (line 3099).
  - The calculator runs `SELECT ... FROM line_items WHERE form_page = ?` with `form_page='builder_beta'`.
  - **No line_item has `form_page='builder_beta'`** — items are keyed by individual page IDs
    (`additional_building_work_page`, `materials_page`, `optional_extras_page`,
    `special_notes_page`, `summary_page`, `additional_costs_page`, `further_requirements_page`).
  - Result: `items=[]`, `subtotals={}`, `groups=[]` → `li_by_category={}` → "Selected Line
    Items" accordion hidden; `totals_by_group={}` (falsy) → Cost-Summary table hidden but its
    accordion **header still renders with an empty body** = the empty accordion.
  - Verified live on the running server (`http://127.0.0.1:5003/review`).
- `review()` does NOT need the calculator at all. Per the UX flow, pricing belongs to a
  **separate Calculator Mode** page (which does not exist yet). Review's only job is to let the
  user check their form entries.
- The form-answers data is shaped wrong: route builds
  `review_data[page_title] = {'fields':[...], 'page_id':...}` but `review.html` (lines 8-43)
  iterates `items.items()` expecting `{field_name: [values]}`. Current render emits raw Python
  dict reprs + a `page_id:` line instead of `Label: value1, value2`.
- The form-answers loop iterates `page_schemas.get('pages', {})` (the 2 top-level `pages`
  entries that have NO `title`) instead of `get_builder_beta_state()['pages']` (all 9 titled
  builder-beta pages). So 7 pages are skipped and headers show raw IDs.

## Out of scope for this plan (explicitly deferred)

- Building the standalone **Calculator Mode** page (`/calculator` route + template). That is a
  separate future task. It will be the new home of the cost matrix, line items, and overrides.
- The "Update Overrides" wiring (no `<form>` on the matrix; POST dumps `og_*` into
  `checkbox_data` instead of `session['overrides']`) — belongs to Calculator Mode.

## Step-by-step plan (Review page only)

### Step 1 — Strip the calculator out of `review()` (read-only intent check first)

In `review()` (QMapp.py:3082):
- Remove the `calculator.calculate_quote(...)` call (line 3099) and the
  `subtotals`/`grand_total` override math (lines 3097-3117).
- Remove `li_by_category` construction (lines 3188-3207) — no longer a Review concern.
- Remove `export_html`/`session['quote_html']` rendering of `export.html` (lines 3122-3144) —
  that is Quote-Builder/export territory, not Review. (Confirm nothing else reads
  `session['quote_html']` before removing; if consumers exist, keep it computed but it is
  currently only used by export routes — verify in Step 0.)
- Keep `ctx = _get_runtime_quote_context()` if the template still references client_name etc.
  (Review.html currently does not display client info in the visible section, but keep ctx
  available; harmless.)

### Step 2 — Fix `review_data` structure + iterate all 9 builder-beta pages

Replace the page-source loop:
- FROM: `for page_id, page_info in page_schemas.get('pages', {}).items():`
- TO: `for page_id, page_info in get_builder_beta_state().get('pages', {}).items():`

Rebuild `review_data` so each section maps `{field_name: value}` directly:
```python
review_data = {}
session_data = session.get('data', {})
checkbox_data = session.get('checkbox_data', {})

for page_id, page_info in get_builder_beta_state().get('pages', {}).items():
    compiled_page = compile_builder_beta_page_to_runtime_schema(page_id)
    if not compiled_page:
        continue
    section = {}
    for field in compiled_page.get('fields', []):
        field_name = field.get('name')
        if not field_name:
            continue
        # value lookup: flat session data, then checkbox_data (dict or scalar)
        value = session_data.get(field_name)
        if not value:
            cb_val = checkbox_data.get(field_name)
            if isinstance(cb_val, dict):
                value = cb_val.get('preselected', [])
            elif cb_val:
                value = cb_val
            else:
                value = []
        # Only include fields that have a value (per template intent: non-empty)
        if value:
            section[field_name] = value if isinstance(value, list) else [value]
    if section:
        # page_info here comes from builder-beta state which HAS 'title'
        title = page_info.get('title') or page_id.replace('_', ' ').title()
        review_data[title] = section
```
- Skip non-entrant pages that are not user "answer" pages for review: `index` (Project Details —
  its client_address/Date live in `session['data']` and are shown in the site header/quote ctx,
  but *could* be a small "Project Details" section; decide: include as a tiny section OR rely
  on header). Keep `image_upload_page` (not an answers page — skip; it's an upload step).
  Decision point: iterate pages but only render those whose compiled fields yield selections.
- `TITLE_MAPPING` construction (lines 3210-3218) is kept as-is; it already maps
  `field_name -> label`. Note: for `accordion_group` blocks `compile_builder_beta_page_to_runtime_schema`
  sets label to `[beta:accordion_group] <label>` — that `[beta:...]` prefix should be stripped
  for Review display (decide: clean the label in the mapping, or it's cosmetic). Keep minimal:
  map field_name -> `field.get('label')` and strip the `[beta:...]` prefix.

### Step 3 — Rewrite `review.html` to Review-only (no pricing)

Edit `templates/review.html`:
- Keep: heading "Review Your Submission".
- Keep: the `{% for section, items in review_data.items() %}` accordion loop (lines 8-43) —
  this now yields correct `{field_name: [values]}` sections. Verify the `items is mapping`
  branch renders fine (it will, since each section is a dict of field_name->list).
- **Remove** the "Selected Line Items" accordion (lines 48-76) — moves to Calculator Mode.
- **Remove** the "Cost Summary & Payment Schedule" accordion + table (lines 78-113) —
  moves to Calculator Mode.
- **Remove** the `<button type="submit" class="btn btn-primary mt-2">Update Overrides</button>`
  (was line 110) — belongs to Calculator Mode.
- Replace the button bar: keep "Previous" (`window.history.back()`), change "Next" to
  point at the next stage per your flow. Since Calculator Mode is not built yet, set "Next"
  to `url_for('image_upload_page')` for now BUT relabel it to reflect the real next step once
  `/calculator` exists. (Document this as a TODO in the template via a comment.)
- Confirm `toggleAccordion`, `.accordion-section`/`.accordion-body` CSS, and `script.js`
  already support the remaining sections (they do).

### Step 4 — Keep the GET-only `review()` POST branch consistent

`review()` POST (lines 3087-3094) currently persists checkbox changes by dumping
`request.form` into `checkbox_data` and redirects to GET. With the calculator removed this
POST branch is still valid for "edit checkbox in review" (Test 6 step 6). Keep it, but
ensure it does NOT pollute `checkbox_data` with stray non-checkbox keys. Minimal change:
filter form keys to known field names, or just keep dumping (low risk for now). Decision:
keep existing behavior for now (it already works for persistence); note the `og_*`
pollution issue is gone once the matrix is removed from this template.

### Step 5 — Update navigation chain in the builder-beta payload

Per your flow the real order is `…form pages… -> review -> calculator -> image_upload_page`.
Today `image_upload_page.next_endpoint = 'review'`. Two options:
  - (A) Leave payload nav as-is for now and just fix the **on-page** Next button in
    `review.html` (Step 3) to go to the next stage; accept that the form-page "Save &
        Continue" from the last form page still lands on Review (good).
  - (B) Rewire `image_upload_page` to follow `review` (i.e. form -> review happens
        before image upload). This is a payload/DB edit.

Decision: go with (A) for the immediate fix — change the Review "Next" button target and
leave the page-template `next_endpoint` chain untouched until Calculator Mode exists.

### Step 6 — Verify

- Run the app and hit `/review` with a populated session (use Flask test client or complete
  the form via the browser) and confirm:
  - Only per-section answer accordions render (titled, not raw IDs).
  - Each section shows `Human Label: value1, value2` (no raw dict reprs).
  - The empty "Cost Summary" accordion is **gone**.
  - "Previous" / "Next" buttons work.
- Re-run `git diff` to confirm only `QMapp.py` (review route) and `templates/review.html`
  changed.
- Run lint/typecheck if configured (check `AGENTS.md` / `package.json` scripts).

## Acceptance criteria

- `/review` no longer renders the empty Cost-Summary accordion.
- `/review` no longer calls `calculator.calculate_quote`.
- `/review` renders titled sections from ALL builder-beta answer pages, each showing
  `field label -> selected values` (matching the template's `{field_name: [values]}` contract).
- No raw Python dicts / `page_id:` lines appear in the output.
- Navigation buttons are correct for the post-review next stage.
