#!/usr/bin/env python3
"""Script to fix the review route in QMapp.py"""

# Read the file
with open('app/QMapp.py', 'r') as f:
    content = f.read()

# Find and replace the review route render_template call
old_render = """    return render_template(
        'review.html',
        pages=calc_result.get('groups', []),
        totals_by_group=subtotals,
        grand_total=grand_total,
        groups=calc_result.get('groups', []),
        calc_result=calc_result,
        **ctx
    )"""

new_render = """    # ── FIX: Compile data in format expected by review.html ──
    # review.html expects: review_data, li_by_category, totals_by_group, TITLE_MAPPING
    
    # Build review_data from session data (data and checkbox_data)
    session_data = session.get('data', {})
    
    review_data = {}
    # Group form data by sections from page_schemas
    for page_id, page_info in page_schemas.get('pages', {}).items():
        section_fields = []
        
        # Get fields for this page from compiled schema
        compiled_page = compile_builder_beta_page_to_runtime_schema(page_id)
        if compiled_page:
            for field in compiled_page.get('fields', []):
                field_name = field.get('name')
                if field_name:
                    # Get the value from session
                    value = session_data.get(field_name) or checkbox_data.get(field_name, {}).get('preselected', [])
                    if value:
                        section_fields.append({
                            'field_name': field_name,
                            'display_name': field.get('label', field_name),
                            'value': value,
                            'type': field.get('type', 'unknown')
                        })
        
        if section_fields:
            review_data[page_info.get('title', page_id)] = {
                'fields': section_fields,
                'page_id': page_id
            }

    # Build li_by_category from calc_result - extracting selected line items
    li_by_category = {}
    for item in calc_result.get('items', []):
        category = item.get('category', 'General')
        if category not in li_by_category:
            li_by_category[category] = []
        
        li_item = {
            'line_code': item.get('line_code', ''),
            'output_title': item.get('output_title', ''),
            'internal_description': item.get('internal_description', ''),
            'output_notes': item.get('output_notes', ''),
            'output_guidance': item.get('output_guidance', ''),
            'unit_cost': item.get('unit_cost', 0),
            'units': item.get('units', 1),
            'line_total': item.get('line_total', 0),
            'pricing_visibility': item.get('pricing_visibility', 'admin_only'),
            'category': item.get('category', 'General')
        }
        li_by_category[category].append(li_item)

    # Build TITLE_MAPPING from page_schemas for field name translation
    TITLE_MAPPING = {}
    for page_id, page_info in page_schemas.get('pages', {}).items():
        compiled_page = compile_builder_beta_page_to_runtime_schema(page_id)
        if compiled_page:
            for field in compiled_page.get('fields', []):
                field_name = field.get('name')
                display_name = field.get('label', field_name)
                if field_name and display_name != field_name:
                    TITLE_MAPPING[field_name] = display_name

    return render_template(
        'review.html',
        review_data=review_data,
        li_by_category=li_by_category,
        totals_by_group=subtotals,
        TITLE_MAPPING=TITLE_MAPPING,
        grand_total=grand_total,
        **ctx
    )"""

if old_render in content:
    content = content.replace(old_render, new_render)
    with open('app/QMapp.py', 'w') as f:
        f.write(content)
    print('Successfully updated the review route')
else:
    print('Could not find the old render_template block')
    print('Looking for pattern...')
    # Try to find it with different whitespace
    import re
    pattern = r"return render_template\(\s*'review\.html'"
    if re.search(pattern, content):
        print('Found render_template for review.html')
    else:
        print('Could not find render_template for review.html')