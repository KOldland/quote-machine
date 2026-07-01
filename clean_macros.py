with open("app/templates/_builder_macros.html", "r") as f:
    text = f.read()

import re
# Remove the old .li-3col-canvas style block
text = re.sub(r'/\* Canvas wrapper — shared by all edit-mode views \*/\s*\.li-3col-canvas \{[^}]+\}\s*', '', text)

with open("app/templates/_builder_macros.html", "w") as f:
    f.write(text)

