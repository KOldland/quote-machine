import sqlite3
conn = sqlite3.connect('app/template_store.sqlite3')
cur = conn.cursor()
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';"):
    print(row[0])
conn.close()
