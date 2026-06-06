# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session M: Verify + Stabilise 3-Column Canvas** — Boot the server, confirm `/materials_page?edit=1` and `/further_requirements_page?edit=1` render the 3-column canvas, click through the section list, View One question list, and View Two editor; fix any rendering issues found.

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/templates/_builder_macros.html
* @app/static/js/builder.js
* @app/template_store.py
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session K**: Cleaned up deprecated standalone builder routes in `QMapp.py`. All tests pass. Committed as `bf9d5ea`.
* **Session L**: Full 3-column line-item editor canvas implemented. Committed as `6afd05c`.
* **Session M**: Patched `page_schemas.json` to enable the 3-column canvas. Verified that the canvas renders and all interactive features (section navigation, question list, editor, save/back buttons) are working correctly on both `/materials_page` and `/further_requirements_page`.

## Exact Stopping Point
* Session M completed. The 3-column canvas is stable and verified in the browser.

## Immediate Next Task (start here on reopen)
### Session N — Next Steps
* Define the next development goal.

### Known Potential Issues to Watch
* If `li_categories` is an empty list (no `line_items_by_category` block configured in `page_schemas.json`), the canvas will show the legacy block builder — not a bug, by design
* Jinja2 deprecation: `opt_pricing.get(...)` calls in `form.html` require Jinja2 ≥ 3.0 (mapping `.get()` method)
* CSRF token: JS reads `document.querySelector('[name=csrf_token]')` — works because `<input type="hidden" name="csrf_token">` is injected at top of 3-col canvas
