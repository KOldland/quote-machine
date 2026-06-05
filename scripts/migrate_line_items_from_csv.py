"""
migrate_line_items_from_csv.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Seeds the `line_items` table in template_store.sqlite3 from the Google Sheet CSV export.

Source CSV (0-indexed columns):
  0  form_page
  1  line_code
  2  category
  3  internal_description
  4  include_default
  5  unit_cost
  6  units
  7  total_cost          (skip)
  8  Summed_Totals       (skip)
  9  Dimension           (skip)
  10 output_title
  11 Calculations        (skip)
  12 output_notes
  13 output_guidance

Suffix taxonomy → item_role + form_visible:
  #  → parent,      form_visible=1
  ^  → standalone,  form_visible=1
  a/b/c (no *)  → auto_child,  form_visible=0
  *  → guidance,    form_visible=0
  @  → special,     form_visible=0
  (none) → standalone, form_visible=1

Run from the repo root:
  python3 app/scripts/migrate_line_items_from_csv.py
"""

import csv
import os
import re
import sqlite3
from pathlib import Path
from typing import Optional

# ─── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
CSV_PATH = APP_DIR / "context_archive " / "Plus Rooms Live input in doc formatting (back up) - Sheet1.csv"
DB_PATH = Path(os.getenv("QM_TEMPLATE_DB_PATH", "")).expanduser().resolve() if os.getenv("QM_TEMPLATE_DB_PATH") else APP_DIR / "template_store.sqlite3"


# ─── Suffix Taxonomy ─────────────────────────────────────────────────────────

def classify_code(raw_code: str):
    """Return (clean_code, item_role, form_visible) for a raw line code."""
    code = raw_code.strip()

    if code.endswith("#"):
        return code, "parent", 1

    if code.endswith("^"):
        return code, "standalone", 1

    if code.endswith("*"):
        return code, "guidance", 0

    if code.endswith("@"):
        return code, "special", 0

    # Trailing a/b/c/d/e (letters only, no special chars) → auto_child
    if re.search(r"[a-z]$", code, re.IGNORECASE) and re.search(r"\d", code):
        # Only classify as auto_child if the base (strip trailing alpha) resolves
        # to a known parent pattern — we use the heuristic: digit + trailing letter(s)
        if re.search(r"\d[a-z]+$", code, re.IGNORECASE):
            return code, "auto_child", 0

    # Default
    return code, "standalone", 1


def infer_parent_code(clean_code: str, parent_set: set) -> Optional[str]:
    """
    Strip trailing alpha chars from code, append '#', check if that exists
    in parent_set.  e.g. 'sn1a' → 'sn1#'
    """
    base = re.sub(r"[a-z]+$", "", clean_code, flags=re.IGNORECASE)
    if not base:
        return None
    candidate = base + "#"
    return candidate if candidate in parent_set else None


# ─── Unit Cost Cleaner ────────────────────────────────────────────────────────

def parse_unit_cost(raw: str) -> float:
    cleaned = raw.strip().lstrip("£").replace(",", "").strip()
    if not cleaned or cleaned in ("-", "N/A", "n/a"):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_units(raw: str) -> float:
    cleaned = raw.strip().replace(",", "").strip()
    if not cleaned or cleaned in ("-", "N/A", "n/a"):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Run the app once to initialise template_store.sqlite3 first."
        )

    # ── Pass 1: Read all rows and classify ───────────────────────────────────
    raw_rows = []
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)  # skip header row
        for row in reader:
            # Pad short rows to avoid index errors
            while len(row) < 14:
                row.append("")
            raw_rows.append(row)

    print(f"CSV rows read (excl. header): {len(raw_rows)}")

    # Build parent set first (all codes ending with #)
    parent_set: set = set()
    for row in raw_rows:
        raw_code = row[1].strip()
        if raw_code.endswith("#"):
            parent_set.add(raw_code)

    # ── Pass 2: Build insert list ─────────────────────────────────────────────
    records = []
    role_counts: dict = {}

    for sort_idx, row in enumerate(raw_rows):
        raw_code = row[1].strip()
        if not raw_code:
            continue  # skip blank code rows

        clean_code, item_role, form_visible = classify_code(raw_code)

        form_page            = row[0].strip() or None
        category             = row[2].strip() or "Uncategorised"
        internal_description = row[3].strip() or None
        include_default      = row[4].strip().upper() or "N"
        if include_default not in ("Y", "N"):
            include_default = "N"
        unit_cost            = parse_unit_cost(row[5])
        units                = parse_units(row[6])
        output_title         = row[10].strip() or None
        output_notes         = row[12].strip() or None
        output_guidance      = row[13].strip() or None

        # Parent inference
        parent_code = None
        if item_role == "auto_child":
            parent_code = infer_parent_code(clean_code, parent_set)

        records.append((
            clean_code,
            form_page,
            category,
            internal_description,
            include_default,
            unit_cost,
            units,
            output_title,
            output_notes,
            output_guidance,
            parent_code,
            item_role,
            form_visible,
            sort_idx,
        ))

        role_counts[item_role] = role_counts.get(item_role, 0) + 1

    print(f"Records to insert: {len(records)}")

    # ── Pass 3: Insert into DB ────────────────────────────────────────────────
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Ensure table exists (idempotent — schema may already be present)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS line_items (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            line_code            TEXT NOT NULL UNIQUE,
            form_page            TEXT,
            category             TEXT NOT NULL,
            internal_description TEXT,
            include_default      TEXT NOT NULL DEFAULT 'N',
            unit_cost            REAL DEFAULT 0.0,
            units                REAL DEFAULT 0.0,
            pricing_visibility   TEXT NOT NULL DEFAULT 'admin_only',
            output_title         TEXT,
            output_notes         TEXT,
            output_guidance      TEXT,
            parent_code          TEXT,
            item_role            TEXT NOT NULL DEFAULT 'standalone',
            input_type           TEXT,
            trigger_parent_code  TEXT,
            form_visible         INTEGER NOT NULL DEFAULT 1,
            sort_order           INTEGER NOT NULL DEFAULT 0,
            created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at           DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    insert_sql = """
        INSERT INTO line_items (
            line_code, form_page, category, internal_description,
            include_default, unit_cost, units,
            output_title, output_notes, output_guidance,
            parent_code, item_role, form_visible, sort_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(line_code) DO UPDATE SET
            form_page            = excluded.form_page,
            category             = excluded.category,
            internal_description = excluded.internal_description,
            include_default      = excluded.include_default,
            unit_cost            = excluded.unit_cost,
            units                = excluded.units,
            output_title         = excluded.output_title,
            output_notes         = excluded.output_notes,
            output_guidance      = excluded.output_guidance,
            parent_code          = excluded.parent_code,
            item_role            = excluded.item_role,
            form_visible         = excluded.form_visible,
            sort_order           = excluded.sort_order,
            updated_at           = CURRENT_TIMESTAMP
    """

    inserted = 0
    with conn:
        for rec in records:
            conn.execute(insert_sql, rec)
            inserted += 1

    final_count = conn.execute("SELECT COUNT(*) FROM line_items").fetchone()[0]
    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n=== line_items Migration Summary ===")
    print(f"  Rows processed : {len(records)}")
    print(f"  Rows in DB now : {final_count}")
    print("\n  item_role distribution:")
    for role, count in sorted(role_counts.items()):
        print(f"    {role:<15} {count:>4}")
    print("\n✅ Migration complete.")


if __name__ == "__main__":
    main()
