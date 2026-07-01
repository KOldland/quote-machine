with open("app/templates/_builder_macros.html", "r") as f:
    text = f.read()

text = text.replace(
    "$id('li-view-two-title').textContent = (item.output_title || item.internal_description || 'Unnamed Question');",
    "$id('li-view-two-title').textContent = 'Question: ' + (item.output_title || item.internal_description || 'Unnamed Question');"
)

with open("app/templates/_builder_macros.html", "w") as f:
    f.write(text)

