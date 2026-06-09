import sys

def patch_qmapp():
    filepath = 'app/QMapp.py'
    with open(filepath, 'r') as f:
        content = f.read()

    # Part 1: Update inject_ui_context
    search_str_1 = """@app.context_processor
def inject_ui_context():
	\"\"\"Inject auth and edit-mode state into every template context.\"\"\"
	role = session.get('role')
	is_admin = role == 'admin'
	edit_requested = request.args.get('edit', '').lower() in {'1', 'true', 'yes'}
	edit_mode = is_admin and edit_requested
	return dict(
		current_user_role=role,
		current_username=session.get('username'),
		is_admin=is_admin,
		edit_mode=edit_mode,
	)"""

    replace_str_1 = """@app.context_processor
def inject_ui_context():
	\"\"\"Inject auth and edit-mode state into every template context.\"\"\"
	role = session.get('role')
	is_admin = role == 'admin'
	edit_requested = request.args.get('edit', '').lower() in {'1', 'true', 'yes'}
	edit_mode = is_admin and edit_requested
	
	db_pages = []
	if edit_mode:
		from app.template_store import get_all_pages
		db_pages = get_all_pages()
		
	return dict(
		current_user_role=role,
		current_username=session.get('username'),
		is_admin=is_admin,
		edit_mode=edit_mode,
		db_pages=db_pages,
	)"""

    if search_str_1 not in content:
        print("Error: Part 1 search string not found in QMapp.py")
        sys.exit(1)
        
    content = content.replace(search_str_1, replace_str_1)

    # Part 2: Append endpoints at the bottom
    search_str_2 = "if __name__ == '__main__':"
    
    replace_str_2 = """@app.route('/builder_beta/page/add', methods=['POST'])
@require_role('admin')
def builder_beta_page_add():
	import app.template_store as _ts
	data = request.json
	if not data or 'page_key' not in data or 'title' not in data:
		return jsonify({'success': False, 'error': 'Missing page_key or title'}), 400
	res = _ts.add_page(data['page_key'], data['title'])
	if res.get('success'):
		return jsonify({'success': True})
	return jsonify(res), 500

@app.route('/builder_beta/category/add', methods=['POST'])
@require_role('admin')
def builder_beta_category_add():
	import app.template_store as _ts
	data = request.json
	if not data or 'page_key' not in data or 'category_name' not in data:
		return jsonify({'success': False, 'error': 'Missing page_key or category_name'}), 400
	res = _ts.add_category(data['page_key'], data['category_name'])
	if res.get('success'):
		return jsonify({'success': True})
	return jsonify(res), 500

if __name__ == '__main__':"""

    if search_str_2 not in content:
        print("Error: Part 2 search string not found in QMapp.py")
        sys.exit(1)

    content = content.replace(search_str_2, replace_str_2)

    with open(filepath, 'w') as f:
        f.write(content)
        
    print("Patched successfully")

if __name__ == '__main__':
    patch_qmapp()
