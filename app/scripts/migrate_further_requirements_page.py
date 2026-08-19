"""
Migration: further_requirements_page
Re-tags dw% and frc% line items from legacy form_page='3B'
to form_page='further_requirements_page'.

Run from repo root:
    python3 app/scripts/migrate_further_requirements_page.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'template_store.sqlite3')
TARGET_PAGE = 'further_requirements_page'

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# --- Audit before ---
cur.execute("""
    SELECT form_page, category, COUNT(*) as cnt
    FROM line_items
    WHERE line_code LIKE 'dw%' OR line_code LIKE 'frc%'
    GROUP BY form_page, category
    ORDER BY line_code
""")
print("BEFORE migration:")
for row in cur.fetchall():
    print(f"  form_page={row[0]!r:25} category={row[1]!r:45} count={row[2]}")

# --- Migrate dw% rows ---
cur.execute("""
    UPDATE line_items
    SET form_page = ?
    WHERE line_code LIKE 'dw%'
""", (TARGET_PAGE,))
dw_updated = cur.rowcount
print(f"\nUpdated {dw_updated} dw% rows -> form_page='{TARGET_PAGE}'")

# --- Migrate frc% rows ---
cur.execute("""
    UPDATE line_items
    SET form_page = ?
    WHERE line_code LIKE 'frc%'
""", (TARGET_PAGE,))
frc_updated = cur.rowcount
print(f"Updated {frc_updated} frc% rows -> form_page='{TARGET_PAGE}'")

conn.commit()

# --- Audit after ---
cur.execute("""
    SELECT form_page, category, COUNT(*) as cnt
    FROM line_items
    WHERE line_code LIKE 'dw%' OR line_code LIKE 'frc%'
    GROUP BY form_page, category
    ORDER BY line_code
""")
print("\nAFTER migration:")
for row in cur.fetchall():
    print(f"  form_page={row[0]!r:25} category={row[1]!r:45} count={row[2]}")

conn.close()
print("\nDone. further_requirements_page migration complete.")
