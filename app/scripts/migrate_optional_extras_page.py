"""
Session W — Migrate optional_extras_page line items
- Items with line_code LIKE 'oe%' / 'op%' / 'ex%'
- form_page: '' (empty) → 'optional_extras_page'
- category: 'Optional Extras' already matches schema — no rename needed
- 2 'Uncategorised' items also get page tagged (won't show in 3-col but correctly owned)
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'template_store.sqlite3')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Pre-migration breakdown
cur.execute("""
    SELECT form_page, category, COUNT(*) 
    FROM line_items 
    WHERE line_code LIKE 'oe%' OR line_code LIKE 'op%' OR line_code LIKE 'ex%'
    GROUP BY form_page, category
""")
print("Pre-migration breakdown:")
for row in cur.fetchall():
    print(f"  form_page={row[0]!r}, category={row[1]!r}, count={row[2]}")

# Migration — set form_page; category already correct for 'Optional Extras'
cur.execute("""
    UPDATE line_items
    SET form_page = 'optional_extras_page'
    WHERE line_code LIKE 'oe%' OR line_code LIKE 'op%' OR line_code LIKE 'ex%'
""")
affected = cur.rowcount
conn.commit()
print(f"\nUpdated {affected} rows.")

# Post-migration verification
cur.execute("""
    SELECT form_page, category, COUNT(*) 
    FROM line_items 
    WHERE line_code LIKE 'oe%' OR line_code LIKE 'op%' OR line_code LIKE 'ex%'
    GROUP BY form_page, category
""")
print("Post-migration breakdown:")
for row in cur.fetchall():
    print(f"  form_page={row[0]!r}, category={row[1]!r}, count={row[2]}")

conn.close()
print("\nDone.")
