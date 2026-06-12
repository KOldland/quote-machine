# Reactive Quote Calculator UI – Implementation Plan

## 0. Overview

We will modify two user‑facing templates (`form.html` and `review.html`) and add one small admin‑settings panel to achieve three goals:

1. **Live user price overrides** on the form, respecting `allow_user_override`.
2. **Interactive cost matrix with discounts** on the review page, grouped by cost bucket.
3. **Dynamic payment schedule with adjustable percentages**, where the admin can lock/unlock the deposit and completion percentages.

Everything stays within vanilla JavaScript, uses existing Flask session endpoints, and builds on the current `builder_beta` / line‑item infrastructure already visible in `form.html`.

### Files to modify
| File | Change |
|------|--------|
| `app/QMapp.py` | Add 2 new endpoints |
| `app/templates/form.html` | Add price override inputs + payment % override section |
| `app/templates/review.html` | Rebuild as dynamic cost matrix + payment schedule |
| `app/templates/admin_config.html` (new or existing) | Payment schedule defaults panel |
| Database: `question_templates` | Ensure `allow_user_override` and `output_group` columns exist |

---

## 1. Backend Prerequisites

### 1.1 Database columns
Ensure `question_templates` table has:
- `allow_user_override INTEGER DEFAULT 0`
- `output_group TEXT DEFAULT 'General'`

If missing, run a migration script or use the admin schema patching pattern already in the project (see `patch_add_category_fix.py` etc.).

### 1.2 New endpoint: `POST /quote/session-override`
**File:** `app/QMapp.py`

**Purpose:** Accept JSON payloads for both question‑level price overrides and payment‑schedule parameter overrides.

**Logic:**
- Receive JSON body.
- If `question_id` + `value` present → store in `session['overrides'][f"q_{question_id}"]`.
- If `deposit_pct` present → store in `session['overrides']['deposit_pct']`.
- If `completion_pct` present → store in `session['overrides']['completion_pct']`.
- Mark session modified, return `{success: true}`.

### 1.3 New endpoint: `POST /admin/payment-schedule`
**File:** `app/QMapp.py`

**Purpose:** Save default percentages and the `allow_user_override` flag into `builder_beta` (or a dedicated settings table).

**Logic:**
- Receive `deposit_pct`, `completion_pct`, `allow_user_override`.
- Persist into a `payment_schedule` block within `builder_beta`.
- Return `{success: true}`.

### 1.4 Updated view functions
**Form view:** Pass `active_question_blocks` (questions with pricing) and `session_overrides` to the template.
**Review view:** Pass `line_items` (structured list of chargeable items), `payment_schedule`, and `session_overrides`.

---

## 2. `form.html` – User Pricing Overrides

### 2.1 HTML section (inside `{% if not edit_mode %}` block)
Place after the line-item accordions, before the navigation buttons.

For each active question block:
```django
<div class="form-price-row" data-question-id="{{ block.question_id }}">
    <label>{{ block.description }}</label>
    {% if block.allow_user_override %}
        <input type="number" step="0.01" class="price-input"
               value="{{ session_overrides.get('q_' + block.question_id, block.default_price) }}">
    {% else %}
        <span class="price-badge">{{ block.default_price | currency }}</span>
    {% endif %}
</div>
```

### 2.2 Payment schedule override (below price inputs)
Only rendered if `payment_schedule.allow_user_override` is true:
```django
{% if payment_schedule.allow_user_override %}
<div class="payment-percentage-override">
    <label>Deposit %: <input type="number" id="user-deposit-pct" class="pct-input"
           value="{{ (session_overrides.get('deposit_pct', payment_schedule.deposit_pct)) * 100 }}"
           step="0.1" min="0" max="100" data-field="deposit_pct"></label>
    <label>Completion %: <input type="number" id="user-completion-pct" class="pct-input"
           value="{{ (session_overrides.get('completion_pct', payment_schedule.completion_pct)) * 100 }}"
           step="0.1" min="0" max="100" data-field="completion_pct"></label>
</div>
{% endif %}
```

### 2.3 JavaScript
Attach to DOMContentLoaded (add to existing script block):
- On `.price-input` change → POST `{question_id, value}` to `/quote/session-override`.
- On `.pct-input` change → POST `{[field]: value/100}` to `/quote/session-override`.
- Use existing CSRF token from hidden input.

---

## 3. `review.html` – Interactive Cost Matrix

### 3.1 Data passed from backend
```python
line_items = [...]          # list of dicts: {id, description, admin_price,
                            #   user_price, group, allow_user_override}
payment_schedule = {        # from builder_beta
    'deposit_pct': 0.10,
    'completion_pct': 0.10,
    'allow_user_override': True/False
}
session_overrides = session.get('overrides', {})
```

### 3.2 HTML structure
Replace the current static review accordion with:
```html
<div id="review-matrix">
  <table id="cost-table">
    <thead>
      <tr><th>Item</th><th>Admin Price</th><th>Your Price</th><th>Subtotal</th></tr>
    </thead>
    <tbody id="cost-body"></tbody>
  </table>

  <div id="discount-lines"></div>

  <div id="payment-schedule">
    <h4>Payment Schedule</h4>
    <label>Number of Payment Weeks:
      <select id="num-weeks">
        <option value="4">4</option>
        <option value="8">8</option>
        <option value="12" selected>12</option>
        <option value="16">16</option>
        <option value="24">24</option>
      </select>
    </label>
    <table id="schedule-table">
      <thead><tr><th>Milestone</th><th>Amount</th></tr></thead>
      <tbody id="schedule-body"></tbody>
    </table>
  </div>
</div>
```

### 3.3 JavaScript matrix rendering (`buildCostMatrix()`)
**Algorithm:**
1. Group `lineItems` by `group` property (`'Uncategorized'` fallback).
2. For each group:
   - Insert a bold header row.
   - For each item:
     - Determine effective price = `overrides[`q_${item.id}`] ?? item.user_price ?? item.admin_price`.
     - Calculate differential `diff = item.admin_price - effectivePrice`.
     - Render row with editable `<input>` if `allow_user_override`, else locked text.
     - Add to group subtotal.
     - If `diff > 0`, push to `discounts[]`.
   - Insert group subtotal row.
3. Render discount lines in `#discount-lines` (itemized list with formatted currency).
4. Attach change listeners to `.matrix-price-input` elements.
5. On price change → update `overrides` in memory, POST to `/quote/session-override`, re-render matrix and schedule.

### 3.4 Payment schedule rendering (`buildPaymentSchedule()`)
**Algorithm:**
1. Compute `total` = sum of all effective user prices.
2. Get `depositPct` and `completionPct` from overrides or defaults.
3. `middlePct = 1 - depositPct - completionPct`.
4. `deposit = total * depositPct`, `completion = total * completionPct`.
5. `middleBalance = total * middlePct`, `weekly = middleBalance / numWeeks`.
6. Render rows: Deposit → Week 1..N → Completion.
7. Attach change listener to `#num-weeks` dropdown → re-render schedule.
8. If percentages are overridable, render editable `<input>` fields and re-render on change.

### 3.5 Helper: `formatCurrency(value)`
Use `Intl.NumberFormat('en-US', {style:'currency', currency:'GBP'})` for consistent display.

---

## 4. Admin Configuration UI

### 4.1 Placement
Add a panel inside the existing admin edit interface (e.g., as a new section in `builder_beta.html` or a dedicated admin settings template).

### 4.2 HTML snippet
```html
<div class="admin-payment-config">
    <h4>Payment Schedule Defaults</h4>
    <label>Deposit %: 
      <input type="number" id="admin-deposit-pct" 
             value="{{ ps.deposit_pct * 100 }}" step="0.1" min="0" max="100">
    </label>
    <label>Completion %: 
      <input type="number" id="admin-completion-pct" 
             value="{{ ps.completion_pct * 100 }}" step="0.1" min="0" max="100">
    </label>
    <label>
      <input type="checkbox" id="admin-allow-override" 
             {% if ps.allow_user_override %}checked{% endif %}>
      Allow user to override percentages
    </label>
    <button id="save-payment-defaults">Save</button>
</div>
```

### 4.3 JavaScript
On `#save-payment-defaults` click:
- Read values, convert percentages to decimals.
- POST to `/admin/payment-schedule` with `{deposit_pct, completion_pct, allow_user_override}`.
- Show confirmation toast.

---

## 5. Integration Steps (Order of Work)

| Step | What | Who/Where |
|------|------|-----------|
| 1 | Add/verify `allow_user_override` and `output_group` columns in `question_templates` | DB migration |
| 2 | Add `POST /quote/session-override` endpoint | `app/QMapp.py` |
| 3 | Add `POST /admin/payment-schedule` endpoint | `app/QMapp.py` |
| 4 | Update form view to pass `active_question_blocks` + `session_overrides` | `app/QMapp.py` (form route) |
| 5 | Add price input section + JS to `form.html` | `app/templates/form.html` |
| 6 | Add payment % override section + JS to `form.html` | `app/templates/form.html` |
| 7 | Update review view to pass `line_items`, `payment_schedule`, `session_overrides` | `app/QMapp.py` (review route) |
| 8 | Rebuild review page with cost matrix + schedule JS | `app/templates/review.html` |
| 9 | Add admin config panel for payment schedule | Admin template |
| 10 | End-to-end testing per checklist below | Manual / QA |

---

## 6. Testing Checklist

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Admin sets `allow_user_override=False` for a question | Field appears as a **locked badge** on the form (no input). |
| 2 | Admin sets `allow_user_override=True` for a question | Field is an **editable number input**; changing it fires a POST to `/quote/session-override`. |
| 3 | User reduces a price in the review matrix | A **discount line** appears with the calculated differential (Admin − User). |
| 4 | Items grouped by `output_group` in review | Each cost bucket shows a **subtotal row** with correct sum. |
| 5 | Admin sets `allow_user_override=False` for payment %s | Percentages are **not editable** on form or review. Only the default locked values shown. |
| 6 | Admin sets `allow_user_override=True` for payment %s | User can **change percentages** on form; review schedule recalculates instantly with those values. |
| 7 | User changes the "Number of Payment Weeks" dropdown | Middle 80% balance is **divided equally** by the new week count; schedule re-renders without page reload. |
| 8 | Admin saves new default percentages via admin panel | Saved values propagate to new sessions; existing sessions keep their overrides. |
| 9 | CSRF token missing/invalid | Fetch POST returns error; no state corrupted. |
| 10 | User enters non-numeric value in override field | Change event ignores invalid input (NaN guard); no broken fetch. |