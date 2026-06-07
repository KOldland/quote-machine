"""
Bug 1 fix (v2): Key remapping in dict→list conversion.
The second _get_line_items_for_page returns dict rows with keys:
  line_code, internal_description, include_default
But the template expects:
  value, label, include_default
Replace the 2-line patch from v1 with a version that remaps the keys.
"""
import os

QMAPP = os.path.join(os.path.dirname(__file__), '..', 'QMapp.py')
content = open(QMAPP, encoding='utf-8').read()

OLD = (
    "\t\t\t_li_raw = _get_line_items_for_page(page_id)\n"
    "\t\t\tli_groups = [{'category': c, 'items': v} for c, v in _li_raw.items()] "
    "if isinstance(_li_raw, dict) else _li_raw\n"
)

NEW = (
    "\t\t\t_li_raw = _get_line_items_for_page(page_id)\n"
    "\t\t\tif isinstance(_li_raw, dict):\n"
    "\t\t\t\tli_groups = [\n"
    "\t\t\t\t\t{'category': c, 'items': [\n"
    "\t\t\t\t\t\t{'value': r.get('line_code', ''),\n"
    "\t\t\t\t\t\t 'label': r.get('internal_description') or r.get('line_code', ''),\n"
    "\t\t\t\t\t\t 'include_default': r.get('include_default') or 'N'}\n"
    "\t\t\t\t\t\tfor r in v\n"
    "\t\t\t\t\t]}\n"
    "\t\t\t\t\tfor c, v in _li_raw.items()\n"
    "\t\t\t\t]\n"
    "\t\t\telse:\n"
    "\t\t\t\tli_groups = _li_raw\n"
)

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    open(QMAPP, 'w', encoding='utf-8').write(content)
    print("✓ Bug 1 v2 patched — key remapping (line_code→value, internal_description→label)")
else:
    print("!! OLD block not found — searching for _li_raw line...")
    for i, line in enumerate(content.splitlines(), 1):
        if '_li_raw = _get_line_items_for_page' in line:
            print(f"   Found at line {i}: {repr(line)}")
