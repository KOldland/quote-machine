#!/usr/bin/env python3
"""
Re-tag legacy form_page values to current page keys.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "template_store.sqlite3"

MAPPINGS = {
    "0": "index",
    "2": "summary_page",
    "2B": "summary_page",
    "3D": "additional_building_work_page",
    "4": "additional_costs_page",
    "7": "additional_costs_page",
    "8": "additional_costs_page",
    "9": "additional_costs_page",
    "10": "image_upload_page",
    "11": "image_upload_page",
    "12": "image_upload_page",
    "13": "optional_extras_page",
    "totals": "summary_page",
    "price breakdowns": "summary_page",
}

CATEGORY_MAPPINGS = {
    "Optional Extras": "optional_extras_page",
    "Finishing Works": "optional_extras_page",
    "Finishing Works Optional Extras": "optional_extras_page",
    "Additional Notes": "summary_page",
    "dimensions": "materials_page",
    "dimension 5": "materials_page",
    "Aluminum Capping": "additional_costs_page",
    "image": "image_upload_page",
    "images": "image_upload_page",
    "price breakdowns": "summary_page",
}

PREFIX_MAPPINGS = {
    "dr": "materials_page",
    "id": "materials_page",
    "wp": "materials_page",
    "dm": "materials_page",
    "er": "materials_page",
    "ew": "materials_page",
    "fs": "materials_page",
    "ps": "materials_page",
    "dw": "further_requirements_page",
    "frc": "further_requirements_page",
    "ab": "additional_building_work_page",
    "el": "additional_costs_page",
    "pl": "additional_costs_page",
    "sk": "additional_costs_page",
    "vl": "additional_costs_page",
    "ac": "additional_costs_page",
    "sd": "additional_costs_page",
    "sn": "special_notes_page",
    "pp": "summary_page",
    "cs": "summary_page",
    "bw": "summary_page",
    "bl": "summary_page",
    "bs": "summary_page",
    "an": "summary_page",
    "img": "image_upload_page",
    "co": "summary_page",
    "gv": "additional_costs_page",
    "saw": "additional_costs_page",
}

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    total_updated = 0

    # 1. Direct form_page mappings
    for old_fp, new_fp in MAPPINGS.items():
        cur.execute(
            "UPDATE line_items SET form_page=? WHERE form_page=?",
            (new_fp, old_fp)
        )
        updated = cur.rowcount
        if updated:
            print(f"  {old_fp:20s} -> {new_fp:30s}: {updated} rows")
            total_updated += updated

    # 2. Empty/NULL form_page: map by category first, then by prefix
    cur.execute("SELECT id, line_code, category FROM line_items WHERE form_page IS NULL OR form_page = ''")
    unmapped = cur.fetchall()

    cat_updated = 0
    prefix_updated = 0
    still_unmapped = []

    for row_id, line_code, category in unmapped:
        new_fp = None
        clean_code = (line_code or "").strip().lower()

        # Try category mapping
        if category:
            cat_lower = category.lower().strip()
            for cat_key, fp in CATEGORY_MAPPINGS.items():
                if cat_lower == cat_key.lower():
                    new_fp = fp
                    break

        # Try prefix mapping
        if not new_fp:
            for prefix, fp in PREFIX_MAPPINGS.items():
                if clean_code.startswith(prefix):
                    new_fp = fp
                    break

        if new_fp:
            cur.execute("UPDATE line_items SET form_page=? WHERE id=?", (new_fp, row_id))
            if category and category.lower() in [k.lower() for k in CATEGORY_MAPPINGS]:
                cat_updated += 1
            else:
                prefix_updated += 1
        else:
            still_unmapped.append((row_id, line_code, category))

    print(f"\n  Empty form_page - category match: {cat_updated} rows")
    print(f"  Empty form_page - prefix match:  {prefix_updated} rows")
    total_updated += cat_updated + prefix_updated

    if still_unmapped:
        print(f"\n  Still unmapped: {len(still_unmapped)} rows")
        for row_id, line_code, category in still_unmapped[:20]:
            print(f"    id={row_id} code={line_code} cat={category}")

    conn.commit()

    # Verification
    print("\n=== FINAL STATE ===")
    cur.execute("SELECT form_page, COUNT(*) FROM line_items GROUP BY form_page ORDER BY form_page")
    for row in cur.fetchall():
        print(f"  {str(row[0]):30s}: {row[1]}")

    total = cur.execute("SELECT COUNT(*) FROM line_items").fetchone()[0]
    print(f"\nTotal line_items: {total}")
    print(f"Total updated: {total_updated}")

    conn.close()

if __name__ == "__main__":
    main()
