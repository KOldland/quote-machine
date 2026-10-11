# Quote Machine — Do List (deferred / needs decisions)

Last updated: 5 Oct 2026

Worked through and shipped this round: category image button, add-category error
surfacing, payment-schedule layout, merge-tag braces, larger-text-box question
type, move-question-between-categories.

---

## 1. Pricing matrix (item 2) — BACKEND READY, UI MISSING

**Status:** half-built. The save + calculate halves exist; the builder UI was
never written, so it cannot be used. Not a rollback casualty — the UI has never
existed in git history.

**What already works**

| Layer | Location | State |
|---|---|---|
| Calculate | `calculator.py:346` (`pricing_mode == "matrix"`) | done — types x sizes lookup |
| Save | `QMapp.py:1028-1057` | done — reads `pricing_matrix_types`, `pricing_matrix_sizes`, `pricing_matrix_prices` |
| Allow-list | `QMapp.py:691` — `'matrix'` in `ALLOWED_BLOCK_PRICING_MODES` | done |
| **Builder UI** | `_builder_macros.html`, `builder.js` | **zero references — missing** |
| Data | DB | nothing uses it; only `per_unit` (489), `per_selection` (15), `per_unit_rate` (1) |

**To build:** a pricing-mode option in the block pricing panel, plus type/size
row + column editors feeding the three form fields the save handler already reads.

**Decisions needed before starting**
- Single dropdown selection that indexes the matrix, or two (type then size)?
  The calculator already supports **both** shapes (1 dropdown and 2 dropdowns), so
  which does the UI expose — or both?
- How should matrix cells be entered: spreadsheet-style grid, or one-per-line
  JSON as `pricing_matrix_prices` currently expects?
- Should matrix pricing be available on blocks only, or on questions/categories
  too? (`line_items` has `pricing_mode` but no matrix handling today.)

---

## 2. Cost group CRUD (item 4) — NEEDS INPUT

**Status:** `output_group` exists on both `line_items` and `category_templates`
but is **free text**, defaults to `'General'`, and **every row in the DB is
`'General'`**. There is no managed list anywhere.

**Current touch points**
- Category editor: free-text input `cat_output_group` (`_builder_macros.html:1160`)
- Block editor: free-text `output_options.group` (`_builder_macros.html:175`)
- Add-category modal: free-text "Cost group" input
- Save: `category_details_save` / `line_item_save` pass the string through

**Open questions**
1. Managed global list (like question types in `DEFAULT_BUILDER_BETA_QUESTION_TYPES`)
   or free text with a datalist of existing values?
2. On rename, cascade to every row using the old name, or only affect new choices?
3. Do groups need ordering, a description, or other metadata?
4. Per-page, or shared across the whole quote?
5. Should a deleted group be blocked while rows still reference it, or remap those rows?

---

## 3. Calculator pages (item 6) — NEEDS SCOPING

**Status:** not started. Could not scope this from the codebase.

**Open questions**
1. What is a "calculator page"? Candidates:
   - a page that totals the selected items from another page (prelims/summary), or
   - a page that exposes pricing configuration, or
   - something that emits a subtotal into the quote output
2. New **page type**, or a question/block type usable on any existing page?
3. Does it produce an output line, an output group, or a single summary figure?
4. Live-recalculate as selections change, or calculate on save/continue?
5. Does it need its own pricing rules, or reuse the calculator engine as-is?

---

## Carried-over risks (not do-list items, but worth remembering)

- **5 pages have zero `question_templates`** — `schedule_of_works`, `contingency`,
  `finishing_works`, `additional_notes`, `pricing_categories`. They render only via
  the `line_items_by_category` fallback in
  `compile_builder_beta_page_to_runtime_schema`. That fallback is load-bearing:
  remove it and those five pages show "No form fields configured" again.
- **All of this is still uncommitted.** Commit before the next concurrent edit.
- **Two interpreters in play** — `start_flask.sh` and the `venv/bin/python -m flask`
  command are different processes; template edits can appear "missing" if the other
  one is serving. Standardise on one.

