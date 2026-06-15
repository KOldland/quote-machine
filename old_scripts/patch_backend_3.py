import os

file_path = "app/QMapp.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace builder_line_items_json logic to include category IDs
search_1 = """    cats = {}
    for r in rows:
        cats.setdefault(r['category'], []).append(dict(r))
    return jsonify({'categories': [{'name': c, 'items': v} for c, v in cats.items()]})"""

replace_1 = """    cats = {}
    for r in rows:
        cats.setdefault(r['category'], []).append(dict(r))
        
    import sqlite3 as _sq
    _conn2 = _sq.connect(str(db))
    _conn2.row_factory = _sq.Row
    _cat_rows = _conn2.execute("SELECT c.id, c.name FROM category_templates c JOIN page_templates p ON c.page_template_id = p.id WHERE p.page_key = ?", [page_filter]).fetchall()
    _conn2.close()
    cat_id_map = {r['name']: r['id'] for r in _cat_rows}
    
    return jsonify({'categories': [{'id': cat_id_map.get(c), 'name': c, 'items': v} for c, v in cats.items()]})"""

if search_1 in content:
    content = content.replace(search_1, replace_1, 1)
    print("Patched builder_line_items_json")
else:
    print("Could not find search_1")

# Replace builder_beta_page_editor logic to include category IDs
# _li_cats is populated by `_li_cats = _get_li_categories_from_schema('...') or []`
# Let's search for `return render_template(` inside `builder_beta_page_editor`? Wait, builder_beta_page_editor doesn't call `render_template`. It returns JSON.
# Oh, `def builder_beta_page_editor(page_id):` handles POST and returns JSON!
# Let me search for where `builder_beta.html` is rendered.
