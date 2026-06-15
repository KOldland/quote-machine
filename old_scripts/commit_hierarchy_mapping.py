import sqlite3

DB_PATH = "app/template_store.sqlite3"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("--- EXECUTING RELATIONAL HIERARCHY COMMIT ---")

# 1. Re-index parents
cursor.execute("SELECT line_code FROM line_items WHERE line_code LIKE '%#' OR line_code LIKE '%@'")
parents = [row[0] for row in cursor.fetchall()]

# 2. Update logic: Iterate through parents and link children
count = 0
for parent_code in parents:
    root = parent_code[:-1]
    # Update children: matches root, isn't parent, and follows our alphanumeric suffix rule
    # The GLOB '[0-9]' ensures we don't match numeric siblings (e.g., sn1 matching sn11)
    cursor.execute("""
        UPDATE line_items 
        SET parent_code = ? 
        WHERE line_code LIKE ? 
          AND line_code != ? 
          AND (SUBSTR(line_code, LENGTH(?) + 1, 1) NOT GLOB '[0-9]')
    """, (parent_code, f"{root}%", parent_code, root))
    count += cursor.rowcount

conn.commit()
print(f"SUCCESS: Relational hierarchy commit complete. {count} child rows linked to master parents.")
conn.close()
