"""Give every page a real ``line_items_by_category`` block in ``question_templates``.

Why this exists
---------------
The form renders categories/questions from a page's *blocks*. Blocks live in
``question_templates.metadata_json``. Several pages carry ``line_items`` (and
``category_templates``) but no block row at all, so
``compile_builder_beta_page_to_runtime_schema`` had to synthesise a
``line_items_by_category`` field on the fly as a safety net.

That fallback works, but it means those pages depend on a defensive branch in the
request path rather than on real data. This script writes the block row they
should have had, matching the shape the other pages already use:

    question_key  = '<page_key>__line_items'
    question_type = 'unknown'
    metadata_json = {"block_type": "line_items_by_category",
                     "config": {}, "id": "<page_key>__line_items"}

so the rendered output is unchanged but no longer fallback-dependent.

Idempotent: a page that already has a ``line_items_by_category`` block is left
alone. The runtime fallback is intentionally NOT removed - it stays as a safety
net for pages created in future. Back up the database before running.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "template_store.sqlite3"
TEMPLATE_KEY = "builder_beta"

# Pages the builder UI does not expose.
EXCLUDED_PAGES = {"index", "image_upload_page"}


def _latest_version_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute(
        """
        SELECT ftv.id
        FROM form_template_versions ftv
        JOIN form_templates ft ON ft.id = ftv.form_template_id
        WHERE ft.key = ?
        ORDER BY ftv.version DESC
        LIMIT 1
        """,
        (TEMPLATE_KEY,),
    ).fetchone()
    return int(row[0]) if row else None


def _find_gaps(conn: sqlite3.Connection, version_id: int) -> list[sqlite3.Row]:
    """Pages with line_items but no line_items_by_category block."""
    return conn.execute(
        """
        SELECT p.page_key, p.id AS page_template_id, p.title,
               (SELECT COUNT(*) FROM line_items li
                 WHERE li.form_page = p.page_key) AS items
        FROM page_templates p
        WHERE p.form_template_version_id = ?
          AND p.page_key NOT IN ({excluded})
          AND EXISTS (
              SELECT 1 FROM line_items li WHERE li.form_page = p.page_key
          )
        ORDER BY p.page_key
        """.format(excluded=",".join("?" * len(EXCLUDED_PAGES))),
        (version_id, *sorted(EXCLUDED_PAGES)),
    ).fetchall()


def _has_li_block(conn: sqlite3.Connection, page_template_id: int) -> bool:
    rows = conn.execute(
        "SELECT metadata_json FROM question_templates WHERE page_template_id = ?",
        (page_template_id,),
    ).fetchall()
    for r in rows:
        try:
            if json.loads(r[0] or "{}").get("block_type") == "line_items_by_category":
                return True
        except (TypeError, ValueError):
            continue
    return False


def main() -> int:
    apply_changes = "--apply" in sys.argv
    mode = "APPLY" if apply_changes else "DRY-RUN"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        version_id = _latest_version_id(conn)
        if version_id is None:
            print(f"No {TEMPLATE_KEY} template found.")
            return 1

        gaps = _find_gaps(conn, version_id)
        if not gaps:
            print(f"[{mode}] Every page with line_items already has a block.")
            return 0

        print(f"[{mode}] {TEMPLATE_KEY} latest version id = {version_id}")
        print(f"[{mode}] {len(gaps)} page(s) need a line_items block:\n")

        planned: list[tuple[int, str, int]] = []
        for gap in gaps:
            if _has_li_block(conn, gap["page_template_id"]):
                print(f"  {gap['page_key']:<32} already has a block - skipping")
                continue
            key = f"{gap['page_key']}__line_items"
            meta = json.dumps(
                {"block_type": "line_items_by_category", "config": {}, "id": key}
            )
            planned.append((gap["page_template_id"], key, gap["items"]))
            print(
                f"  {gap['page_key']:<32} + {key}"
                f"  (page_template_id={gap['page_template_id']}, {gap['items']} items)"
            )

        if not planned:
            print("\nNothing to do.")
            return 0

        if not apply_changes:
            print("\nDry run only. Re-run with --apply to write these changes.")
            return 0

        for page_template_id, key, _items in planned:
            conn.execute(
                """
                INSERT INTO question_templates (
                    page_template_id, question_key, question_type, label,
                    storage_key, display_order, metadata_json
                ) VALUES (?, ?, 'unknown', '', '', 0, ?)
                """,
                (page_template_id, key, json.dumps(
                    {"block_type": "line_items_by_category", "config": {}, "id": key}
                )),
            )
        conn.commit()
        print(f"\nInserted {len(planned)} block row(s).")
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR, rolled back: {exc}")
        return 1
    finally:
        conn.close()

    print("Done. Restart Flask to load the changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
