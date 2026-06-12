import sys
import os
sys.path.append('app')
import template_store as _ts

res = _ts.duplicate_page("special_notes_page", "special_notes_page_clone", "Special Notes Clone", template_key="first_client_template_v1")
print(res)

if res.get('success'):
    conn = _ts._connect('app/template_store.sqlite3')
    cats = conn.execute("SELECT * FROM category_templates WHERE page_template_id = (SELECT id FROM page_templates WHERE page_key='special_notes_page_clone')").fetchall()
    print(f"Cloned Categories: {len(cats)}")
    
    items = conn.execute("SELECT * FROM line_items WHERE form_page='special_notes_page_clone'").fetchall()
    print(f"Cloned Items: {len(items)}")
    
    conn.close()
