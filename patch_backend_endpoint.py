import os

file_path = "app/QMapp.py"
with open(file_path, "r") as f:
    lines = f.readlines()

# Ensure we aren't adding duplicate definition
if any("def builder_beta_swap_order():" in line for line in lines):
    print("Function already exists!")
    exit(0)

# Find insertion point
insert_idx = -1
for i, line in enumerate(lines):
    if line.startswith("@app.route('/builder_beta/line_items_json'"):
        insert_idx = i
        break

if insert_idx == -1:
    print("Could not find insertion point.")
    exit(1)

endpoint_code = """
@app.route('/builder_beta/swap_order', methods=['POST'])
@require_role('admin')
def builder_beta_swap_order():
\timport sqlite3 as _sq
\tfrom pathlib import Path as _P
\tdata = request.json
\tif not data:
\t\treturn jsonify({'success': False, 'error': 'No data provided'}), 400

\tscope = data.get('scope')
\tdirection = data.get('direction')
\tidentifier = data.get('identifier')
\tpage_key = data.get('page_key')

\tif scope not in ['page', 'category', 'question'] or direction not in ['up', 'down'] or identifier is None:
\t\treturn jsonify({'success': False, 'error': 'Invalid parameters'}), 400

\tdb_path = str(_P(os.environ.get('QM_TEMPLATE_DB_PATH', '') or _P(__file__).parent / 'template_store.sqlite3'))
\tconn = _sq.connect(db_path)
\tconn.row_factory = _sq.Row
\tcursor = conn.cursor()

\ttry:
\t\tif scope == 'page':
\t\t\tcurr_row = cursor.execute("SELECT id, display_order FROM page_templates WHERE id = ?", [identifier]).fetchone()
\t\t\tif not curr_row:
\t\t\t\treturn jsonify({'success': False, 'error': 'Page not found'}), 404
\t\t\t
\t\t\tcurr_id = curr_row['id']
\t\t\tcurr_order = curr_row['display_order']

\t\t\tif direction == 'up':
\t\t\t\tadj_row = cursor.execute("SELECT id, display_order FROM page_templates WHERE display_order < ? ORDER BY display_order DESC LIMIT 1", [curr_order]).fetchone()
\t\t\telse:
\t\t\t\tadj_row = cursor.execute("SELECT id, display_order FROM page_templates WHERE display_order > ? ORDER BY display_order ASC LIMIT 1", [curr_order]).fetchone()

\t\t\tif adj_row:
\t\t\t\tcursor.execute("UPDATE page_templates SET display_order = ? WHERE id = ?", [adj_row['display_order'], curr_id])
\t\t\t\tcursor.execute("UPDATE page_templates SET display_order = ? WHERE id = ?", [curr_order, adj_row['id']])

\t\telif scope == 'category':
\t\t\tcurr_row = cursor.execute("SELECT id, display_order, page_template_id FROM category_templates WHERE id = ?", [identifier]).fetchone()
\t\t\tif not curr_row:
\t\t\t\treturn jsonify({'success': False, 'error': 'Category not found'}), 404
\t\t\t
\t\t\tcurr_id = curr_row['id']
\t\t\tcurr_order = curr_row['display_order']
\t\t\tpage_template_id = curr_row['page_template_id']

\t\t\tif direction == 'up':
\t\t\t\tadj_row = cursor.execute("SELECT id, display_order FROM category_templates WHERE page_template_id = ? AND display_order < ? ORDER BY display_order DESC LIMIT 1", [page_template_id, curr_order]).fetchone()
\t\t\telse:
\t\t\t\tadj_row = cursor.execute("SELECT id, display_order FROM category_templates WHERE page_template_id = ? AND display_order > ? ORDER BY display_order ASC LIMIT 1", [page_template_id, curr_order]).fetchone()

\t\t\tif adj_row:
\t\t\t\tcursor.execute("UPDATE category_templates SET display_order = ? WHERE id = ?", [adj_row['display_order'], curr_id])
\t\t\t\tcursor.execute("UPDATE category_templates SET display_order = ? WHERE id = ?", [curr_order, adj_row['id']])

\t\telif scope == 'question':
\t\t\tcurr_row = cursor.execute("SELECT id, sort_order, form_page, category FROM line_items WHERE id = ?", [identifier]).fetchone()
\t\t\tif not curr_row:
\t\t\t\treturn jsonify({'success': False, 'error': 'Question not found'}), 404
\t\t\t
\t\t\tcurr_id = curr_row['id']
\t\t\tcurr_order = curr_row['sort_order']
\t\t\tq_page = curr_row['form_page']
\t\t\tq_cat = curr_row['category']

\t\t\tif direction == 'up':
\t\t\t\tadj_row = cursor.execute("SELECT id, sort_order FROM line_items WHERE form_page = ? AND category = ? AND sort_order < ? ORDER BY sort_order DESC LIMIT 1", [q_page, q_cat, curr_order]).fetchone()
\t\t\telse:
\t\t\t\tadj_row = cursor.execute("SELECT id, sort_order FROM line_items WHERE form_page = ? AND category = ? AND sort_order > ? ORDER BY sort_order ASC LIMIT 1", [q_page, q_cat, curr_order]).fetchone()

\t\t\tif adj_row:
\t\t\t\tcursor.execute("UPDATE line_items SET sort_order = ? WHERE id = ?", [adj_row['sort_order'], curr_id])
\t\t\t\tcursor.execute("UPDATE line_items SET sort_order = ? WHERE id = ?", [curr_order, adj_row['id']])

\t\tconn.commit()
\t\treturn jsonify({'success': True})
\texcept Exception as e:
\t\tconn.rollback()
\t\treturn jsonify({'success': False, 'error': str(e)}), 500
\tfinally:
\t\tconn.close()

"""

lines.insert(insert_idx, endpoint_code)

with open(file_path, "w") as f:
    f.writelines(lines)
print("Added builder_beta_swap_order endpoint.")
