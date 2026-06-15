import csv
import re
import os

CSV_PATH = "app/context_archive /Plus Rooms Live input in doc formatting (back up) - Sheet1v2.csv"

def run_simulation():
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV not found at {CSV_PATH}")
        return

    print("[SIMULATION] Parsing CSV for Description-Child Mapping...")
    print("---------------------------------------------------------")

    groups = {} # base_stem -> {'parent': row, 'children': [rows]}

    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_code = row.get('Line Code')
            if not raw_code: continue
            
            # 1. Strip special characters
            clean_code = re.sub(r'[*@^#]', '', raw_code)
            
            # 2. Determine if Parent or Child
            # Stem is the numeric part, e.g., 'ab1' from 'ab1a'
            # We look for a pattern of letters followed by digits
            stem_match = re.match(r'^([a-z]+\d+)', clean_code)
            if not stem_match: continue
            
            stem = stem_match.group(1)
            groups.setdefault(stem, {'parent': None, 'children': []})
            
            if clean_code == stem:
                groups[stem]['parent'] = row
            else:
                groups[stem]['children'].append(row)

    # 3. Print Mapping Blueprint
    mapping_count = 0
    parent_count = 0
    
    # Sort stems by numeric value if possible, or string sort
    def sort_key(s):
        match = re.match(r'([a-z]+)(\d+)', s)
        if match:
            return (match.group(1), int(match.group(2)))
        return (s, 0)

    for stem in sorted(groups.keys(), key=sort_key):
        data = groups[stem]
        parent = data['parent']
        if not parent: continue
        
        parent_count += 1
        print(f"\nMASTER PARENT: {parent['Line Code']} [{parent['Category'].strip()}]")
        print(f"  Internal Desc: {parent['Internal Description']}")
        print(f"  Output Title:  {parent['description (title)']}")
        
        for child in data['children']:
            notes = child.get('Description (notes)', '').strip()
            guidance = child.get('Description (additional guidance)', '').strip()
            
            if notes:
                print(f"  + Map Child '{child['Line Code']}' Notes -> Parent Output Notes")
                print(f"    Content: {notes[:80]}...")
            if guidance:
                print(f"  + Map Child '{child['Line Code']}' Guidance -> Parent Output Guidance")
                print(f"    Content: {guidance[:80]}...")
            
            mapping_count += 1

    print("\n---------------------------------------------------------")
    print(f"[SIMULATION COMPLETE] Found {parent_count} Master Parents.")
    print(f"Mapped {mapping_count} children as descriptive metadata.")

if __name__ == "__main__":
    run_simulation()
