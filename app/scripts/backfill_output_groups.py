"""
Backfill script for Phase 1: Output Group Mapping.

Sets output_group on existing line_items based on their category name.
Default rule: output_group = category (verbatim), with 'General' fallback.

Also updates category_templates to include output_group from page_schemas.json
category objects (or defaults to 'General' for legacy string-only categories).

Usage:
    cd /Users/krisoldland/Documents/QM_web_app
    python3 app/scripts/backfill_output_groups.py
"""

import sqlite3
import json
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "template_store.sqlite3"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "page_schemas.json"


def backfill_line_items(conn: sqlite3.Connection) -> int:
    """Set output_group = category for all line_items where output_group is 'General'."""
    rows = conn.execute(
        "SELECT id, category, output_group FROM line_items"
    ).fetchall()

    updated = 0
    for row in rows:
        item_id, category, current_group = row
        if current_group and current_group != "General":
            continue  # already has a non-default group
        new_group = category if category else "General"
        conn.execute(
            "UPDATE line_items SET output_group = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_group, item_id),
        )
        updated += 1

    return updated


def backfill_category_templates(conn: sqlite3.Connection) -> int:
    """Read page_schemas.json and update category_templates with output_group."""
    if not SCHEMA_PATH.exists():
        print(f"Schema file not found: {SCHEMA_PATH}")
        return 0

    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    pages = schema.get("builder_beta", {}).get("pages", {})
    updated = 0

    for page_key, page_data in pages.items():
        categories = page_data.get("categories", [])
        if not isinstance(categories, list):
            continue

        for cat in categories:
            if isinstance(cat, dict):
                cat_name = cat.get("name", "")
                output_group = cat.get("output_group", "General")
            elif isinstance(cat, str):
                cat_name = cat
                output_group = "General"
            else:
                continue

            if not cat_name:
                continue

            conn.execute(
                "UPDATE category_templates SET output_group = ? WHERE name = ? AND output_group IS NULL",
                (output_group, cat_name),
            )
            updated += conn.total_changes

    return updated


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))

    # Ensure output_group column exists in category_templates
    cols = [row[1] for row in conn.execute("PRAGMA table_info(category_templates)").fetchall()]
    if "output_group" not in cols:
        conn.execute("ALTER TABLE category_templates ADD COLUMN output_group TEXT DEFAULT 'General'")
        print("Added output_group column to category_templates")

    li_updated = backfill_line_items(conn)
    print(f"Backfilled {li_updated} line_items with output_group = category")

    ct_updated = backfill_category_templates(conn)
    print(f"Updated {ct_updated} category_templates with output_group from schema")

    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()