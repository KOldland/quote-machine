with open("app/templates/_builder_macros.html", "r") as f:
    text = f.read()

# Add CSS for li-canvas-wrap
old_css_start = ".li-category { border:1px solid #dee2e6; border-radius:6px; margin-bottom:.5rem; overflow:hidden; }"
new_css_start = """.li-canvas-wrap { flex: 1; min-width: 300px; display: flex; flex-direction: column; border-right: 1px solid #dee2e6; overflow: hidden; background: #fff; }
.li-category { border:1px solid #dee2e6; border-radius:6px; margin-bottom:.5rem; overflow:hidden; }"""

text = text.replace(old_css_start, new_css_start)

with open("app/templates/_builder_macros.html", "w") as f:
    f.write(text)

