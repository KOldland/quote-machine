import re

with open("app/QMapp.py", "r") as f:
    content = f.read()

new_route = """
@app.route('/builder_beta/page/duplicate', methods=['POST'])
@require_role('admin')
def builder_beta_page_duplicate():
    import template_store as _ts
    data = request.json
    if not data or 'source_page_key' not in data or 'new_page_key' not in data or 'new_title' not in data:
        return jsonify({'success': False, 'error': 'Missing source_page_key, new_page_key, or new_title'}), 400
    res = _ts.duplicate_page(data['source_page_key'], data['new_page_key'], data['new_title'], template_key=TEMPLATE_STORE_KEY)
    if res.get('success'):
        return jsonify({'success': True})
    return jsonify(res), 500

@app.route('/builder_beta/page/add',"""

if "@app.route('/builder_beta/page/duplicate'" not in content:
    content = content.replace("@app.route('/builder_beta/page/add',", new_route)

    with open("app/QMapp.py", "w") as f:
        f.write(content)
    print("Patched app/QMapp.py successfully!")
else:
    print("duplicate_page route already exists in QMapp.py")

