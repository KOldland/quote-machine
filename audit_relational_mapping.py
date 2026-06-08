import sqlite3
import os
import re

# Configuration
DB_PATH = "app/template_store.sqlite3"

def run_audit():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    # Connect in read-only mode
    try:
        # Use URI for read-only mode
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    print("--- STARTING STRUCTURAL MAPPING AUDIT ---\n")

    # 1. Extract all distinct categories
    cursor.execute("SELECT DISTINCT category FROM line_items ORDER BY category")
    categories = [row['category'] for row in cursor.fetchall()]

    for category in categories:
        print(f"CATEGORY: {category}")
        print("-" * (len(category) + 10))

        # 2. Extract Master Rows (Parents ending in # or @) for this category
        cursor.execute("""
            SELECT line_code, internal_description 
            FROM line_items 
            WHERE category = ? 
              AND (line_code LIKE '%#' OR line_code LIKE '%@')
            ORDER BY line_code
        """, (category,))
        
        parents = cursor.fetchall()

        if not parents:
            print("  (No master parent records found in this category)\n")
            continue

        for parent in parents:
            parent_code = parent['line_code']
            parent_label = parent['internal_description']
            
            # Identify the root stem by stripping the # or @
            root_stem = parent_code[:-1]
            
            print(f"  [PARENT] {parent_code: <15} | {parent_label}")

            # 3. Look up Child records matching the root stem prefix
            # We look for codes starting with root_stem + suffix, excluding the parent itself
            cursor.execute("""
                SELECT line_code, internal_description 
                FROM line_items 
                WHERE line_code LIKE ? 
                  AND line_code != ?
                ORDER BY line_code
            """, (f"{root_stem}%", parent_code))
            
            children = cursor.fetchall()

            if children:
                for child in children:
                    print(f"    └─ [CHILD] {child['line_code']: <11} | {child['internal_description']}")
            else:
                print("    └─ (No children identified)")
        
        print("\n")

    conn.close()
    print("--- AUDIT COMPLETE ---")

if __name__ == "__main__":
    run_audit()
