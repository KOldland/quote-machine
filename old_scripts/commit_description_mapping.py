import csv
import re
import sqlite3
import os

CSV_PATH = "app/context_archive /Plus Rooms Live input in doc formatting (back up) - Sheet1v2.csv"
DB_PATH = "app/template_store.sqlite3"

def run_commit():
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV not found at {CSV_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- EXECUTING DESCRIPTION-CHILD DATABASE COMMIT ---")

    groups = {} # base_stem -> {'notes': [], 'guidance': []}

    # 1. Parse CSV and group descriptive metadata
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_code = row.get('Line Code')
            if not raw_code: continue
            
            # Extract root stem by stripping special characters
            clean_code = re.sub(r'[*@^#]', '', raw_code)
            stem_match = re.match(r'^([a-z]+\d+)', clean_code)
            if not stem_match: continue
            
            stem = stem_match.group(1)
            
            # If it's a child (ends in alpha suffix), collect its descriptive data
            if clean_code != stem:
                groups.setdefault(stem, {'notes': [], 'guidance': []})
                notes = row.get('Description (notes)', '').strip()
                guidance = row.get('Description (additional guidance)', '').strip()
                
                if notes: groups[stem]['notes'].append(notes)
                if guidance: groups[stem]['guidance'].append(guidance)

    # 2. Update Master Parents in Database
    update_count = 0
    for stem, meta in groups.items():
        # Combine multiple children into single newline-separated strings
        combined_notes = "\n".join(meta['notes'])
        combined_guidance = "\n".join(meta['guidance'])
        
        if not combined_notes and not combined_guidance:
            continue

        # Find the parent code in the DB that matches this stem
        # Parents in the DB are already tagged with # or @
        cursor.execute("""
            UPDATE line_items 
            SET output_notes = ?,
                output_guidance = ?
            WHERE (line_code = ? OR line_code = ?)
        """, (combined_notes, combined_guidance, f"{stem}#", f"{stem}@"))
        
        if cursor.rowcount > 0:
            update_count += cursor.rowcount

    conn.commit()
    print(f"SUCCESS: {update_count} Master Parents enriched with child metadata.")
    conn.close()

if __name__ == "__main__":
    run_commit()
