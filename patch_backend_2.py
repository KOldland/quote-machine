import os

file_path = "app/QMapp.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace builder_line_items_json logic to include category IDs
search_1 = """	groups = _get_line_items_for_page(page_filter)
	categories_list = []
	for cat, items in groups.items():
		if category_filter and cat != category_filter:
			continue
		categories_list.append({
			'name': cat,
			'items': items
		})"""

replace_1 = """	groups = _get_line_items_for_page(page_filter)

	# Fetch category IDs for the builder mapping
	_cat_query = "SELECT c.id, c.name FROM category_templates c JOIN page_templates p ON c.page_template_id = p.id WHERE p.page_key = ?"
	_db = str(_P(os.environ.get('QM_TEMPLATE_DB_PATH', '') or _P(__file__).parent / 'template_store.sqlite3'))
	_conn = _sq.connect(_db)
	_conn.row_factory = _sq.Row
	_cat_rows = _conn.execute(_cat_query, [page_filter]).fetchall()
	_conn.close()
	cat_id_map = {r['name']: r['id'] for r in _cat_rows}

	categories_list = []
	for cat, items in groups.items():
		if category_filter and cat != category_filter:
			continue
		categories_list.append({
			'id': cat_id_map.get(cat),
			'name': cat,
			'items': items
		})"""

if search_1 in content:
    content = content.replace(search_1, replace_1, 1)
    print("Patched builder_line_items_json")
else:
    print("Could not find search_1")

# Replace builder_beta_page_editor logic to include category IDs in li_categories
search_2 = """	_li_cats = list(_get_line_items_for_page(page_id).keys())"""
replace_2 = """	# Get category objects with IDs for the builder UI
	_cat_query = "SELECT c.id, c.name FROM category_templates c JOIN page_templates p ON c.page_template_id = p.id WHERE p.page_key = ? ORDER BY c.display_order ASC"
	import sqlite3 as _sq
	from pathlib import Path as _P
	_db = str(_P(os.environ.get('QM_TEMPLATE_DB_PATH', '') or _P(__file__).parent / 'template_store.sqlite3'))
	_conn = _sq.connect(_db)
	_conn.row_factory = _sq.Row
	_cat_rows = _conn.execute(_cat_query, [page_id]).fetchall()
	_conn.close()
	_li_cats = [{'id': r['id'], 'name': r['name']} for r in _cat_rows]"""

if search_2 in content:
    content = content.replace(search_2, replace_2, 1)
    print("Patched builder_beta_page_editor")
else:
    print("Could not find search_2")

with open(file_path, "w") as f:
    f.write(content)
