# Active Sprint Handoff

## Workspace Structure
* **VS Code workspace root**: `/Users/krisoldland/Documents/QM_web_app/`
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`
* **GitHub Repository**: `https://github.com/KOldland/quote-machine`

## Current Goal
* Fix sidebar collapse bug in edit mode (P1), then begin Block Properties deep-dive sprint.

## Active Files for Context
* @app/static/js/builder.js
* @app/templates/_builder_macros.html
* @app/templates/index.html
* @app/templates/form.html
* @app/static/css/main.css
* @app/SESSION.md
* @app/.continue/prompts/current_development.md

## What Was Completed (05/06/26 — CRUD Testing Sprint)
* **Items 1–8, 10 CLEAR** — all core CRUD flows verified: login, edit mode entry, canvas render, properties panel, add question, save block, exit edit mode, page navigation.
* **Item 6** ✅ — "+ Add Question" modal opens and creates a new block on canvas.
* **Item 8** ✅ — "Exit Edit Mode" reverts sidebar and strips `?edit=1` from URL.
* **Item 10** ✅ — "Select Page" dropdown navigates between pages while preserving edit mode.
* **Testing phase 9/10 complete** — one item remains (sidebar collapse in edit mode).

## Known Issues / Bug Backlog

| Priority | Issue | File(s) |
|----------|-------|---------|
| **P1** | Sidebar does not fully collapse in edit mode. Normal mode works fine. Clicking the hamburger (≡) partially collapses but content remains visible. | `app/templates/index.html`, `app/static/js/builder.js`, `app/static/css/main.css` |
| **P2** | "Select Page" `<details>` element is slightly narrower than Add Question / Publish / Undo / Exit buttons on the right. | `app/static/css/main.css` |

## Immediate Next Task (start here on reopen)
1. **Fix sidebar collapse in edit mode (P1)**:
   - Inspect the sidebar collapse toggle — likely a CSS class conflict or a JS condition that skips collapse when `edit_mode` is active.
   - Check `builder.js` for the hamburger click handler and any guard that might prevent collapse.
   - Check `main.css` for `.sidebar-collapsed` rules — confirm they apply in edit mode layout too.
   - Fix and verify collapse works in both normal and edit modes.
2. **Fix Select Page button width (P2)** — ensure `<details>` element matches sibling button widths exactly.
3. **Begin Block Properties sprint** — this is the next major work area. Agreed with user that Block Properties panel needs significant work (exact scope to be defined at start of next session).

## Session Log Summary
| Date | Items | Result |
|------|-------|--------|
| 05/06/26 | #1–5, #7 | All CLEAR |
| 05/06/26 | #6, #8, #10 | All CLEAR |
| 05/06/26 | #9 | BUG — sidebar collapse broken in edit mode |
