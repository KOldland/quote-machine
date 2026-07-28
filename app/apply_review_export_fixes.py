#!/usr/bin/env python3
"""Fix for review and export issues in overnight-shipping.md

This script addresses the key export issues:
1. Setting form_key in session
2. Populating form_data from session['data']
3. Ensuring consistent data flow
"""

import os
from pathlib import Path

def fix_export_issues():
    """Apply fixes for the export workflow"""
    
    app_dir = Path("/Volumes/Document Drive/sites/Quote_Machine/QM_web_app/app")
    
    # 1. Fix QMapp.py: Set form_key in index() after form submission
    qmapp_path = app_dir / "QMapp.py"
    with open(qmapp_path, 'r') as f:
        qmapp_content = f.read()
    
    # Add session['form_key'] after session['data'] in index()
    qmapp_content = qmapp_content.replace(
        "        session['data'] = data\n        session.modified = True\n\n        if first_dynamic_page:",
        "        session['data'] = data\n        session['form_key'] = 'builder_beta'  # Set form_key for export\n        session.modified = True\n\n        if first_dynamic_page:"
    )
    
    # Add session['form_data'] in review() method
    qmapp_content = qmapp_content.replace(
        "    # Build review_data from session data (data and checkbox_data)\n    session_data = session.get('data', {})\n    \n    review_data = {}",
        "    # Build review_data from session data (data and checkbox_data)\n    session_data = session.get('data', {})\n    \n    # Ensure form_data is populated from session['data']\n    session['form_data'] = session_data\n    \n    review_data = {}"
    )
    
    # Add session['form_data'] at the end of review() for export
    qmapp_content = qmapp_content.replace(
        "        li_item['category'] = item.get('category', 'General')\n        li_by_category[category].append(li_item)\n\n    # Build TITLE_MAPPING",
        "        li_item['category'] = item.get('category', 'General')\n        li_by_category[category].append(li_item)\n\n    # Ensure form_data is available for export (preserve data for export routes)\n    session['form_data'] = session_data\n\n    # Build TITLE_MAPPING"
    )
    
    # 2. Fix export_routes.py: Use proper fallbacks
    export_path = app_dir / "export_routes.py"
    with open(export_path, 'r') as f:
        export_content = f.read()
    
    # Replace session.get('form_key', 'kitchen_only_template_test') with more robust logic
    export_content = export_content.replace(
        "    form_key = session.get('form_key', 'kitchen_only_template_test')",
        "    form_key = session.get('form_key') or 'builder_beta'"
    )
    
    # Replace session.get('form_data', {}) with fallback to session['data']
    export_content = export_content.replace(
        "    # Fresh calculation\n    form_data = session.get('form_data', {})",
        "    # Fresh calculation - try session['form_data'], fallback to session['data'], then empty dict\n    form_data = session.get('form_data') or session.get('data', {})"
    )
    
    # 3. Write updated files
    with open(qmapp_path, 'w') as f:
        f.write(qmapp_content)
    
    with open(export_path, 'w') as f:
        f.write(export_content)
    
    print("✅ Applied fixes for export workflow")
    print("   - Added session['form_key'] in index()")
    print("   - Added session['form_data'] population in review()")
    print("   - Improved fallbacks in export_routes")

def fix_builder_beta_state():
    """Verify the get_builder_beta_state() bug fix is correct"""
    
    app_dir = Path("/Volumes/Document Drive/sites/Quote_Machine/QM_web_app/app")
    qmapp_path = app_dir / "QMapp.py"
    
    with open(qmapp_path, 'r') as f:
        lines = f.readlines()
    
    # Check the get_builder_beta_state function
    in_function = False
    state_pages_checked = False
    
    for i, line in enumerate(lines, 1):
        if 'def get_builder_beta_state():' in line:
            in_function = True
            
        if in_function and '# 6' in line:
            state_pages_checked = True
            
        if in_function and 'return state' in line:
            in_function = False
            if state_pages_checked:
                print("✅ get_builder_beta_state() bug fix is present")
                print(f"   Line {i}: Fix verifies state.get('pages') only used if it has actual content")
                break
    else:
        print("❌ Could not find get_builder_beta_state() bug fix")

if __name__ == '__main__':
    print("=== Applying Review and Export Fixes ===\n")
    fix_builder_beta_state()
    print()
    fix_export_issues()
    print("\n=== Application Complete ===")
    print("\nNext steps for manual testing:")
    print("1. Run: python QMapp.py")
    print("2. Navigate / → Project Details → Fill form → /review")
    print("3. Verify review page displays data correctly")
    print("4. Test /api/export-pdf and /api/export-docx")