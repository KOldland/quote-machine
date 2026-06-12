import sqlite3

conn = sqlite3.connect('app/template_store.sqlite3')
cur = conn.cursor()

def dump_schema(table_name):
    print(f"\n--- {table_name} ---")
    for col in cur.execute(f"PRAGMA table_info({table_name});"):
        print(f"  {col[1]}: {col[2]}")

dump_schema("page_templates")
dump_schema("category_templates")
dump_schema("line_items")
conn.close()
