import os
import sqlite3

def patch_qmapp():
    qmapp_path = 'app/QMapp.py'
    with open(qmapp_path, 'r') as f:
        lines = f.readlines()
    
    # 1. Delete lines 1121-1155 (first _get_line_items_for_page)
    # Be safe: find the def _get_line_items_for_page(page_id):
    start_idx = -1
    for i, line in enumerate(lines):
        if 'def _get_line_items_for_page(page_id):' in line:
            start_idx = i
            break
            
    if start_idx != -1:
        end_idx = start_idx
        while not lines[end_idx].strip() == "def build_builder_beta_runtime_context(page_id, sheet_data, page_answers):":
            end_idx += 1
        # Delete from start_idx to end_idx-1
        # Actually it's better to just comment them out or replace with pass
        del lines[start_idx:end_idx-2]
        
    with open(qmapp_path, 'w') as f:
        f.writelines(lines)

patch_qmapp()
print("Patched QMapp")
