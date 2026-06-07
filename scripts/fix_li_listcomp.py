"""
Fix: replace unsafe nested listcomp in build_builder_beta_runtime_context
with a defensive for-loop that validates types at each level.
Also appends the new pitfall to context.md.
"""
import os

BASE = os.path.join(os.path.dirname(__file__), '..')

# ── Fix QMapp.py ──────────────────────────────────────────────────────────────
qmapp = os.path.join(BASE, 'QMapp.py')
content = open(qmapp, encoding='utf-8').read()

OLD = (
    "\t\t\tif not stored:\n"
    "\t\t\t\tstored = [item['value'] for grp in li_groups for item in grp['items']\n"
    "\t\t\t\t         if item.get('include_default') == 'Y']"
)

NEW = (
    "\t\t\tif not stored:\n"
    "\t\t\t\tstored = []\n"
    "\t\t\t\tfor grp in (li_groups or []):\n"
    "\t\t\t\t\tif not isinstance(grp, dict):\n"
    "\t\t\t\t\t\tcontinue\n"
    "\t\t\t\t\tfor item in (grp.get('items') or []):\n"
    "\t\t\t\t\t\tif not isinstance(item, dict):\n"
    "\t\t\t\t\t\t\tcontinue\n"
    "\t\t\t\t\t\tif item.get('include_default') == 'Y' and item.get('value'):\n"
    "\t\t\t\t\t\t\tstored.append(item['value'])"
)

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    open(qmapp, 'w', encoding='utf-8').write(content)
    print("✓ QMapp.py listcomp replaced with defensive for-loop")
else:
    print("!! QMapp.py anchor NOT FOUND — check whitespace")

# ── Append pitfall to context.md ──────────────────────────────────────────────
context_path = os.path.join(BASE, '.continue', 'prompts', 'context.md')
pitfall = """
### Avoid Nested Listcomps Over DB-Backed Grouped Data
`TypeError: string indices must be integers` occurs when a nested listcomp iterates over a grouped data structure that has an unexpected shape — e.g., `grp['items']` holds a string instead of a list, so iterating over it yields single characters. The error message is misleading and hard to trace.

**Never flatten grouped DB helper results with a nested listcomp.** Always use a defensive for-loop with `isinstance` checks:

```python
# UNSAFE — cryptic TypeError if any grp or item has wrong shape
stored = [item['value'] for grp in li_groups for item in grp['items']
         if item.get('include_default') == 'Y']

# SAFE — validates types at each level
stored = []
for grp in (li_groups or []):
    if not isinstance(grp, dict):
        continue
    for item in (grp.get('items') or []):
        if not isinstance(item, dict):
            continue
        if item.get('include_default') == 'Y' and item.get('value'):
            stored.append(item['value'])
```

This also protects against `None` returns from DB helpers or empty `items` keys.
"""

existing = open(context_path, encoding='utf-8').read()
if '### Avoid Nested Listcomps' not in existing:
    with open(context_path, 'a', encoding='utf-8') as f:
        f.write(pitfall)
    print("✓ Pitfall appended to context.md")
else:
    print("  (pitfall already present in context.md)")

print("\nDone.")
