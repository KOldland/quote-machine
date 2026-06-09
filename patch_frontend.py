import os

file_path = "app/templates/_builder_macros.html"
with open(file_path, "r") as f:
    content = f.read()

search_1 = """        {% if li_categories %}
            {% for cat in li_categories %}
            <button type="button"
                    class="li-section-btn"
                    data-category="{{ cat }}"
                    data-page="{{ form_page_key }}">
                {{ cat }}
            </button>
            {% endfor %}
        {% else %}"""

replace_1 = """        {% if li_categories %}
            {% for cat in li_categories %}
            {% set cat_name = cat.name if cat is mapping else cat %}
            {% set cat_id = cat.id if cat is mapping else cat_name %}
            <div class="li-section-item" style="display:flex;align-items:center;border-bottom:1px solid #f3f3f3;">
                <button type="button"
                        class="li-section-btn"
                        data-category="{{ cat_name }}"
                        data-id="{{ cat_id }}"
                        data-page="{{ form_page_key }}"
                        style="flex:1;">
                    {{ cat_name }}
                </button>
                <div class="li-reorder-controls" style="display:flex;flex-direction:column;margin-right:4px;">
                    <button type="button" class="li-move-btn" data-scope="category" data-id="{{ cat_id }}" data-dir="up" data-page="{{ form_page_key }}" style="border:none;background:none;font-size:10px;cursor:pointer;padding:0 4px;color:#888;">▲</button>
                    <button type="button" class="li-move-btn" data-scope="category" data-id="{{ cat_id }}" data-dir="down" data-page="{{ form_page_key }}" style="border:none;background:none;font-size:10px;cursor:pointer;padding:0 4px;color:#888;">▼</button>
                </div>
            </div>
            {% endfor %}
        {% else %}"""

search_2 = """        items.forEach(function (item) {
            var desc = item.internal_description || item.output_title || '—';
            var vis  = item.form_visible ? '✓' : '–';
            html += '<div class="li-qlist-row" data-id="' + item.id + '">'
                +   '<span class="li-qlist-desc" title="' + _esc(desc) + '">' + _esc(desc) + '</span>'
                +   '<span class="li-qlist-vis">' + vis + '</span>'
                + '</div>';
        });
        list.innerHTML = html;
        list.querySelectorAll('.li-qlist-row').forEach(function (row) {
            row.addEventListener('click', function () {
                list.querySelectorAll('.li-qlist-row').forEach(function (r) { r.classList.remove('selected'); });"""

replace_2 = """        items.forEach(function (item) {
            var desc = item.internal_description || item.output_title || '—';
            var vis  = item.form_visible ? '✓' : '–';
            html += '<div class="li-qlist-row" data-id="' + item.id + '">'
                +   '<span class="li-qlist-desc" title="' + _esc(desc) + '">' + _esc(desc) + '</span>'
                +   '<span class="li-qlist-vis">' + vis + '</span>'
                +   '<div class="li-reorder-controls" style="display:flex;flex-direction:column;align-items:center;">'
                +       '<button type="button" class="li-move-btn" data-scope="question" data-id="' + item.id + '" data-dir="up" style="border:none;background:none;font-size:10px;cursor:pointer;padding:0 4px;color:#888;">▲</button>'
                +       '<button type="button" class="li-move-btn" data-scope="question" data-id="' + item.id + '" data-dir="down" style="border:none;background:none;font-size:10px;cursor:pointer;padding:0 4px;color:#888;">▼</button>'
                +   '</div>'
                + '</div>';
        });
        list.innerHTML = html;
        list.querySelectorAll('.li-qlist-row').forEach(function (row) {
            row.addEventListener('click', function (e) {
                if (e.target.closest('.li-move-btn')) return;
                list.querySelectorAll('.li-qlist-row').forEach(function (r) { r.classList.remove('selected'); });"""

search_3 = """.li-qlist-row {
    display:grid;
    grid-template-columns:1fr 60px;
    gap:.4rem; align-items:center;
    padding:.35rem .75rem; font-size:.8rem; cursor:pointer;
    border-bottom:1px solid #f3f3f3; transition:background .1s;
}"""

replace_3 = """.li-qlist-row {
    display:grid;
    grid-template-columns:1fr 40px 30px;
    gap:.4rem; align-items:center;
    padding:.35rem .75rem; font-size:.8rem; cursor:pointer;
    border-bottom:1px solid #f3f3f3; transition:background .1s;
}
.li-move-btn:hover { color: #1b3a6b !important; }"""

search_4 = """.li-section-btn {
    display:block; width:100%; text-align:left;
    padding:.45rem .85rem; border:none; background:none;
    font-size:.82rem; color:#1b3a6b; cursor:pointer;
    border-left:3px solid transparent;
    transition:background .1s, border-color .1s;
}"""

replace_4 = """.li-section-btn {
    display:block; text-align:left;
    padding:.45rem .85rem; border:none; background:none;
    font-size:.82rem; color:#1b3a6b; cursor:pointer;
    border-left:3px solid transparent;
    transition:background .1s, border-color .1s;
}"""

search_5 = """    // ── Back button (View Two → View One) ─────────────────────────────────"""

replace_5 = """    // ── Reorder AJAX Handler ───────────────────────────────────────────────
    document.addEventListener('click', function(e) {
        var btn = e.target.closest('.li-move-btn');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();

        var scope = btn.dataset.scope;
        var dir = btn.dataset.dir;
        var identifier = parseInt(btn.dataset.id, 10);
        var pageKey = btn.dataset.page || _pageKey;

        fetch('/builder_beta/swap_order', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                scope: scope,
                identifier: identifier,
                direction: dir,
                page_key: pageKey
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                if (scope === 'category') {
                    window.location.reload();
                } else if (scope === 'question') {
                    var url = '/builder_beta/line_items_json?page=' + encodeURIComponent(_pageKey) + '&category=' + encodeURIComponent(_activeCategory);
                    fetch(url, {credentials: 'same-origin'})
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            _categoryItems = [];
                            if (data.categories && data.categories.length > 0) {
                                _categoryItems = data.categories[0].items || [];
                            }
                            renderQuestionList(_categoryItems);
                        });
                }
            } else {
                alert('Swap failed: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(function(e) {
            alert('Swap request failed.');
        });
    });

    // ── Back button (View Two → View One) ─────────────────────────────────"""


if search_1 in content:
    content = content.replace(search_1, replace_1, 1)
    print("Patched categories HTML")
else:
    print("Could not find search_1")

if search_2 in content:
    content = content.replace(search_2, replace_2, 1)
    print("Patched questions HTML")
else:
    print("Could not find search_2")

if search_3 in content:
    content = content.replace(search_3, replace_3, 1)
    print("Patched questions CSS")
else:
    print("Could not find search_3")

if search_4 in content:
    content = content.replace(search_4, replace_4, 1)
    print("Patched categories CSS")
else:
    print("Could not find search_4")

if search_5 in content:
    content = content.replace(search_5, replace_5, 1)
    print("Patched AJAX handler")
else:
    print("Could not find search_5")

with open(file_path, "w") as f:
    f.write(content)
