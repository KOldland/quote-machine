import re

filepath = 'app/QMapp.py'
with open(filepath, 'r') as f:
    orig = f.read()

# Missing Endpoints
endpoints_code = """
@app.route('/builder_beta/page_details_delete/<page_key>', methods=['POST'])
@require_role('admin')
def builder_page_delete(page_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = sqlite3.connect(db)
    try:
        page_id = conn.execute("SELECT id FROM page_templates WHERE page_key = ?", [page_key]).fetchone()[0]
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
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    return jsonify({'ok': True, 'msg': f'Stub: Page {page_key} saved as template.'})
"""

# Now we need to fix line_item_delete if it exists, or create it.
li_delete_code = """
@app.route('/builder_beta/line_item_delete', methods=['POST'])
@require_role('admin')
def builder_line_item_delete():
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    line_code = data.get('line_code')
    conn = sqlite3.connect(db)
    try:
        conn.execute("DELETE FROM line_items WHERE line_code = ?", [line_code])
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()
"""

# Let's check what currently exists in QMapp for line_item delete.
# If it's already there, this might just be a JS side routing issue.
# Wait, let's look at `_builder_macros.html` where delete question is triggered.
