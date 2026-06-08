"""
Session W — Migrate additional_building_work_page line items
- 51 items with line_code LIKE 'ab%'
- form_page: '3C' → 'additional_building_work_page'
- category: 'Additional Building Items' → 'Additional Building Works'
  (to match page_schemas.json config.categories exactly)
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'template_store.sqlite3')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Pre-migration count
cur.execute("SELECT COUNT(*) FROM line_items WHERE line_code LIKE 'ab%'")
total = cur.fetchone()[0]
print(f"Total ab% items: {total}")

cur.execute("""
    SELECT form_page, category, COUNT(*) 
    FROM line_items WHERE line_code LIKE 'ab%' 
    GROUP BY form_page, category
""")
print("Pre-migration breakdown:")
for row in cur.fetchall():
    print(f"  form_page={row[0]!r}, category={row[1]!r}, count={row[2]}")

# Migration
cur.execute("""
    UPDATE line_items
    SET form_page = 'additional_building_work_page',
        category  = 'Additional Building Works'
    WHERE line_code LIKE 'ab%'
""")
affected = cur.rowcount
conn.commit()
print(f"\nUpdated {affected} rows.")

# Post-migration verification
cur.execute("""
    SELECT form_page, category, COUNT(*) 
    FROM line_items WHERE line_code LIKE 'ab%' 
    GROUP BY form_page, category
""")
print("Post-migration breakdown:")
for row in cur.fetchall():
    print(f"  form_page={row[0]!r}, category={row[1]!r}, count={row[2]}")

conn.close()
print("\nDone.")
