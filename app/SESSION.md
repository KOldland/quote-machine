# Active Sprint Handoff

## Workspace Structure
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session AF — COMPLETE: Secondary Questions UI logic ✅**

## Active Files for Context (next session)
* @app/templates/_builder_macros.html
* @app/static/js/builder.js
* @app/SESSION.md

## What Was Completed — Session AF (Secondary Questions UI logic)
* **Secondary Questions Tab:** Renamed the "Logic / Secondary Questions" tab to "Secondary Questions".
* **Dimension Dynamic Logic:** In the `_builder_macros.html` macro `renderEditorForm`, added JS logic to grey out and make `Default Dimension 2` and `Default Dimension 3` inputs read-only when their respective `Enable Dimension` checkboxes are unchecked.
* **Cost Override Logic:** Left `Default Unit Cost (£)` always editable in the edit mode (frontend behavior remains driven by the data).

## Immediate Next Task
### Session AH — Ready for Next Assignment

## What Was Completed — Session AG (Change Pricing Visibility)
* **Simplified Pricing Visibility:** Converted the `Pricing Visibility` setting from a three-option dropdown (`admin_only`, `user_view`, `user_edit`) into a single "Price Override Enabled" checkbox.
* **Backend Compatibility:** Ensured that the form submission correctly translates the checkbox state back to the `user_edit` (if checked) or `admin_only` (if unchecked) format expected by the database.
* **Consistency:** Applied these changes both to the primary 3-column page editor in `_builder_macros.html` and the Line Items Library canvas in `builder.js`.
