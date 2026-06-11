import os
import re

filepath = 'app/QMapp.py'
with open(filepath, 'r') as f:
    orig = f.read()

# ADD ENDPOINTS for page details and category logic

route_code = """
@app.route('/builder_beta/page_details_json/<page_key>')
@require_role('admin')
def builder_page_details_json(page_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT title, description FROM page_templates WHERE page_key = ?", [page_key]).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({})

@app.route('/builder_beta/page_details_save/<page_key>', methods=['POST'])
@require_role('admin')
def builder_page_details_save(page_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    title = data.get('title', '')
    desc = data.get('description', '')
    conn = sqlite3.connect(db)
    conn.execute("UPDATE page_templates SET title = ?, description = ? WHERE page_key = ?", [title, desc, page_key])
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/builder_beta/category_details_json')
@require_role('admin')
def builder_category_details_json():
    page_key = request.args.get('page_key')
    name = request.args.get('name')
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute('''
        SELECT c.name, c.description 
        FROM category_templates c
        JOIN page_templates p ON c.page_template_id = p.id
        WHERE p.page_key = ? AND c.name = ?
    ''', [page_key, name]).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({})

@app.route('/builder_beta/category_details_save', methods=['POST'])
@require_role('admin')
def builder_category_details_save():
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    desc = data.get('description', '')
    
    conn = sqlite3.connect(db)
    try:
        # Get page id
        page_id = conn.execute("SELECT id FROM page_templates WHERE page_key = ?", [page_key]).fetchone()[0]
        conn.execute("UPDATE category_templates SET name = ?, description = ? WHERE page_template_id = ? AND name = ?", 
                     [new_name, desc, page_id, old_name])
        
        # cascading update line_items category linking to match if changed
        if old_name != new_name:
            conn.execute("UPDATE line_items SET category = ? WHERE form_page = ? AND category = ?",
                         [new_name, page_key, old_name])
                         
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/builder_beta/line_item_add', methods=['POST'])
@require_role('admin')
def builder_line_item_add():
    import sqlite3
    import time
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    category = data.get('category')
    
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    
    # get max sort
    max_sort = conn.execute("SELECT MAX(sort_order) FROM line_items WHERE form_page = ? AND category = ?", [page_key, category]).fetchone()[0]
    next_sort = 0 if max_sort is None else max_sort + 1
    new_code = f"new_{int(time.time())}"
    
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO line_items (form_page, category, line_code, internal_description, item_role, form_visible, sort_order)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    ''', [page_key, category, new_code, "New Question", "parent", next_sort])
    conn.commit()
    
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM line_items WHERE id = ?", [new_id]).fetchone()
    conn.close()
    
    return jsonify({'ok': True, 'item': dict(row)})
"""

# inject right before the PAGE ROUTES block starts (line 2859 area)
inject_target = "################################################################################################################################"
if route_code not in orig:
    idx = orig.find(inject_target)
    new_code = orig[:idx] + route_code + "\n" + orig[idx:]
    with open(filepath, 'w') as f:
        f.write(new_code)
