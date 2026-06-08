import os

QMAPP = os.path.join(os.path.dirname(__file__), '..', 'QMapp.py')
content = open(QMAPP, encoding='utf-8').read()

INJECT_AB = "\tpage_schema = build_page_schema_context('additional_building_work_page', sheet_data, session.get('checkbox_data', {}))\n"
INJECT_OE = "\tpage_schema = build_page_schema_context('optional_extras_page', sheet_data, session.get('checkbox_data', {}))\n"

# 1. Fix additional_building_work_page
old_ab = """	return render_template(
		'form.html',
		additional_building_work_page=True,
		previous_page=previous_page,
		next_page='additional_costs_page',
		title="Additional Building Works",
		data=data
	)"""

new_ab = INJECT_AB + """	return render_template(
		'form.html',
		page_schema=page_schema,
		additional_building_work_page=True,
		previous_page=previous_page,
		next_page='additional_costs_page',
		title="Additional Building Works",
		data=data
	)"""

# 2. Fix optional_extras_page (need to find the non-edit return)
# Searching for the specific return block in optional_extras_page
old_oe = """	return render_template(
		'form.html',
		optional_extras_page=True,
		previous_page=previous_page,
		next_page='image_upload_page',
		title="Optional Extras",
		data=data
	)"""

new_oe = INJECT_OE + """	return render_template(
		'form.html',
		page_schema=page_schema,
		optional_extras_page=True,
		previous_page=previous_page,
		next_page='image_upload_page',
		title="Optional Extras",
		data=data
	)"""

if old_ab in content:
    content = content.replace(old_ab, new_ab, 1)
    print("✓ additional_building_work_page fixed")
else:
    print("!! additional_building_work_page anchor NOT FOUND")

if old_oe in content:
    content = content.replace(old_oe, new_oe, 1)
    print("✓ optional_extras_page fixed")
else:
    # Try with different title if needed, or check context
    print("!! optional_extras_page anchor NOT FOUND")
    # Debug: look for where optional_extras_page return is
    import re
    match = re.search(r"return render_template\(\s+'form\.html',\s+optional_extras_page=True", content)
    if match:
        print(f"Found something similar: {repr(content[match.start():match.start()+150])}")

open(QMAPP, 'w', encoding='utf-8').write(content)
