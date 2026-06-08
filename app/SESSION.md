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
### Session AG — Change Pricing Visibility
1. Modify the `Pricing Visibility` setting within the `Costs` tab of the question builder in edit mode.