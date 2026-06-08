import sqlite3
import re
import os

DB_PATH = "app/template_store.sqlite3"

def run_cleanup():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- EXECUTING DESCRIPTIVE-CHILD CLEANUP ---")

    # 1. Identify rows to delete:
    # Criteria:
    # - Has a parent_code assigned (populated in Phase 4)
    # - line_code ends in an alphabetical character (excluding special chars)
    # - Is NOT a master parent (doesn't end in # or @)
    
    cursor.execute("""
        SELECT id, line_code, parent_code 
        FROM line_items 
        WHERE parent_code IS NOT NULL
          AND line_code NOT LIKE '%#'
          AND line_code NOT LIKE '%@'
    """)
    
    candidates = cursor.fetchall()
    to_delete = []

    for row_id, code, parent in candidates:
        # Regex check: strip special chars (*, ^) and check if it ends in alpha
        # This targets 'ab1a', 'sn4b*', etc.
        clean_code = re.sub(r'[*^]', '', code)
        if clean_code and clean_code[-1].isalpha():
            to_delete.append(row_id)

    if not to_delete:
        print("No descriptive children identified for cleanup.")
        conn.close()
        return

    print(f"Identified {len(to_delete)} descriptive child records for removal.")

    # 2. Perform Deletion
    # We use chunks to avoid potential SQL expression depth limits for very large sets
    chunk_size = 500
    total_deleted = 0
    for i in range(0, len(to_delete), chunk_size):
        chunk = to_delete[i:i + chunk_size]
        placeholders = ','.join('?' for _ in chunk)
        cursor.execute(f"DELETE FROM line_items WHERE id IN ({placeholders})", chunk)
        total_deleted += cursor.rowcount
    
    conn.commit()
    print(f"SUCCESS: {total_deleted} redundant child records removed from database.")
    
    # 3. Quick integrity check
    cursor.execute("SELECT COUNT(*) FROM line_items WHERE line_code LIKE '%#' OR line_code LIKE '%@'")
    parent_count = cursor.fetchone()[0]
    print(f"Integrity Check: {parent_count} Master Parents remain intact.")
    
    conn.close()

if __name__ == "__main__":
    run_cleanup()
