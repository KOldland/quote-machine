with open("app/templates/_builder_macros.html", "r") as f:
    text = f.read()

# 1. Page Structure Header (Col 1)
text = text.replace(
    '<div class="li-sections-header">\n        <span style="font-weight:700;font-size:.85rem;color:#1b3a6b;">Categories</span>\n    </div>',
    '<div class="li-sections-header">\n        <span style="font-weight:700;font-size:.85rem;color:#1b3a6b;">Page Structure</span>\n    </div>'
)

# 2. Add fixed height to .li-sections-header
text = text.replace(
    '.li-sections-header {\n    padding:.6rem .75rem; min-height:44px;\n    border-bottom:1px solid #dee2e6; background:#f0f4ff;\n    display:flex; align-items:center;\n}',
    '.li-sections-header {\n    padding:0 .75rem; height:48px; box-sizing:border-box;\n    border-bottom:1px solid #dee2e6; background:#f0f4ff;\n    display:flex; align-items:center;\n}'
)

# 3. Add fixed height to .li-qp-header
text = text.replace(
    'style="display:flex;align-items:center;gap:.5rem;padding:.6rem .75rem;min-height:44px;border-bottom:1px solid #dee2e6;background:#f0f4ff;"',
    'style="display:flex;align-items:center;gap:.5rem;padding:0 .75rem;height:48px;box-sizing:border-box;border-bottom:1px solid #dee2e6;background:#f0f4ff;"'
)

# 4. Fix Questions List Header
text = text.replace(
    '<div style="padding: 0.6rem 0.75rem; font-weight:700; color:#1b3a6b; font-size:0.85rem; background:#f0f4ff; border-bottom:1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center;">\n                <span>Questions in Category</span>',
    '<div style="padding: 0 0.75rem; height: 48px; box-sizing: border-box; font-weight:700; color:#1b3a6b; font-size:0.85rem; background:#f0f4ff; border-bottom:1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center;">\n                <span>Questions</span>'
)

# 5. Fix Question Meta initial label
text = text.replace(
    '<span id="li-view-two-title" style="font-weight:700;font-size:.85rem;color:#1b3a6b;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Question Properties</span>',
    '<span id="li-view-two-title" style="font-weight:700;font-size:.85rem;color:#1b3a6b;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Question Meta</span>'
)

# 6. Flex resizing for Qlist-section
text = text.replace(
    '<div id="qlist-section" style="flex: 0 1 45%; display: flex; flex-direction: column; border-bottom: 2px solid #dee2e6; background: #fff;">',
    '<div id="qlist-section" style="flex: 0 0 38%; min-height: 250px; display: flex; flex-direction: column; border-bottom: 2px solid #dee2e6; background: #fff;">'
)

with open("app/templates/_builder_macros.html", "w") as f:
    f.write(text)

