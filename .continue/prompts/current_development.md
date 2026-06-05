# Current Development: Inline Builder Validation & Testing

## Phase Status

**Build complete. Entering testing/validation phase.** All 7 implementation steps from the build phase have been completed (archived in `current_development_comp1.md`). The inline drag-and-drop form builder is structurally integrated across all 9 page routes, with the question palette rendering in the main sidebar, three-panel layout, and visual polish applied.

---

## Expected Functionality

When an admin user is logged in and appends `?edit=1` to any form page URL, the following behaviors should hold:

1. **Sidebar Swap** — The main sidebar transitions from page navigation links to the question builder palette (question types, page selector, "+ Add Question" button, "Exit Edit Mode" button)
2. **Three-Panel Layout** — Left sidebar (palette + controls) | Center (canvas showing current page blocks) | Right (properties panel for selected block)
3. **Drag-and-Drop** — Question types from the palette can be dragged onto the canvas to create new blocks
4. **Add Question Button** — Clicking "+ Add Question" opens the type picker modal; selecting a type creates a new default block on the canvas
5. **Block Selection** — Clicking a block on the canvas selects it and populates the properties panel
6. **Properties Panel** — Selected block properties (label, required, options, etc.) can be edited and saved
7. **Page Navigation** — The page selector in edit mode navigates between form pages while preserving edit mode
8. **Exit Edit Mode** — "Exit Edit Mode" navigates to the same page without `?edit=1`, restoring normal sidebar navigation
9. **All Routes** — The above behaviors work consistently across all 9 form routes (index, special_notes_page, summary_page, materials_page, further_requirements_page, additional_costs_page, image_upload_page, additional_building_work_page, optional_extras_page)
10. **CSRF & Session** — Save operations respect CSRF protection and session state

---

## Test Protocol

The testing workflow follows a human-in-the-loop cycle:

1. **Agent opens session** — reads SESSION.md and current_development.md to align with active state
2. **Agent establishes session task** — defines what needs to be tested/fixed in this session
3. **Human provides manual testing** — runs the app server, navigates pages, performs actions, observes behavior
4. **Human reports result** — reports either **CLEAR** (test passed) or **BUG** (test failed, with description)
5. **If BUG: Agent establishes fix plan** — within the 5-request budget constraint, plans the minimal fix
6. **Agent implements fix** — uses small, precise `replace_in_file` blocks (2-3 lines); no wholesale rewrites
7. **Human retests** — runs the same test again; reports CLEAR or BUG
8. **Repeat** — steps 5-7 until resolved or budget exhausted
9. **Agent updates relevant files** — updates SESSION.md and current_development.md with results

### Budget & Scope Rules
- Each fix cycle is scoped to 1-2 bugs maximum, per the 5-request hard ceiling
- If budget is exhausted mid-fix, agent halts, reports progress, and requests manual permission to continue
- Agent never rewrites QMapp.py wholesale — only localized search-and-replace blocks

---

## Bug Triage

| Priority | Definition | Action |
|----------|-----------|--------|
| **P0** | Blocks testing pipeline; app crashes/500s on page load | Must fix immediately |
| **P1** | Major feature broken (can't drag/drop, can't save, sidebar doesn't swap) | Must fix before moving on |
| **P2** | Cosmetic (spacing, alignment, colour mismatch, missing icon) | Log for later; proceed if time allows |

---

## Testing Checklist

1. Log in as admin, navigate to any form page
2. Click "Edit Page" — verify the sidebar changes from nav links to question palette
3. Verify the canvas still shows the current page's blocks
4. Verify the properties panel still shows on the right when a block is selected
5. Drag a question type from the sidebar palette onto the canvas
6. Click "+ Add Question" — verify a new default block appears
7. Click "Save Block" in properties — verify save works
8. Click "Exit Edit Mode" — verify sidebar reverts to page nav
9. Toggle sidebar collapse/expand in both modes
10. Navigate between pages in edit mode via the page selector

---

## Exit Criteria

Testing is considered complete when:
- All 10 checklist items have been executed across at least 3 different form routes
- Zero P0 or P1 bugs remain unresolved
- Any P2 bugs are documented in SESSION.md under "Known Issues"
- SESSION.md and current_development.md have been updated with the session results

---

## Session Log

| Date | Session | Result |
|------|---------|--------|
| 04/06/26 | Validation Phase Start | **BUG (Test #3)**: Discovery of "Schema Gap". Legacy form fields are missing from Edit Mode canvas because they aren't defined in `page_schemas.json`. P0 fix applied for missing JS globals. |
| 04/06/26 | Schema Unification | **CLEAR**: Audited all routes and migrated legacy fields into `page_schemas.json` under `builder_beta`. Updated `QMapp.py` to prefer builder state in `build_page_schema_context`. Verified bootstrap state is complete across all pages. Ready for Test #3 re-run. |
| 04/06/26 | Manual Testing Resume | **BUG**: Discovery that `builder.js` and state injection were only in `form.html`, missing from the global sidebar palette in `index.html`. Interactivity (drag-and-drop) was dead. Checkbox previews in canvas were not rendering correctly due to data structure mismatches. |
| 04/06/26 | UI Interactivity Fix | **CLEAR**: Moved JS initialization to `index.html`. Fixed checkbox preview rendering. Verified that canvas and sidebar are now interactive. Ready for CRUD testing. |
| 04/06/26 | Session Handoff | **CLEAR**: Resumed project, reviewed context files, and started the Flask server. The application is ready for manual testing of CRUD functionality. |
| 04/06/26 | CRUD Testing | **BUG**: Encountered a JavaScript error (`Uncaught ReferenceError: updatePricingFields is not defined`) in `app/static/js/builder.js`. The error is caused by a function being called before it is defined. The session was interrupted before the fix could be applied. |
| 04/06/26 | Session Closeout | **INFO**: Documented the `builder.js` bug and prepared the workspace for a clean session restart. The fix for the bug has been identified and implemented, but not yet verified. |
| 04/06/26 | Bug Squashing | **CLEAR**: Fixed `updatePricingFields is not defined` JS error. Fixed `NameError: name 'edit_mode' is not defined` Python error. Restored missing save button. Drag-and-drop and reordering are now functional. Ready for save functionality testing. |
| 05/06/26 | Save Block Fix | **CLEAR**: Full save-block pipeline now working. See "Save Block Fix — Root Cause & Resolution" section below for details. |
| 05/06/26 | UX Sidebar Cleanup | **DONE**: Removed "Question Types" palette from sidebar + canvas `+ ADD QUESTION` button. Renamed "Page Controls" → "Select Page". Removed Prev/Next nav buttons. Moved Publish/Rollback to sidebar (renamed Publish/Undo). Removed yellow edit-mode banner from centre column (status label retained). Flipped properties/canvas column ratio to 2fr/1fr. Changes in: `index.html`, `_builder_macros.html`, `form.html`, `builder.js`, `main.css`. Pending manual verification on server restart. |

---

## Save Block Fix — Root Cause & Resolution

### Problem Summary
"Save Block" appeared broken: clicking the button either triggered a "Failed to save block" JS alert, or silently succeeded on the server but showed no change in the UI. A full page reload was the only way to see the saved state.

### Three Bugs Fixed (in order of discovery)

#### Bug 1 — Page reload masked the real issue
**File:** `app/static/js/builder.js`, inside the `addBlock()` callback.
**Root cause:** A `setTimeout(() => location.reload(), 300)` call was inserted broadly after every successful save, which hid the fact that the client-side state was never being updated. Removing it exposed the underlying state-sync problem.
**Fix:** Removed the unconditional `location.reload()` from the save handler. The reload on `add_block` was retained (needed to get the server-assigned block ID) but isolated to that specific action only.

#### Bug 2 — Client-side state never synced after save
**File:** `app/static/js/builder.js`, in the `blockPropertiesForm` submit handler.
**Root cause:** After a successful `fetch()` POST to the server, the local in-memory `blocks` JavaScript array was never updated. The server correctly wrote to `page_schemas.json`, but the UI re-rendered from the stale local state. On the next page load the server's saved state appeared, but live in-session it looked like nothing changed.
**Fix (Option A):** After a successful `fetch()`, read all field values directly from the `FormData` object and patch them onto the matching block object in the local `blocks` array. Then call `saveHistory()`, `renderCanvas()`, and `renderProperties()` to reflect the changes instantly. This is the recommended pattern — no extra server round-trip, no reload needed.

#### Bug 3 — `updatePricingFields is not defined` ReferenceError
**File:** `app/static/js/builder.js`.
**Root cause:** `updatePricingFields` was defined as a **function expression** assigned to `window`:
```javascript
window.updatePricingFields = function(mode) { ... }
```
This assignment is **not hoisted**. Because `renderProperties()` is called during the init sequence (before that line is reached in execution), calling `updatePricingFields(...)` inside `renderProperties()` threw a `ReferenceError`. This was the cause of the "Failed to save block" alert — the error fired inside the `try` block and was caught.
**Fix:** Changed to a **named function declaration** (which IS hoisted), then separately assigned to `window` for the inline HTML `onchange="updatePricingFields(...)"` attribute in `_builder_macros.html`:
```javascript
function updatePricingFields(mode) { ... }
window.updatePricingFields = updatePricingFields; // expose for inline HTML
```

### Null-guard for conditional pricing inputs
**File:** `app/static/js/builder.js`, in `renderProperties()`.
**Context:** Pricing inputs (`pricing_fixed_amount`, `pricing_entered_key`, etc.) are only present in the DOM when the pricing mode matches. Calling `.value =` on a `null` querySelector result throws a `TypeError`. These are now all guarded:
```javascript
const elFixedAmount = document.querySelector('input[name="pricing_fixed_amount"]');
if (elFixedAmount) elFixedAmount.value = block.pricing_options.fixed_amount;
```

### Troubleshooting Checklist (for future regressions)
If "Save Block" breaks again, check in this order:
1. **Browser console** — look for `ReferenceError` or `TypeError` in `builder.js`
2. **Is it a hoisting issue?** — any function called during init that is defined as `window.fn = function(){}` will fail
3. **Is the `blocks` array stale?** — after save, does an immediate reload show the correct state? If yes, the sync logic is missing or throwing silently
4. **Is the `try/catch` swallowing a real error?** — put a `console.error(error)` in the catch block to see the actual stack trace
5. **Is the form `action` URL null?** — `blockPropertiesForm.getAttribute("action")` must return a valid URL; if the form wasn't rendered by Flask (e.g. no block selected), the form element may not exist
