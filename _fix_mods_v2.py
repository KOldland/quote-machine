with open('app/templates/_builder_macros.html', 'r') as f:
    lines = f.readlines()

# Remove lines 300-314 (0-indexed 299-313) - modules inside else block
assert '{% if enabled_modules %}' in lines[299]
assert '{% endif %}' in lines[313].strip()
del lines[299:314]

# Find the endif closing {% if li_categories %}
for i, line in enumerate(lines):
    s = line.strip()
    if s == '{% endif %}' and i >= 295 and i < 310:
        # Insert modules after this endif
        modules = [
            '        {% if enabled_modules %}\n',
            '            {% for mod_type in enabled_modules %}\n',
            "            {% set mod_label = {'payment_schedule': 'Payment Schedule', 'page_total': 'Page Total', 'image_upload': 'Image'}[mod_type] or mod_type.replace('_', ' ').title() %}\n",
            "            {% set mod_badge = {'payment_schedule': 'PS', 'page_total': '&Sigma;', 'image_upload': 'IMG'}[mod_type] or 'M' %}\n",
            '            <div class="li-section-item" style="display:flex;align-items:center;border-bottom:1px solid #f3f3f3;">\n',
            '                <button type="button" class="li-section-btn" data-module="{{ mod_type }}" style="flex:1;">\n',
            '                    <span style="background:#495057;color:#fff;font-size:.6rem;font-weight:700;padding:.12rem .35rem;border-radius:3px;margin-right:.3rem;">{{ mod_badge }}</span>{{ mod_label }}\n',
            '                </button>\n',
            '                <div class="li-reorder-controls" style="display:flex;flex-direction:column;margin-right:4px;">\n',
            '                    <button type="button" class="li-move-btn" data-scope="module" data-id="{{ mod_type }}" data-page="{{ form_page_key }}" data-dir="up" style="border:none;background:none;font-size:10px;cursor:pointer;padding:0 4px;color:#888;line-height:1;">&#9650;</button>\n',
            '                    <button type="button" class="li-move-btn" data-scope="module" data-id="{{ mod_type }}" data-page="{{ form_page_key }}" data-dir="down" style="border:none;background:none;font-size:10px;cursor:pointer;padding:0 4px;color:#888;line-height:1;">&#9660;</button>\n',
            '                </div>\n',
            '            </div>\n',
            '            {% endfor %}\n',
            '        {% endif %}\n',
        ]
        for l in reversed(modules):
            lines.insert(i + 1, l)
        break

with open('app/templates/_builder_macros.html', 'w') as f:
    f.writelines(lines)
print('Fixed')