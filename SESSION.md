# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session S** — Next development milestone (TBD).

## Active Files for Context
* @app/QMapp.py
* @app/templates/form.html
* @app/page_schemas.json
* @app/scripts/smoke_routes.py
* @app/.continue/prompts/current_development.md
* @app/SESSION.md

## What Was Completed Recently
* **Session P**: Refactored `summary_page` to unified schema-driven handler (commit `62533cb`).
* **Session Q**: Refactored `materials_page` — 231 lines removed (commit `5f676d3`).
* **Session Q (complete)**: Refactored `further_requirements_page` — 224 lines of legacy session-handling removed, replaced with 17-line slim unified handler. py_compile EXIT:0 (commit `d7d6831`).
* **Tooling**: Added shell quote escaping pitfall to `context.md` — always write temp `.py` script file instead of `python3 -c "..."`.
* **Session R (complete)**: Smoke test passed — all 6 refactored pages return 200/302. Zero 500 errors. All routes verified via `smoke_routes.py` and `flask.log`.

## Exact Stopping Point
* Session R complete. All 6 pages smoke-tested green. Ready for next milestone.

## Immediate Next Task (start here on reopen)
* Define next feature or fix. Review `current_development.md` for backlog items.

### Known Potential Issues to Watch
* If `li_categories` is empty, canvas falls back to legacy block builder — by design
* Jinja2 deprecation: `opt_pricing.get(...)` in `form.html` requires Jinja2 ≥ 3.0
* CSRF token: JS reads `document.querySelector('[name=csrf_token]')` — works via hidden input at top of 3-col canvas
* **Never use `replace_in_file` on `QMapp.py`** — use write-to-temp-script pattern (see `context.md`)
* **Shell quote escaping**: Never `python3 -c "..."` for multiline edits — write a temp `.py` file and execute it
