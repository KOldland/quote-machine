"""
Phase 1 — Schema Migration: promote checkbox_group blocks that carry a
source_prefix to block_type "accordion_group" and add an empty sub_blocks list.

Idempotent: safe to re-run. Already-promoted blocks are left untouched.

Writes updated data back to both:
  - page_schemas.json
  - page_schemas_published.json
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)

SCHEMAS = [
    os.path.join(APP_DIR, "page_schemas.json"),
    os.path.join(APP_DIR, "page_schemas_published.json"),
]


def migrate(data: dict) -> tuple[dict, int]:
    """Return (mutated_data, count_of_promotions)."""
    promoted = 0
    for schema_key, schema_val in data.items():
        pages = schema_val.get("pages", {})
        for page_id, page in pages.items():
            for block in page.get("blocks", []):
                source_prefix = block.get("standard", {}).get("source_prefix", "")
                if block.get("block_type") == "checkbox_group" and source_prefix:
                    block["block_type"] = "accordion_group"
                    if "sub_blocks" not in block:
                        block["sub_blocks"] = []
                    promoted += 1
    return data, promoted


def main():
    for path in SCHEMAS:
        if not os.path.exists(path):
            print(f"  SKIP (not found): {path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data, count = migrate(data)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"  OK — {count} block(s) promoted → {os.path.basename(path)}")


if __name__ == "__main__":
    main()
