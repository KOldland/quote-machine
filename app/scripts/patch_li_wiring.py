"""
Session W/X — Wire line_items_by_category fields to the normal form view.

Changes to QMapp.py:
  1. Add 'type': block_type to field_entry in build_builder_beta_runtime_context
     so form.html type checks (field.type == '...') work for builder_beta pages.
  2. Add _get_line_items_for_page() helper — queries SQLite line_items by form_page.
  3. Add elif block_type == 'line_items_by_category': in runtime context builder
     to populate field_entry['li_groups'] and field_entry['value'].
  4. Update persist_schema_page_submission to save line_items_by_category selections.

Changes to form.html:
  5. Add {% elif field.type == 'line_items_by_category' %} rendering block
     inside the main {% for field in page_schema.fields %} loop.
"""
import os
import sys

BASE = os.path.join(os.path.dirname(__file__), '..')
QMAPP = os.path.join(BASE, 'QMapp.py')
FORM_HTML = os.path.join(BASE, 'templates', 'form.html')


def patch_file(path, replacements):
    content = open(path, encoding='utf-8').read()
    for i, (old, new) in enumerate(replacements, 1):
        if old not in content:
            print(f"  !! Anchor {i} NOT FOUND in {os.path.basename(path)} — skipping.")
            print(f"     Looking for: {repr(old[:80])}...")
            continue
        content = content.replace(old, new, 1)
        print(f"  ✓ Change {i} applied to {os.path.basename(path)}")
    open(path, 'w', encoding='utf-8').write(content)


# ─── QMapp.py patches ─────────────────────────────────────────────────────────

QMAPP_PATCHES = [

    # 1. Add 'type': block_type to field_entry dict
    (
        "'block_type': block_type,\n\t\t\t'builder_beta_meta': deepcopy(meta),",
        "'block_type': block_type,\n\t\t\t'type': block_type,\n\t\t\t'builder_beta_meta': deepcopy(meta),"
    ),

    # 2. Insert _get_line_items_for_page helper before build_builder_beta_runtime_context
    (
        "def build_builder_beta_runtime_context(page_id, sheet_data, page_answers):",
        """\
def _get_line_items_for_page(page_id):
\t\"\"\"Query SQLite line_items for a page and return items grouped by category.\"\"\"
\ttry:
\t\timport sqlite3 as _sqlite3
\t\tfrom collections import OrderedDict
\t\tdb_path = os.path.join(os.path.dirname(__file__), 'template_store.sqlite3')
\t\tconn = _sqlite3.connect(db_path)
\t\tconn.row_factory = _sqlite3.Row
\t\trows = conn.execute(
\t\t\t\"\"\"SELECT line_code, internal_description, category, include_default
\t\t\t   FROM line_items WHERE form_page = ? AND form_visible = 1
\t\t\t   ORDER BY category, sort_order\"\"\",
\t\t\t(page_id,)
\t\t).fetchall()
\t\tconn.close()
\t\tgroups = OrderedDict()
\t\tfor row in rows:
\t\t\tcat = row['category'] or 'Uncategorised'
\t\t\tif cat not in groups:
\t\t\t\tgroups[cat] = []
\t\t\tgroups[cat].append({
\t\t\t\t'value': row['line_code'],
\t\t\t\t'label': row['internal_description'] or row['line_code'],
\t\t\t\t'include_default': row['include_default'] or 'N',
\t\t\t})
\t\treturn [{'category': cat, 'items': items} for cat, items in groups.items()]
\texcept Exception as e:
\t\tprint(f'[line_items] Error loading items for {page_id}: {e}')
\t\treturn []


def build_builder_beta_runtime_context(page_id, sheet_data, page_answers):"""
    ),

    # 3. Add elif line_items_by_category branch after text_input/number_currency_input
    (
        "elif block_type in {'text_input', 'number_currency_input'}:\n\t\t\tfield_entry['value'] = str(page_answers.get(field_name, '') or '')",
        """\
elif block_type in {'text_input', 'number_currency_input'}:
\t\t\tfield_entry['value'] = str(page_answers.get(field_name, '') or '')
\t\telif block_type == 'line_items_by_category':
\t\t\tli_groups = _get_line_items_for_page(page_id)
\t\t\tstored = get_preselected(field_name)
\t\t\tif not isinstance(stored, list):
\t\t\t\tstored = []
\t\t\tif not stored:
\t\t\t\tstored = [item['value'] for grp in li_groups for item in grp['items']
\t\t\t\t         if item.get('include_default') == 'Y']
\t\t\tfield_entry['li_groups'] = li_groups
\t\t\tfield_entry['value'] = stored"""
    ),

    # 4. Update persist_schema_page_submission to handle line_items_by_category
    (
        "if field_schema.get('type') == 'checkbox_group':\n\t\t\tselected_values = form_data.getlist(field_schema['name'])\n\t\t\tcheckbox_data[storage_key] = {'preselected': selected_values if selected_values else []}",
        """\
if field_schema.get('type') in {'checkbox_group', 'line_items_by_category'}:
\t\t\tselected_values = form_data.getlist(field_schema['name'])
\t\t\tcheckbox_data[storage_key] = {'preselected': selected_values if selected_values else []}"""
    ),
]

# ─── form.html patch ──────────────────────────────────────────────────────────

# Insert {% elif field.type == 'line_items_by_category' %} rendering block
# just before the closing {% endif %} of the main field loop (before {% endfor %}).
# Anchor: the unique sequence at lines 298-302 (</div> endif endfor endif + comment).

FORM_HTML_PATCHES = [
    (
        "            </div>\n        {% endif %}\n        {% endfor %}\n        {% endif %}\n\n        <!-- First page: Project Details -->",
        """\
            </div>
            {% elif field.type == 'line_items_by_category' %}
            {# ── Session W: line_items_by_category normal form render ──────────── #}
            <div class="schema-field-block">
                {% for grp in field.li_groups %}
                <div class="accordion-section">
                    <button type="button" class="accordion-header"
                            onclick="toggleAccordion('li_{{ loop.index0 }}_{{ field.id }}')">
                        {{ grp.category }}
                    </button>
                    <div id="li_{{ loop.index0 }}_{{ field.id }}" class="accordion-body">
                        {% for item in grp.items %}
                        <label class="checkbox-label">
                            <input type="checkbox" name="{{ field.name }}" value="{{ item.value }}"
                                {% if item.value in field.value %}checked{% endif %}>
                            {{ item.label }}
                        </label><br>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        {% endif %}
        {% endfor %}
        {% endif %}

        <!-- First page: Project Details -->"""
    ),
]


print("=== Patching QMapp.py ===")
patch_file(QMAPP, QMAPP_PATCHES)

print("=== Patching form.html ===")
patch_file(FORM_HTML, FORM_HTML_PATCHES)

print("\nDone. Now run: python3 -m py_compile app/QMapp.py && echo SYNTAX_OK")
