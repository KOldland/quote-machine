with open("app/templates/_builder_macros.html", "r") as f:
    text = f.read()

# fix the empty placeholder color / centering styling so it isn't completely hidden
text = text.replace('id="li-view-empty" style="display:flex;flex:1;align-items:center;justify-content:center;color:#aaa;font-size:.9rem;"', 'id="li-view-empty" style="display:flex;flex:1;align-items:center;justify-content:center;color:#aaa;font-size:.9rem;min-height: 200px;"')

with open("app/templates/_builder_macros.html", "w") as f:
    f.write(text)

