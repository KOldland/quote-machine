import sqlite3

# Let's inspect the `template_store.py` to see where to insert duplicate_page
with open('app/template_store.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "def add_page" in line:
        print(f"add_page is at {i}")
        break

print("Checking line_items foreign keys and constraints...")
conn = sqlite3.connect('app/template_store.sqlite3')
cur = conn.cursor()
for row in cur.execute("PRAGMA index_list(line_items);"):
    print(f"Index: {row}")
    for col in cur.execute(f"PRAGMA index_info({row[1]});"):
        print(f"  Col: {col}")

conn.close()
