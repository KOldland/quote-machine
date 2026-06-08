import sqlite3
import os
import re

# Configuration
DB_PATH = "app/template_store.sqlite3"

def run_simulation():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    # Connect in read-only mode using URI
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    print("[SIMULATION] Initiating Parent-Child Relational Mapping Audit...")
    print("----------------------------------------------------------------")

    # Fetch all active items
    cursor.execute("SELECT id, line_code, category, internal_description FROM line_items")
    all_items = [dict(row) for row in cursor.fetchall()]

    # 1. Identify and index master parents (ending in # or @)
    # Map root_stem -> full_parent_code
    parent_map = {}
    for item in all_items:
        code = item['line_code']
        if code.endswith('#') or code.endswith('@'):
            root = code[:-1]
            parent_map[root] = code

    # 2. Loop through all items to identify children
    links_identified = 0
    results_by_category = {}

    for item in all_items:
        code = item['line_code']
        category = item['category']
        
        # Skip if this is already a parent
        if code.endswith('#') or code.endswith('@'):
            continue

        # Logic to find the parent:
        # We need the longest matching root to avoid partial matches
        # and we must ensure alphanumeric suffixing logic
        match_found = False
        
        # Sort roots by length descending to ensure we match the most specific parent first
        for root in sorted(parent_map.keys(), key=len, reverse=True):
            parent_code = parent_map[root]
            
            # A child must start with the root stem
            if code.startswith(root):
                suffix = code[len(root):]
                # CRITICAL: Collision Guard
                # If the suffix starts with a digit, it's a numeric sibling (sn1 -> sn11), not a child.
                # A child suffix usually starts with a letter (sn1 -> sn1a).
                # Exception: if suffix is empty, it's the root itself (already skipped parents)
                if suffix and not suffix[0].isdigit():
                    mapping_str = f"  -> Link Child '{code: <12}' to Master Parent '{parent_code: <12}' | {item['internal_description'][:50]}"
                    results_by_category.setdefault(category, []).append(mapping_str)
                    links_identified += 1
                    match_found = True
                    break

    # 3. Print categorized results
    for category, links in sorted(results_by_category.items()):
        print(f"\n[CATEGORY: {category}]")
        for link in links:
            print(link)

    print("\n----------------------------------------------------------------")
    print(f"[SIMULATION COMPLETE] Found {links_identified} child rows ready for relational mapping.")
    
    conn.close()

if __name__ == "__main__":
    run_simulation()
