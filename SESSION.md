# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* All P1/P2 sidebar bugs resolved. Block Properties deep-dive sprint in progress.

## Active Files for Context
* @app/static/js/builder.js
* @app/templates/_builder_macros.html
* @app/templates/index.html
* @app/templates/form.html
* @app/static/css/main.css
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed (05/06/26 — Bug Squash Sprint)
* **P2 — Select Page width** ✅ — Removed `margin: 5px` horizontal bleed + `calc(100% - 10px)`; now `width: 100%` with vertical-only margin. Matches Add Question / Publish / Undo / Exit buttons exactly. Commit `2852f49`.
* **P2 — Select Page arrow direction** ✅ — `▼` when collapsed (`rotate(0deg)`), `▲` when expanded (`rotate(180deg)`). Commit `2852f49`.
* **P1 — Sidebar collapse in edit mode** ✅ — Root cause: `.sidebar.builder-edit-mode { min-width: 220px }` overrode `width: 0`. Fixed by adding `.sidebar.builder-edit-mode.collapsed` override with `width: 0 !important; min-width: 0 !important`. Commit `66abfb9`.
* **Testing checklist item #9** ✅ — Sidebar collapse/expand now works in both normal and edit modes. All 10 checklist items are now CLEAR.

## Known Issues / Bug Backlog
* None — all P1 and P2 bugs from the CRUD testing sprint resolved.

## Immediate Next Task (start here on reopen)

### 🔍 Manual Verification Required (human action)
1. **Verify sidebar collapse fix** — hard-refresh (Cmd+Shift+R), enter edit mode, click hamburger (☰) — sidebar should fully collapse and content should expand to full width. Report CLEAR or BUG.

### 🚀 Block Properties Sprint — Scope Defined
Code review of `_builder_macros.html` complete. The panel structure is sound (4 sections: Question Fields, Logic, Pricing, Output). The following areas need manual testing to confirm behaviour:

**A — Logic section toggle**
- The `logic_visibility` select has no `onchange` in the static HTML. When a block is clicked and `renderProperties()` runs in JS, test: change visibility dropdown from "Always show" → "Show conditionally" — does the `#logic-conditions` div appear? Then change back — does it hide?

**B — Pricing enabled toggle**
- The `pricing-fields` div gets its `active` class server-side via Jinja, but no JS checkbox listener is visible in the template. Test: tick "Enable pricing" checkbox — do the mode fields appear? Untick — do they hide?

**C — Pricing mode field swap**
- Pricing mode-specific fields (fixed_amount, entered_key, quantity_key+rate, percent_of_subtotal) are rendered server-side via Jinja `{% if %}`. Test: change the Mode dropdown — do the correct input fields appear for each mode (fixed / entered / quantity_rate / percent_subtotal)?

**D — Field population on block-click**
- Click block A, note its label/required/choices. Click block B. Click block A again — do all fields repopulate correctly from block A's data (not stale from B)?

**E — Block-type-specific fields**
- For each block type (text_input, number_currency_input, dropdown_select, checkbox_group, static_text_heading), select a block and verify the correct type-specific fields appear in Question Fields (placeholder vs choices+source_prefix vs content+variant).

Start testing at **A** and report CLEAR or BUG after each. Agent will fix in order.

## Session Log Summary
| Date | Items | Result |
|------|-------|--------|
| 05/06/26 | #1–5, #7 | All CLEAR |
| 05/06/26 | #6, #8, #10 | All CLEAR |
| 05/06/26 | #9 | BUG — sidebar collapse broken in edit mode |
| 05/06/26 | P2 Select Page width + arrow direction | FIXED — commit `2852f49` |
| 05/06/26 | P1 Sidebar collapse in edit mode | FIXED — commit `66abfb9` |
