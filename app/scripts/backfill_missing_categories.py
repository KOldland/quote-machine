"""Backfill category_templates rows for pages that have line_items but no categories.

Root cause
----------
Build Mode writes two independent stores:

  * ``category_templates`` + ``line_items``  (SQLite - the builder UI)
  * ``blocks``                              (page_schemas.json - the form view)

Some pages were seeded before ``category_templates`` existed, so they hold
``line_items`` with no category rows at all. Two things follow:

  1. ``/builder_beta/line_item_add`` refuses new questions, because it validates
     the category against ``category_templates`` before inserting.
  2. ``get_line_items_for_page`` silently falls back to grouping by the
     ``line_items.category`` string (sorted alphabetically), so the builder shows
     an "implied" category that has no real row behind it.

This script materialises the missing rows from the category values already
present on ``line_items``, so the builder's implied categories and the database
agree. It also updates ``page_schemas.json`` so a later quick-save/payload
rebuild does not drop them again.

Idempotent: existing categories are never modified or reordered, and re-running
is a no-op. Back up the database before running.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "template_store.sqlite3"
SCHEMA_PATH = APP_DIR / "page_schemas.json"
TEMPLATE_KEY = "builder_beta"

# Pages the builder UI does not expose (sidebar filters these out).
EXCLUDED_PAGES = {"index", "image_upload_page"}


def latest_version_id(conn: sqlite3.Connection, template_key: str) -> int | None:
    row = conn.execute(
        """
        SELECT ftv.id
        FROM form_template_versions ftv
        JOIN form_templates ft ON ft.id = ftv.form_template_id
        WHERE ft.key = ?
        ORDER BY ftv.version DESC
        LIMIT 1
        """,
        (template_key,),
    ).fetchone()
    return int(row["id"]) if row else None


def find_gaps(conn: sqlite3.Connection, version_id: int) -> list[sqlite3.Row]:
    """Pages with line_items but no category_templates rows."""
    return conn.execute(
        """
        SELECT p.page_key, p.id AS page_template_id, p.title
        FROM page_templates p
        WHERE p.form_template_version_id = ?
          AND p.page_key NOT IN ({excluded})
          AND EXISTS (
              SELECT 1 FROM line_items li WHERE li.form_page = p.page_key
          )
          AND NOT EXISTS (
              SELECT 1 FROM category_templates c
              WHERE c.page_template_id = p.id
          )
        ORDER BY p.page_key
        """.format(excluded=",".join("?" * len(EXCLUDED_PAGES))),
        (version_id, *sorted(EXCLUDED_PAGES)),
    ).fetchall()


def categories_for_page(conn: sqlite3.Connection, page_key: str) -> list[sqlite3.Row]:
    """Distinct category values on this page's line_items.

    Ordered to match ``get_line_items_for_page``'s own fallback (alphabetical),
    so the rendered form order does not change once real rows exist.
    """
    return conn.execute(
        """
        SELECT li.category, MIN(li.output_group) AS output_group
        FROM line_items li
        WHERE li.form_page = ? AND li.category IS NOT NULL AND TRIM(li.category) != ''
        GROUP BY li.category
        ORDER BY li.category ASC
        """,
        (page_key,),
    ).fetchall()


def sync_schema_json(db_cats: dict[str, list[dict]], apply: bool) -> int:
    """Add any DB categories that are missing from page_schemas.json.

    The file nests pages under 'builder_beta' -> 'pages'; older files also had a
    top-level 'pages'. Both structures are updated when present. Returns the
    number of pages changed.
    """
    if not SCHEMA_PATH.exists():
        print(f"  (no {SCHEMA_PATH.name} to update)")
        return 0

    with SCHEMA_PATH.open() as fh:
        schemas = json.load(fh)

    page_maps = []
    if isinstance(schemas.get("pages"), dict):
        page_maps.append(schemas["pages"])
    bb = schemas.get("builder_beta")
    if isinstance(bb, dict) and isinstance(bb.get("pages"), dict):
        page_maps.append(bb["pages"])

    changed: set[str] = set()
    for pages in page_maps:
        for page_key, entries in db_cats.items():
            page = pages.get(page_key)
            if not isinstance(page, dict) or not entries:
                continue
            existing = {
                c.get("name")
                for c in page.get("categories", [])
                if isinstance(c, dict)
            }
            added = [e for e in entries if e["name"] not in existing]
            if added:
                print(f"      {page_key}: + {added}")
                page.setdefault("categories", []).extend(added)
                changed.add(page_key)

    if changed and apply:
        with SCHEMA_PATH.open("w") as fh:
            json.dump(schemas, fh, indent=2)
    return len(changed)


def main() -> int:
    apply_changes = "--apply" in sys.argv
    sync_json = "--sync-json" in sys.argv
    mode = "APPLY" if apply_changes else "DRY-RUN"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        version_id = latest_version_id(conn, TEMPLATE_KEY)
        if version_id is None:
            print(f"No {TEMPLATE_KEY} template found.")
            return 1

        # --sync-json: reconcile builder_beta.pages[].categories from the DB.
        # Safe to run any time; only adds categories that are missing in JSON.
        if sync_json:
            db_cats: dict[str, list[dict]] = {}
            rows = conn.execute(
                """
                SELECT p.page_key, c.name, c.display_order, c.description
                FROM category_templates c
                JOIN page_templates p ON p.id = c.page_template_id
                WHERE p.form_template_version_id = ?
                """,
                (version_id,),
            ).fetchall()
            for r in rows:
                db_cats.setdefault(r["page_key"], []).append(
                    {
                        "name": r["name"],
                        "sort_order": r["display_order"],
                        "description": r["description"] or "",
                    }
                )
            for entries in db_cats.values():
                entries.sort(key=lambda e: e["sort_order"])

            n = sync_schema_json(db_cats, apply=apply_changes)
            print(f"  {n} page(s) {'updated' if apply_changes else 'would update'} in page_schemas.json")
            if not apply_changes:
                print("Dry run only. Re-run with --apply to write these changes.")
            return 0

        gaps = find_gaps(conn, version_id)
        if not gaps:
            print(f"[{mode}] No pages missing categories. Nothing to do.")
            return 0

        print(f"[{mode}] {TEMPLATE_KEY} latest version id = {version_id}")
        print(f"[{mode}] {len(gaps)} page(s) need category backfill:\n")

        planned: dict[str, list[dict]] = {}
        for gap in gaps:
            cats = categories_for_page(conn, gap["page_key"])
            planned[gap["page_key"]] = [
                {
                    "name": c["category"],
                    "sort_order": i,
                    "description": "",
                    "output_group": c["output_group"] or "General",
                }
                for i, c in enumerate(cats)
            ]
            total = conn.execute(
                "SELECT COUNT(*) c FROM line_items WHERE form_page = ?",
                (gap["page_key"],),
            ).fetchone()["c"]
            print(f"  {gap['page_key']} ({gap['title']}) - {total} line items")
            for entry in planned[gap["page_key"]]:
                print(
                    f"      + {entry['name']!r}"
                    f"  sort_order={entry['sort_order']}"
                    f"  output_group={entry['output_group']!r}"
                )
            if not cats:
                print("      (no usable category values - skipped)")
            print()

        if not apply_changes:
            print("Dry run only. Re-run with --apply to write these changes.")
            return 0

        for gap in gaps:
            entries = planned[gap["page_key"]]
            if not entries:
                continue
            for entry in entries:
                conn.execute(
                    """
                    INSERT INTO category_templates (
                        form_template_version_id, page_template_id, name,
                        display_order, description, output_group
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id,
                        gap["page_template_id"],
                        entry["name"],
                        entry["sort_order"],
                        entry["description"],
                        entry["output_group"],
                    ),
                )
            print(f"  inserted {len(entries)} category row(s) for {gap['page_key']}")

        conn.commit()
    finally:
        conn.close()

    # Keep page_schemas.json in step so a payload rebuild does not lose these.
    sync_schema_json(planned, apply=apply_changes)

    print("\nDone. Restart Flask to load the changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
