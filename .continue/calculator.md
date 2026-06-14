# Reactive Quote Calculator UI — Implementation Plan

> **Status:** Part 1 ✅ | Part 2 ✅ | Part 3 ⏳ | Part 4 ⏳
> **Phase 0+1 (Backend Prerequisites + Output Group Mapping):** ✅ Complete
> **Phase 2 (Calculator Engine):** ✅ Complete — `app/calculator.py` created and verified
> **Phase 3 (Frontend Integration):** ⏳ NEXT — form.html overrides + review.html cost matrix

## 0. Overview

Three goals:
1. **Live user price overrides** on the form, respecting `allow_user_override`.
2. **Interactive cost matrix with discounts** on the review page, grouped by cost bucket.
3. **Dynamic payment schedule with adjustable percentages**, admin-lockable.

All vanilla JS, existing Flask session endpoints, building on `builder_beta` / line-item infrastructure.

---

## 1. Backend Prerequisites ✅ COMPLETE

### 1.1 DB columns
`line_items`: `allow_user_override INTEGER DEFAULT 0`, `output_group TEXT DEFAULT 'General'`
`form_templates`: `settings_json TEXT DEFAULT '{}'`

### 1.2 POST /quote/session-override ✅
File: `app/QMapp.py` line 1824. Accepts `{question_id, value}` and `{deposit_pct, completion_pct}` into `session['overrides']`.

### 1.3 POST /admin/payment-schedule ✅
File: `app/QMapp.py` line 1844. Admin-only. Saves default percentages + `allow_user_override`.

### 1.4 template_store helpers ✅
File: `app/template_store.py` lines 1276 & 1312.
- `upsert_payment_schedule_block()` — persists to `form_templates.settings_json`
- `get_payment_schedule_block()` — reads with fallback defaults.

### 1.5 Builder beta extended ✅
`_build_block_from_schema_field` now includes `allow_user_override: False` in pricing options.
Page editor saves `pricing_allow_user_override` checkbox.

### 1.6 Output Group Mapping ✅ (Verified)
- Backfilled `output_group` into `page_schemas.json` and `category_templates`.
- Wired into `/builder_beta/line_item_save` (allowed field, line 2102).
- UI field added in Form Editor (line item + category editors).

---

## 2. Phase 3 — Frontend Integration Plan ⏳ NEXT

### Current State Summary

**Already exists:**
- ✅ `calculator.py` — fully ready with `calculate_quote()` and `save_calculated_quote()`
- ✅ `/quote/session-override` endpoint — accepts `question_id`, `value`, `deposit_pct`, `completion_pct`
- ✅ `/admin/payment-schedule` endpoint — saves defaults with `allow_user_override`
- ✅ `get_payment_schedule_block()` in template_store.py
- ✅ `pricing_options` with `allow_user_override` in builder_beta block schemas (line_items table)
- ✅ `review.html` template (Jinja) showing legacy `review_data` based output
- ✅ `form.html` with `entered` pricing mode for fields (line 593)
- ✅ `Index`, `special_notes_page`, `summary_page` routes exist

**Missing / needs creation:**
- ❌ Routes: `/materials_page`, `/further_requirements_page`, `/additional_building_work_page`, `/additional_costs_page`, `/optional_extras_page`, `/image_upload_page`, `/review`, `/submit`, `/trigger_production`, `/production-page`
- ❌ `review.html` cost matrix (interactive version)
- ❌ `form.html` price override inputs for checkbox_options with `allow_user_override=True`
- ❌ `form.html` payment schedule overrides at runtime
- ❌ Context passing (`session_overrides`, `payment_schedule`) to form/review templates
- ❌ JS handlers for price override submission and payment schedule live recalculation

### Implementation Steps

---

#### Step 5 — Update QMapp.py runtime render_template calls + create missing routes

**Files to modify:**
- `app/QMapp.py`

**Changes:**

1. **Add helper function** that gathers common context needed at runtime:
```python
def _get_runtime_quote_context():
    """Return session_overrides and payment_schedule for templates."""
    import template_store as ts
    session_overrides = session.get('overrides', {})
    payment_schedule = ts.get_payment_schedule_block(TEMPLATE_STORE_KEY)
    return {
        'session_overrides': session_overrides,
        'payment_schedule': payment_schedule,
    }
```

2. **Update all 3 existing runtime render_template calls** (index, special_notes_page, summary_page) to include `**_get_runtime_quote_context()` in the non-edit_mode branch, plus `li_detail_level` and `li_line_items`.

3. **Create the missing routes** (each following the same pattern as `special_notes_page`/`summary_page`):

   - `materials_page` — GET/POST, runtime schema-driven, redirects to `further_requirements_page`
   - `further_requirements_page` — same pattern
   - `additional_building_work_page` — same
   - `additional_costs_page` — same
   - `optional_extras_page` — same
   - `image_upload_page` — GET/POST for image uploads (cover, cgi, floorplan, site_images)
   - `review` — GET, calculates quote via `calculator.py`, renders `review.html`
   - `submit` — POST (JSON + fallback form), commits data to production, redirects to `/trigger_production`
   - `trigger_production` — GET, generates output images, redirects to `/production-page`
   - `production-page` — GET, shows final production results

---

#### Step 6 — Add price override inputs to form.html for checkbox_group options

**File:** `app/templates/form.html`

**Change:** In the checkbox_group rendering section, for each `field` in the runtime schema:
- Check if `field.builder_beta_meta.pricing_options.get('allow_user_override')` is `True`
- If so, render a small inline currency input next to each checkbox option showing the option's base price (from catalog/line_items)
- Add a `data-question-id` attribute to track the override target

**Example rendering logic:**
```html
{% if field.builder_beta_meta and field.builder_beta_meta.pricing_options.get('allow_user_override') %}
    <input type="number" step="0.01" class="override-price-input"
           data-question-id="{{ option.value }}"
           value="{{ session_overrides.get('q_' + option.value, '') }}"
           placeholder="£ price">
{% endif %}
```

---

#### Step 7 — Add payment schedule override inputs to form.html

**File:** `app/templates/form.html`

**Change:** Add a section (visible only when `payment_schedule.allow_user_override` is True) with inputs for:
- Deposit percentage
- Completion percentage

These post to `/quote/session-override` on change via JS.

---

#### Step 8 — Rewrite review.html as interactive cost matrix

**File:** `app/templates/review.html`

**Change:** Replace the static review output with an interactive cost matrix that receives from the `/review` route:
- `review_data` (legacy output mapping)
- `quote_result` (from `calculator.py`) — containing `groups`, `subtotals`, `grand_total`, `payment_schedule` data
- `session_overrides` (for pre-fill)
- `li_by_category` (line items grouped by category)

**Matrix sections:**
1. **Accordion per output_group** — each shows items with editable price fields
2. **Live subtotal** per group — recalculated via JS on price change
3. **Grand total** at the bottom
4. **Payment schedule** section with deposit/completion amounts (editable percentages)
5. **Discount/adjustment** input row
6. **"Recalculate" button** or live JS update

---

#### Step 9 — Add JS for interactive cost matrix

**File:** `app/templates/review.html` (inline `<script>`)

**JS functions:**
- `updateLineItemPrice(questionId, newPrice)` — POST to `/quote/session-override`, then re-fetch calculation or recalculate client-side
- `updatePaymentSchedule(depositPct, completionPct)` — POST to `/quote/session-override`
- `calculateTotals()` — reads all price inputs and recomputes subtotals/grand total
- `submitQuote()` — POST to `/submit` endpoint

---

#### Step 10 — Wire submit endpoint to persist + redirect

**File:** `app/QMapp.py`

**Route `/submit`:**
1. Accept JSON or form POST
2. Validate CSRF token
3. Call `calculate_quote()` + `save_calculated_quote()` to persist
4. Build `review_data` output for production
5. Return `{status: 'success'}` or redirect to `/trigger_production`

**Route `/trigger_production`:**
1. Read session data + saved quote
2. Generate final output images (call existing `compose_template()`)
3. Redirect to `/production-page`

---

### Key Data Flow

```
User checks checkbox with editable price
    -> JS reads new price input
    -> POST /quote/session-override {question_id, value}
    -> session['overrides'][f"q_{question_id}"] updated
    -> (recalc happens on next /review page load)

Review page loads
    -> /review route calls calculator.calculate_quote(
        template_key='builder_beta',
        form_data=session['checkbox_data'],
        session_overrides=session.get('overrides', {})
      )
    -> Returns groups, subtotals, grand_total, payment schedule
    -> Renders interactive cost matrix in review.html

User edits price on review page
    -> JS live-updates totals client-side
    -> On "Commit Data" -> POST /submit
    -> calculator saves quote to DB
    -> Redirect to /trigger_production
```

---

## 3. Integration Steps (Order of Work)

| Step | What | Status |
|------|------|--------|
| 1 | DB columns | ✅ |
| 2 | `/quote/session-override` endpoint | ✅ |
| 3 | `/admin/payment-schedule` endpoint | ✅ |
| 4 | upsert/get payment schedule helpers | ✅ |
| 5 | Update form view to pass blocks + overrides | ⏳ |
| 6 | Add price input section + JS to form.html | ⏳ |
| 7 | Add payment percent override + JS to form.html | ⏳ |
| 8 | Update review view to pass line_items, schedule, overrides | ⏳ |
| 9 | Rebuild review page with cost matrix + schedule JS | ⏳ |
| 10 | Add admin config panel for payment schedule | ⏳ |

---

## 4. Testing Checklist

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Admin sets allow_user_override=False | Locked badge on form |
| 2 | Admin sets allow_user_override=True | Editable input; POST fires on change |
| 3 | User reduces price in review matrix | Discount line appears with differential |
| 4 | Items grouped by output_group | Each bucket shows subtotal row |
| 5 | Admin locks payment percents | Not editable on form/review |
| 6 | Admin unlocks payment percents | User can change; schedule recalculates |
| 7 | User changes week count dropdown | Middle balance re-divided instantly |
| 8 | Admin saves new defaults | Propagates to new sessions |
| 9 | CSRF missing/invalid | Error returned; no state corruption |
| 10 | Non-numeric override input | NaN ignored; no broken fetch |
