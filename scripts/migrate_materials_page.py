"""
migrate_materials_page.py
Re-tag all materials_page line items from legacy form_page='3' to 'materials_page'.
Also fixes category case mismatch and normalises stray dm% rows.
"""
import sqlite3

DB_PATH = "app/template_store.sqlite3"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# --- 1. Re-tag all form_page='3' rows with materials prefixes ---
prefixes = ["dr", "id", "wp", "dm", "er", "ew", "fs", "ps"]
for prefix in prefixes:
    cur.execute(
        "UPDATE line_items SET form_page='materials_page' "
        "WHERE form_page='3' AND line_code LIKE ?",
        (f"{prefix}%",)
    )
    print(f"  [{prefix}%] from '3' -> 'materials_page': {cur.rowcount} rows")

# --- 2. Fix case mismatch: 'Internal Doors' -> 'Internal doors' ---
cur.execute(
    "UPDATE line_items SET category='Internal doors' "
    "WHERE form_page='materials_page' AND category='Internal Doors'"
)
print(f"  [case fix] 'Internal Doors' -> 'Internal doors': {cur.rowcount} rows")

# --- 3. Normalise stray dm% rows (form_page='' or '2') ---
cur.execute(
    "UPDATE line_items SET form_page='materials_page', category='dimension' "
    "WHERE (form_page='' OR form_page='2') AND line_code LIKE 'dm%'"
)
print(f"  [dm% stray] normalised to materials_page/dimension: {cur.rowcount} rows")

conn.commit()

# --- Verification ---
print("\n--- Verification: materials_page counts by category ---")
cur.execute(
    "SELECT category, COUNT(*) as n FROM line_items "
    "WHERE form_page='materials_page' GROUP BY category ORDER BY category"
)
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
print("\nDone.")
