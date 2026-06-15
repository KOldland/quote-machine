import os

file_path = "app/QMapp.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace _get_li_categories_from_schema
search_1 = """def _get_li_categories_from_schema(page_id):
	\"\"\"Read page_schemas.json and return config.categories for the
	line_items_by_category block on the given page.
	Returns a list of category strings, or None if not configured (= show all).
	\"\"\"
	import json as _json
	_schema_path = os.path.join(os.path.dirname(__file__), 'page_schemas.json')
	try:
		with open(_schema_path) as _f:
			_schema = _json.load(_f)
		_page = _schema.get('builder_beta', {}).get('pages', {}).get(page_id, {})
		for _b in _page.get('blocks', []):
			if _b.get('block_type') == 'line_items_by_category':
				cats = _b.get('config', {}).get('categories', [])
				return cats if cats else None
	except Exception:
		pass
	return None"""

replace_1 = """def _get_li_categories_from_schema(page_id):
	\"\"\"Query category_templates to get the ordered list of categories for the given page.
	Returns a list of dicts: [{'id': 1, 'name': '...'}], or None if none.
	\"\"\"
	import sqlite3 as _sq
	from pathlib import Path as _P
	_db = str(_P(os.environ.get('QM_TEMPLATE_DB_PATH', '') or _P(__file__).parent / 'template_store.sqlite3'))
	_conn = _sq.connect(_db)
	_conn.row_factory = _sq.Row
	_cat_query = "SELECT c.id, c.name FROM category_templates c JOIN page_templates p ON c.page_template_id = p.id WHERE p.page_key = ? ORDER BY c.display_order ASC"
	_cat_rows = _conn.execute(_cat_query, [page_id]).fetchall()
	_conn.close()
	if not _cat_rows:
		return None
	return [{'id': r['id'], 'name': r['name']} for r in _cat_rows]"""

if search_1 in content:
    content = content.replace(search_1, replace_1, 1)
    print("Patched _get_li_categories_from_schema")
else:
    print("Could not find search_1")

with open(file_path, "w") as f:
    f.write(content)
