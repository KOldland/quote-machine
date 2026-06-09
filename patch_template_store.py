import os

def patch_template_store():
    ts_path = 'app/template_store.py'
    with open(ts_path, 'r') as f:
        content = f.read()
    
    old_func = """def get_line_items_for_page(form_page: str, db_path: Optional[Path] = None) -> Dict[str, list]:
    \"\"\"Return form-visible line_items for a given form_page, grouped by category.

    Returns an ordered dict: {category_name: [row_dict, ...]} sorted by
    category ASC, sort_order ASC, line_code ASC.
    Only rows with form_visible=1 are included.
    \"\"\"
    path = db_path or _default_db_path()
    conn = _connect(path)
    rows = conn.execute(
        "SELECT id, line_code, form_page, category, internal_description, include_default, "
        "unit_cost, units, pricing_visibility, output_title, output_notes, output_guidance, "
        "parent_code, item_role, input_type, trigger_parent_code, form_visible, sort_order "
        "FROM line_items WHERE form_page=? AND form_visible=1 AND item_role != 'auto_child' "
        "ORDER BY category ASC, sort_order ASC, line_code ASC",
        (form_page,),
    ).fetchall()
    conn.close()
    result: Dict[str, list] = {}
    for row in rows:
        cat = row["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(dict(row))
    return result"""

    new_func = """def get_line_items_for_page(form_page: str, db_path: Optional[Path] = None) -> Dict[str, list]:
    \"\"\"Return form-visible line_items for a given form_page, grouped by category.

    Returns an ordered dict: {category_name: [row_dict, ...]} sorted by
    category_templates.display_order ASC, then sort_order ASC, line_code ASC.
    Only rows with form_visible=1 are included.
    \"\"\"
    path = db_path or _default_db_path()
    conn = _connect(path)
    
    # Get ordered categories
    cat_query = \"\"\"
        SELECT c.name
        FROM category_templates c
        JOIN page_templates p ON c.page_template_id = p.id
        WHERE p.page_key = ?
        ORDER BY c.display_order ASC
    \"\"\"
    cat_rows = conn.execute(cat_query, (form_page,)).fetchall()
    result: Dict[str, list] = {}
    for r in cat_rows:
        result[r['name']] = []
        
    cat_fallback = len(result) == 0

    rows = conn.execute(
        "SELECT id, line_code, form_page, category, internal_description, include_default, "
        "unit_cost, units, pricing_visibility, output_title, output_notes, output_guidance, "
        "parent_code, item_role, input_type, trigger_parent_code, form_visible, sort_order "
        "FROM line_items WHERE form_page=? AND form_visible=1 AND item_role != 'auto_child' "
        "ORDER BY sort_order ASC, line_code ASC",
        (form_page,),
    ).fetchall()
    conn.close()
    
    for row in rows:
        cat = row["category"]
        if cat not in result:
            result[cat] = []
        result[cat].append(dict(row))
        
    if cat_fallback:
        result = dict(sorted(result.items()))
        
    return result"""

    if old_func in content:
        content = content.replace(old_func, new_func)
        with open(ts_path, 'w') as f:
            f.write(content)
        print("Replaced get_line_items_for_page successfully.")
    else:
        print("Could not find old_func in template_store.py")

patch_template_store()
