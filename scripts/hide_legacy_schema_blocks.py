#!/usr/bin/env python3
"""
Session F fix: Mark all accordion_group blocks on materials_page and
further_requirements_page as hidden=true so that the legacy schema
checkboxes are suppressed from the runtime form. The new line_items_by_category
section (DB-driven) is now the sole renderer for these pages' content.

Run once: python3 app/scripts/hide_legacy_schema_blocks.py
"""
import json, os

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'page_schemas.json')

TARGET_PAGES = ['materials_page', 'further_requirements_page']

with open(SCHEMA_PATH, 'r') as f:
    schema = json.load(f)

pages = schema['builder_beta']['pages']
changed = []

for page_id in TARGET_PAGES:
    page = pages.get(page_id, {})
    for block in page.get('blocks', []):
        if block.get('block_type') == 'accordion_group' and not block.get('hidden', False):
            block['hidden'] = True
            changed.append(f"  {page_id} → {block['id']} ({block['standard']['label']})")

with open(SCHEMA_PATH, 'w') as f:
    json.dump(schema, f, indent=2)

print(f"Done — {len(changed)} block(s) marked hidden:")
for c in changed:
    print(c)
