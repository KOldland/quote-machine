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
    SET form_page = 'summary_page', category = 'Planning Permission', form_visible = 1
    WHERE line_code LIKE 'pp%'
""")
pp_count = cur.rowcount
print(f"Updated {pp_count} Planning Permission rows (pp%)")

# Fix Council items
cur.execute("""
    UPDATE line_items
    SET form_page = 'summary_page', category = 'Council', form_visible = 1
    WHERE line_code LIKE 'cs%'
""")
cs_count = cur.rowcount
print(f"Updated {cs_count} Council rows (cs%)")

# Fix Building Works items
cur.execute("""
    UPDATE line_items
    SET form_page = 'summary_page', category = 'Building Works', form_visible = 1
    WHERE line_code LIKE 'bw%'
""")
bw_count = cur.rowcount
print(f"Updated {bw_count} Building Works rows (bw%)")

# Fix Boundary Lines items
cur.execute("""
    UPDATE line_items
    SET form_page = 'summary_page', category = 'Boundary Lines', form_visible = 1
    WHERE line_code LIKE 'bl%'
""")
bl_count = cur.rowcount
print(f"Updated {bl_count} Boundary Lines rows (bl%)")

# Fix Basement items
cur.execute("""
    UPDATE line_items
    SET form_page = 'summary_page', category = 'Basement', form_visible = 1
    WHERE line_code LIKE 'bs%'
""")
bs_count = cur.rowcount
print(f"Updated {bs_count} Basement rows (bs%)")

# Fix Dimensions items
cur.execute("""
    UPDATE line_items
    SET form_page = 'summary_page', category = 'Dimensions', form_visible = 1
    WHERE line_code LIKE 'dm%'
""")
dm_count = cur.rowcount
print(f"Updated {dm_count} Dimensions rows (dm%)")

# Fix Additional Notes items (for Neighbours)
cur.execute("""
    UPDATE line_items
    SET form_page = 'summary_page', category = 'Additional Notes', form_visible = 1
    WHERE line_code LIKE 'an%'
""")
an_count = cur.rowcount
print(f"Updated {an_count} Additional Notes rows (an%)")

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
