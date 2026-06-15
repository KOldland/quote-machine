# Reactive Quote Calculator UI — Implementation Plan

> **Status:** Part 1 ✅ | Part 2 ✅ | Part 3 ⏳ | Part 4 ⏳
> **Phase 0+1 (Backend Prerequisites + Output Group Mapping):** ✅ Complete
> **Phase 2 (Calculator Engine):** ✅ Complete — `app/calculator.py` created and verified ✅ COMPLETE
> **Phase 3 (Frontend Integration):** ⏳ NEXT — form.html overrides + review.html cost matrix

## 0. Overview

Three goals:
1. **Live user price overrides** on the form, respecting `allow_user_override`.
2. **Interactive cost matrix with discounts** on the review page, grouped by cost bucket.
3. **Dynamic payment schedule with adjustable percentages**, admin-lockable.

All vanilla JS, existing Flask session endpoints, building on `builder_beta` / line-item infrastructure.

---

## 1. Backend Prerequisites ✅ COMPLETE

## 2. Phase 3 — Frontend Integration Plan ✅ COMPLETE

#### Step 5 — Update QMapp.py runtime render_template calls + create missing routes ✅ COMPLETE

#### Step 6 — Add price override inputs to form.html for checkbox_group options ✅ COMPLETE

#### Step 7 — Add payment schedule override inputs to form.html ✅ COMPLETE

#### Step 8 — Rewrite review.html as interactive cost matrix ✅ COMPLETE

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
| 5 | Update form view to pass blocks + overrides | ✅ |
| 6 | Add price input section + JS to form.html | ✅  |
| 7 | Add payment percent override + JS to form.html |  ✅ |
| 8 | Update review view to pass line_items, schedule, overrides |  ✅ |
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
