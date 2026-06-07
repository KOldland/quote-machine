"""
Migrate summary_page line items:
- pp% items: form_page → 'summary_page', category → 'Planning Permission'
- cs% items: form_page → 'summary_page', category → 'Council'
"""
import sqlite3

DB_PATH = "app/template_store.sqlite3"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Fix Planning Permission items
cur.execute("""
    UPDATE line_items
    SET form_page = 'summary_page', category = 'Planning Permission'
    WHERE line_code LIKE 'pp%'
""")
pp_count = cur.rowcount
print(f"Updated {pp_count} Planning Permission rows (pp%)")

# Fix Council items
cur.execute("""
    UPDATE line_items
    SET form_page = 'summary_page', category = 'Council'
    WHERE line_code LIKE 'cs%'
""")
cs_count = cur.rowcount
print(f"Updated {cs_count} Council rows (cs%)")

conn.commit()
conn.close()

# Verify
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("""
    SELECT form_page, category, COUNT(*) as n
    FROM line_items
    WHERE form_page = 'summary_page'
    GROUP BY form_page, category
    ORDER BY category
""")
print("\nVerification — summary_page rows:")
for row in cur.fetchall():
    print(f"  form_page={row[0]}, category={row[1]}, count={row[2]}")
conn.close()
