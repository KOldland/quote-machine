with open("app/templates/builder_beta.html", "r") as f:
    text = f.read()

new_text = text.replace('    {{ builder_macros.render_line_items_canvas() }}\n', '')
new_text = new_text.replace('<div class="builder-page-wrapper builder-line-items-layout">', '<div class="builder-page-wrapper builder-line-items-layout" style="display: flex; flex-direction: row; height: calc(100vh - 155px); width: 100%; border: 1px solid #dee2e6; background: #fff; overflow: hidden; margin-top: 1rem;">')

with open("app/templates/builder_beta.html", "w") as f:
    f.write(new_text)

