# Reactive Quote Calculator UI — Implementation Plan

> **Status:** Part 1 ✅ | Part 2 ⏳ | Part 3 ⏳ | Part 4 ⏳

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

### 1.6 Quote CRUD ✅ NEW
File: `app/template_store.py`
- `create_quote()` — creates quote record with deposit/completion pct
- `save_quote_line_items()` — replaces all line items for a quote
- `save_quote_adjustments()` — replaces all adjustments
- `update_quote_totals()` — recalculates subtotal, adjustment_total, grand_total, deposit/completion amounts
- `get_quote()` — returns quote with nested line_items and adjustments
- `list_quotes()` — lists all quotes, optionally filtered by template_key
- `delete_quote()` — deletes quote (CASCADE handles children)
---

## 2. form.html — User Pricing Overrides ⏳ NEXT

### 2.1 HTML section (inside `{% if not edit_mode %}`)
For each active question block: render editable `<input>` if `allow_user_override`, else locked badge.

### 2.2 Payment schedule override
Only if `payment_schedule.allow_user_override`: editable Deposit % and Completion %.
### 2.3 JavaScript
On change -> POST to `/quote/session-override` with CSRF token.
---

## 3. review.html — Interactive Cost Matrix ⏳

### 3.1 Data passed
`line_items`, `payment_schedule`, `session_overrides` from backend.

### 3.2 HTML
Cost table, discount lines div, payment schedule with week-count dropdown.

### 3.3 JS: buildCostMatrix()
Group items by `output_group`. Editable inputs if `allow_user_override`. Compute discounts = admin_price - user_price.

### 3.4 JS: buildPaymentSchedule()
Deposit -> weekly middle payments -> completion. Recalculates on week-count or percentage change.
---

## 4. Admin Configuration UI ⏳

Panel in existing admin interface to set default percentages and override flag. Saves via `/admin/payment-schedule`.
---

## 5. Integration Steps (Order of Work)

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
| 11 | Quote CRUD functions | ✅ |
| 12 | Output group mapping (Phase 1) | ⏳ |
| 13 | Calculator engine (Phase 2) | ⏳ |
---

## 6. Testing Checklist

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
| 11 | Create quote from form | Quote record with line items + adjustments |
| 12 | Update quote totals | Subtotal, adjustment, grand recalculated |
| 13 | Delete quote | Cascade removes line items + adjustments |
