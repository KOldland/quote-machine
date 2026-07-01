with open("app/templates/partials/form_editor.html", "r") as f:
    text = f.read()

new_text = text.replace(
    '{{ builder_macros.render_li_sections_panel(',
    '<div class="builder-page-wrapper builder-line-items-layout">\n    {{ builder_macros.render_li_sections_panel('
)

new_text = new_text.replace(
    "current_page_id | default('') ) }}",
    "current_page_id | default('') ) }}\n    </div>", 
    1 # Be careful, replace only the last occurrence or both? wait, the last occurrence is the third macro.
)

with open("test.html", "w") as f:
    f.write(new_text)
