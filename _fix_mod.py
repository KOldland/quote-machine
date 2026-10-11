import sys
with open('app/templates/_builder_macros.html', 'r') as f:
    lines = f.readlines()

# Insert modules collection after line 1296 (var desc = ...)
lines.insert(1297, "            var modules = [];\n")
lines.insert(1298, "            document.querySelectorAll('.page-module-cb:checked').forEach(function(cb) { modules.push(cb.value); });\n")

# Replace lines 1302-1308 (then/catch chain) with new version
old_then_start = 1304  # after the insertions shift, this might be different
# Actually, after insertions at 1297/1298, everything shifts by 2
# Let me find the correct lines
for i, line in enumerate(lines):
    if ".then(r => r.json()).then(d => {" in line and i >= 1300:
        idx_then = i
        break

# Find the .catch line
for i in range(idx_then, len(lines)):
    if ".catch(e => alert") in lines[i]:
        idx_catch = i
        break

print(f"then at {idx_then+1}, catch at {idx_catch+1}")

# Remove old then/catch
del lines[idx_then:idx_catch+1]

# Insert new then/catch at idx_then
new = [
    "            }).then(r => r.json()).then(d => {\n",
    "                if (d.ok) {\n",
    "                    return fetch('/builder_beta/page_modules_save/' + _pageKey, {\n",
    "                        method: 'POST',\n",
    "                        headers: {'Content-Type': 'application/json', 'X-CSRFToken': (document.querySelector('[name=csrf_token]') || {}).value || ''},\n",
    "                        body: JSON.stringify({modules: modules})\n",
    "                    }).then(function(r2) { return r2.json(); });\n",
    "                } else {\n",
    "                    throw new Error(d.error || 'Save failed');\n",
    "                }\n",
    "            }).then(d2 => {\n",
    "                if (d2.ok) {\n",
    "                    try { if (typeof showQmToast === 'function') showQmToast('Page saved', true); } catch(e){}\n",
    "                    _saveSelectionState();\n",
    "                    window.location.reload();\n",
    "                } else {\n",
    "                    alert('Error saving modules: ' + (d2.error || 'Unknown'));\n",
    "                }\n",
    "            }).catch(e => alert('Error: ' + e.message));\n",
]
for l in reversed(new):
    lines.insert(idx_then, l)

with open('app/templates/_builder_macros.html', 'w') as f:
    f.writelines(lines)
print('Done')