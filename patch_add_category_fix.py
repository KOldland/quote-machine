"""
Two fixes:
 1. QMapp.py generic form route — add missing form_page_key=page_key to the
    edit_mode render_template call (line ~4450 block).
 2. _builder_macros.html — remove the eye emoji; replace with plain text "Visible".
"""
import sys

# ── Fix 1: QMapp.py ───────────────────────────────────────────────────────────

QMAPP = 'app/QMapp.py'

OLD_QMAPP = (
    '\t\t\tpricing_modes=sorted(ALLOWED_BLOCK_PRICING_MODES),\n'
    '\t\t\tli_categories=[],\n'
    '\t\t\tdb_pages=db_pages,\n'
    '\t\t)'
)

NEW_QMAPP = (
    '\t\t\tpricing_modes=sorted(ALLOWED_BLOCK_PRICING_MODES),\n'
    '\t\t\tli_categories=[],\n'
    '\t\t\tform_page_key=page_key,\n'
    '\t\t\tdb_pages=db_pages,\n'
    '\t\t)'
)

content = open(QMAPP).read()
if OLD_QMAPP not in content:
    print("ERROR: QMapp.py anchor not found — aborting Fix 1.")
    sys.exit(1)
count = content.count(OLD_QMAPP)
if count > 1:
    print(f"WARNING: QMapp.py anchor appears {count} times — replacing first only.")
content = content.replace(OLD_QMAPP, NEW_QMAPP, 1)
open(QMAPP, 'w').write(content)
print("Fix 1 OK — form_page_key=page_key added to generic route render_template.")

# ── Fix 2: _builder_macros.html — remove eye emoji ───────────────────────────

MACROS = 'app/templates/_builder_macros.html'

OLD_EMOJI = '                &#128065; Include in Form'
NEW_LABEL = '                Include in Form'

content2 = open(MACROS).read()
if OLD_EMOJI not in content2:
    print("ERROR: emoji anchor not found in _builder_macros.html — aborting Fix 2.")
    sys.exit(1)
content2 = content2.replace(OLD_EMOJI, NEW_LABEL, 1)
open(MACROS, 'w').write(content2)
print("Fix 2 OK — eye emoji removed from Include in Form label.")
