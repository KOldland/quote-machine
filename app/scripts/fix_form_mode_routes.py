"""
Session Y — Fix form-mode (non-edit) GET paths for pages that call
compile_builder_beta_page_to_runtime_schema instead of build_page_schema_context.

Root cause: compile_... returns schema skeleton only — no li_groups, no value.
Fix: insert `page_schema = build_page_schema_context(...)` immediately before
each non-edit return render_template('form.html', ...) call.

Routes fixed:
  - materials_page              (~line 2880)
  - further_requirements_page   (~line 2937)
  - additional_costs_page       (~line 3165)
"""
import os

QMAPP = os.path.join(os.path.dirname(__file__), '..', 'QMapp.py')
content = open(QMAPP, encoding='utf-8').read()

INJECT = "\tpage_schema = build_page_schema_context(page_id, sheet_data, session.get('checkbox_data', {}))\n"
INJECT_COSTS = "\tpage_schema = build_page_schema_context('additional_costs_page', get_catalog(), session.get('checkbox_data', {}))\n"

fixes = [
    # ── materials_page ────────────────────────────────────────────────────────
    # Unique anchor: form-mode return with previous_page='summary_page'
    (
        "\treturn render_template(\n"
        "\t\t'form.html',\n"
        "\t\tpage_schema=page_schema,\n"
        "\t\tschema_render_mode='full',\n"
        "\t\tprevious_page='summary_page',\n"
        "\t\tnext_page='further_requirements_page',\n",

        INJECT +
        "\treturn render_template(\n"
        "\t\t'form.html',\n"
        "\t\tpage_schema=page_schema,\n"
        "\t\tschema_render_mode='full',\n"
        "\t\tprevious_page='summary_page',\n"
        "\t\tnext_page='further_requirements_page',\n"
    ),

    # ── further_requirements_page ─────────────────────────────────────────────
    # Unique anchor: form-mode return with previous_page='materials_page'
    (
        "\treturn render_template(\n"
        "\t\t'form.html',\n"
        "\t\tpage_schema=page_schema,\n"
        "\t\tschema_render_mode='full',\n"
        "\t\tprevious_page='materials_page',\n"
        "\t\tnext_page='additional_building_work_page',\n",

        INJECT +
        "\treturn render_template(\n"
        "\t\t'form.html',\n"
        "\t\tpage_schema=page_schema,\n"
        "\t\tschema_render_mode='full',\n"
        "\t\tprevious_page='materials_page',\n"
        "\t\tnext_page='additional_building_work_page',\n"
    ),

    # ── additional_costs_page ─────────────────────────────────────────────────
    # Unique anchor: non-edit form return with previous_page='additional_building_work_page'
    # and next_page='optional_extras_page' WITHOUT li_categories (edit-only var)
    (
        "\treturn render_template(\n"
        "\t\t'form.html',\n"
        "\t\tpage_schema=page_schema,\n"
        "\t\tschema_render_mode='full',\n"
        "\t\tprevious_page='additional_building_work_page',\n"
        "\t\tnext_page='optional_extras_page',\n"
        "\t\ttitle='Additional Costs',\n"
        "\t)\n",

        INJECT_COSTS +
        "\treturn render_template(\n"
        "\t\t'form.html',\n"
        "\t\tpage_schema=page_schema,\n"
        "\t\tschema_render_mode='full',\n"
        "\t\tprevious_page='additional_building_work_page',\n"
        "\t\tnext_page='optional_extras_page',\n"
        "\t\ttitle='Additional Costs',\n"
        "\t)\n"
    ),
]

for i, (old, new) in enumerate(fixes, 1):
    if old in content:
        content = content.replace(old, new, 1)
        print(f"  ✓ Fix {i} applied")
    else:
        print(f"  !! Fix {i} anchor NOT FOUND")
        # Print first 120 chars for debugging
        print(f"     Looking for: {repr(old[:120])}")

open(QMAPP, 'w', encoding='utf-8').write(content)
print("\nDone. Now run: python3 -m py_compile app/QMapp.py && echo SYNTAX_OK")
