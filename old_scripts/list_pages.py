import sqlite3

conn = sqlite3.connect('app/template_store.sqlite3')
cur = conn.cursor()
pages = cur.execute("SELECT page_key FROM page_templates").fetchall()
print("Found DB Pages:")
for p in pages:
    print(p[0])
conn.close()
