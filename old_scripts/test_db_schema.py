import sqlite3

conn = sqlite3.connect('app/template_store.sqlite3')
cur = conn.cursor()

print("--- Tables ---")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';"):
    table = row[0]
    print(f"\nTable: {table}")
    for col in cur.execute(f"PRAGMA table_info({table});"):
        print(f"  {col[1]}: {col[2]}")

conn.close()
