
import csv
import sqlite3
import sys
from pathlib import Path

# Add app directory to sys.path to allow for absolute imports
app_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(app_dir))

def get_db_path():
    return app_dir / "template_store.sqlite3"

def migrate_special_notes():
    db_path = get_db_path()
    csv_path = app_dir / "context_archive /Plus Rooms Live input in doc formatting (back up) - Sheet1v2.csv"

    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Clear existing special notes to avoid duplicates
        print("Deleting existing 'Special Notes' from the database...")
        cursor.execute("DELETE FROM line_items WHERE category = ?", ("special notes",))
        print(f"{cursor.rowcount} rows deleted.")

        print(f"Reading data from {csv_path}...")
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader) # Skip header

            # Find column indices
            col_map = {name.strip(): i for i, name in enumerate(header)}

            items_to_insert = []
            current_parent_code = None

            for i, row in enumerate(reader):
                if len(row) <= col_map['Category'] or row[col_map['Category']].lower().strip() != 'special notes':
                    continue

                line_code = row[col_map['Line Code']].strip()
                internal_desc = row[col_map['Internal Description']].strip()
                include_default = row[col_map['Include']].strip().upper()
                output_title = row[col_map['description (title)']].strip()
                output_notes = row[col_map['Description (notes)']].strip()
                output_guidance = row[col_map['Description (additional guidance)']].strip()

                item_role = 'standalone'
                parent_code = None

                if line_code.endswith('#'):
                    item_role = 'parent'
                    current_parent_code = line_code
                elif line_code.endswith('a') or line_code.endswith('b') or line_code.endswith('c'):
                    item_role = 'auto_child'
                    parent_code = current_parent_code
                if '*' in line_code:
                    item_role = 'guidance'

                item = (
                    line_code,
                    'special_notes_page', # form_page
                    'Special Notes', # category
                    internal_desc,
                    include_default,
                    output_title,
                    output_notes,
                    output_guidance,
                    parent_code,
                    item_role,
                    1, # form_visible
                    i # sort_order
                )
                items_to_insert.append(item)

        if items_to_insert:
            print(f"Found {len(items_to_insert)} 'Special Notes' items to insert...")
            cursor.executemany("""
                INSERT INTO line_items (
                    line_code, form_page, category, internal_description, include_default, 
                    output_title, output_notes, output_guidance, parent_code, item_role, 
                    form_visible, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, items_to_insert)
            print("Insertion complete.")

        conn.commit()
        print("Changes have been committed to the database.")

    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_special_notes()

