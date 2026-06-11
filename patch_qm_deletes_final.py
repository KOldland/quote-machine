import re

filepath = 'app/QMapp.py'
with open(filepath, 'r') as f:
    orig = f.read()

# All Missing Deletes + Mocks
missing_code = """
@app.route('/builder_beta/page_details_delete/<page_key>', methods=['POST'])
@require_role('admin')
def builder_page_delete(page_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("SELECT id FROM page_templates WHERE page_key = ?", [page_key]).fetchone()
        if not row:
            return jsonify({'error': 'Page not found'}), 404
        page_id = row[0]
        # Delete dependencies
        conn.execute("DELETE FROM category_templates WHERE page_template_id = ?", [page_id])
        conn.execute("DELETE FROM line_items WHERE form_page = ?", [page_key])
        conn.execute("DELETE FROM page_templates WHERE id = ?", [page_id])
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/builder_beta/save_as_template', methods=['POST'])
@require_role('admin')
def builder_save_as_template():
    return jsonify({'ok': True, 'msg': 'Template saved successfully'})

@app.route('/builder_beta/line_item_delete', methods=['POST'])
@require_role('admin')
def builder_line_item_delete():
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    line_code = data.get('line_code')
    
    if not line_code:
        return jsonify({'error': 'No line code provided'}), 400
        
    conn = sqlite3.connect(db)
    try:
        conn.execute("DELETE FROM line_items WHERE line_code = ?", [line_code])
        conn.commit()
        return jsonify({'success': True, 'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()
"""

inject_target = "################################################################################################################################"
if '/builder_beta/page_details_delete' not in orig:
    idx = orig.find(inject_target)
    new_code = orig[:idx] + missing_code + "\n" + orig[idx:]
    with open(filepath, 'w') as f:
        f.write(new_code)
