import sqlite3
import random
import string

def generate_line_code(prefix="Q_"):
    return prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Read original
with open("app/template_store.py", "r") as f:
    content = f.read()

# Generate new function
new_func = """
def duplicate_page(source_page_key: str, new_page_key: str, new_title: str, template_key: str = "first_client_template_v1", db_path: Optional[Path] = None) -> Dict[str, Any]:
    \"\"\"Duplicate an existing page, its categories, and line items.\"\"\"
    import uuid
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    version_id = _get_latest_version_id(conn, template_key)
    if version_id is None:
        conn.close()
        return {"success": False, "error": "Template version not found"}
        
    try:
        conn.execute("BEGIN TRANSACTION")
        
        # Get source page
        source_page = conn.execute(
            "SELECT * FROM page_templates WHERE form_template_version_id = ? AND page_key = ?",
            (version_id, source_page_key)
        ).fetchone()
        
        if not source_page:
            conn.rollback()
            return {"success": False, "error": f"Source page '{source_page_key}' not found"}
            
        # Determine next display order
        max_order_row = conn.execute(
            "SELECT MAX(display_order) as max_order FROM page_templates WHERE form_template_version_id = ?",
            (version_id,)
        ).fetchone()
        
        next_order = 0
        if max_order_row and max_order_row["max_order"] is not None:
            next_order = int(max_order_row["max_order"]) + 1
            
        # 1. Insert new page
        cur = conn.cursor()
        cur.execute(
            \"\"\"INSERT INTO page_templates 
               (form_template_version_id, page_key, title, metadata_json, display_order)
               VALUES (?, ?, ?, ?, ?)
            \"\"\",
            (version_id, new_page_key, new_title, source_page["metadata_json"], next_order)
        )
        new_page_id = cur.lastrowid
        
        # 2. Copy Categories
        source_cats = conn.execute(
            "SELECT * FROM category_templates WHERE form_template_version_id = ? AND page_template_id = ?",
            (version_id, source_page["id"])
        ).fetchall()
        
        for cat in source_cats:
            conn.execute(
                \"\"\"INSERT INTO category_templates 
                   (form_template_version_id, page_template_id, name, display_order)
                   VALUES (?, ?, ?, ?)
                \"\"\",
                (version_id, new_page_id, cat["name"], cat["display_order"])
            )
            
        # 3. Copy Line Items
        source_items = conn.execute(
            "SELECT * FROM line_items WHERE form_page = ?",
            (source_page_key,)
        ).fetchall()
        
        for item in source_items:
            import string
            import random
            def get_rand():
                return "Q_" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            new_code = get_rand()
            
            # Reconstruct columns
            columns = [key for key in item.keys() if key not in ["id", "line_code", "form_page", "created_at", "updated_at"]]
            placeholders = ", ".join(["?"] * len(columns))
            cols_str = ", ".join(columns)
            
            vals = [item[c] for c in columns]
            
            # Execute insert
            q = f"INSERT INTO line_items (line_code, form_page, {cols_str}) VALUES (?, ?, {placeholders})"
            conn.execute(q, [new_code, new_page_key] + vals)
            
        conn.commit()
        return {"success": True, "page_key": new_page_key}
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return {"success": False, "error": f"Integrity error: {str(e)}"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
    finally:
        conn.close()

def add_category(page_key: str, category_name: str, template_key: str = "first_client_template_v1", db_path: Optional[Path] = None) -> Dict[str, Any]:"""

if "def duplicate_page" not in content:
    content = content.replace("def add_category(page_key: str, category_name: str, template_key: str = \"first_client_template_v1\", db_path: Optional[Path] = None) -> Dict[str, Any]:", new_func)

    with open("app/template_store.py", "w") as f:
        f.write(content)
    print("Patched app/template_store.py successfully!")
else:
    print("duplicate_page already exists.")

