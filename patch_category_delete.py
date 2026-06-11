import re

filepath = 'app/QMapp.py'
with open(filepath, 'r') as f:
    orig = f.read()

# Add a missing /builder_beta/category/delete endpoint
delete_endpoint = """
@app.route('/builder_beta/category/delete', methods=['POST'])
@require_role('admin')
def builder_category_delete():
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    category_name = data.get('category_name')
    
    conn = sqlite3.connect(db)
    try:
        page_id = conn.execute("SELECT id FROM page_templates WHERE page_key = ?", [page_key]).fetchone()[0]
        # Delete category mapping
        conn.execute("DELETE FROM category_templates WHERE page_template_id = ? AND name = ?", [page_id, category_name])
        # Additionally delete all child line_items
        conn.execute("DELETE FROM line_items WHERE form_page = ? AND category = ?", [page_key, category_name])
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()
"""

inject_target = "################################################################################################################################"
if '/builder_beta/category/delete' not in orig:
    idx = orig.find(inject_target)
    new_code = orig[:idx] + delete_endpoint + "\n" + orig[idx:]
    with open(filepath, 'w') as f:
        f.write(new_code)
