with open("app/templates/_builder_macros.html", "r") as f:
    text = f.read()

# Update JS for showViewOne (Category Details)
text = text.replace(
    "if ($id('li-view-one-title')) $id('li-view-one-title').textContent = title;",
    "if ($id('li-view-one-title')) $id('li-view-one-title').textContent = 'Category Details: ' + title;"
)

# Update JS for showViewTwo (Question)
text = text.replace(
    "$id('li-view-two-title').textContent = name;",
    "$id('li-view-two-title').textContent = 'Question: ' + name;"
)

# Also ensure showViewPage has explicit title update if needed, though it's hardcoded to Page Details in HTML
with open("app/templates/_builder_macros.html", "w") as f:
    f.write(text)

