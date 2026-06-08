import re

# Update current_development.md
with open('app/.continue/prompts/current_development.md', 'r') as f:
    content = f.read()

content = content.replace(
    "- Execute Step 1 and Step 2: Update the `template_store.py` schema creation logic and refactor the `page_schemas.json` structure.",
    "- [x] Execute Step 1 and Step 2: Update the `template_store.py` schema creation logic and refactor the `page_schemas.json` structure."
)

with open('app/.continue/prompts/current_development.md', 'w') as f:
    f.write(content)

# Update SESSION.md
session_content = """# Active Sprint Handoff

## Workspace Structure
* **Git repo root**: `/Users/krisoldland/Documents/QM_web_app/app/`
* **Branch**: `master`

## Current Goal
* **Session AI — COMPLETE: Formalize Pages and Categories in Schema ✅**

## Active Files for Context (next session)
* @app/template_store.py
* @app/QMapp.py
* @app/templates/_builder_macros.html
* @app/static/js/builder.js

## What Was Completed — Session AI
* **Database Schema Update:** Added `category_templates` table in `template_store.py`.
* **Data Integration:** Parsed and inserted categories natively into `category_templates` linked via `page_template_id`.
* **JSON Schema Refactor:** Migrated the `categories` array out of `line_items_by_category` blocks directly into root page configurations across `page_schemas.json` and `page_schemas_published.json`.

## Immediate Next Task
### Session AJ — Integrate Schema Changes into Backend Logic and UI
Update `QMapp.py` data retrieval to query `category_templates` rather than dynamically extracting unique strings from `line_items`. Plan UI components for managing Categories (add, rename, move, reorder). See `current_development.md` for details.
"""
with open('app/SESSION.md', 'w') as f:
    f.write(session_content)

print("Files updated.")
