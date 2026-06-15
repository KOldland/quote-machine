import sqlite3
import json
import os

DB_PATH = "app/template_store.sqlite3"
SCHEMA_PATH = "app/page_schemas.json"

def run_standardization():
    if not os.path.exists(DB_PATH) or not os.path.exists(SCHEMA_PATH):
        print("Error: Missing database or schema file.")
        return
    
    # 1. Load canonical categories from Schema
    with open(SCHEMA_PATH, 'r') as f:
        schema_data = json.load(f)
    
    schema_categories = set()
    pages = schema_data.get('builder_beta', {}).get('pages', {})
    for page in pages.values():
        for block in page.get('blocks', []):
            if block.get('block_type') == 'line_items_by_category':
                cats = block.get('config', {}).get('categories', [])
                for c in cats: schema_categories.add(c)

    print(f"Loaded {len(schema_categories)} canonical categories from schema.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- EXECUTING SCHEMA-ALIGNED OUTPUT TITLE STANDARDIZATION ---")

    # 2. Fetch all questions
    cursor.execute("SELECT id, category FROM line_items")
    rows = cursor.fetchall()

    update_count = 0
    for row_id, db_category in rows:
        if not db_category: continue

        # Match DB category to Schema category (case-insensitive)
        # But we use the EXACT casing from the schema for the output
        matched_cat = db_category # fallback
        for sc in schema_categories:
            if sc.lower().strip() == db_category.lower().strip():
                matched_cat = sc
                break
        
        # Format: Take matched category + append colon
        # If we didn't find a match, we use .title() as a sane default
        if matched_cat == db_category:
            new_title = matched_cat.strip().title()
        else:
            new_title = matched_cat.strip()
            
        if not new_title.endswith(':'):
            new_title += ':'
            
        cursor.execute("""
            UPDATE line_items 
            SET output_title = ? 
            WHERE id = ?
        """, (new_title, row_id))
        update_count += 1

    conn.commit()
    print(f"SUCCESS: {update_count} titles aligned with schema category names.")
    
    # 3. Sample verification
    # Specifically checking the ones from your screenshot example
    cursor.execute("""
        SELECT line_code, category, output_title 
        FROM line_items 
        WHERE line_code IN ('fs1#', 'wp1#', 'dr1^', 'ps2#')
    """)
    print("\nAlignment Verification:")
    for code, cat, title in cursor.fetchall():
        print(f"  [{code}] DB Category: {cat: <25} -> Final Title: {title}")

    conn.close()

if __name__ == "__main__":
    run_standardization()
