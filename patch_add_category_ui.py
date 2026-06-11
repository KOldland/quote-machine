"""
Patch _builder_macros.html:
  1. Expand the bare "Add Category" button into an inline form with name input,
     Save/Cancel buttons, and an "Include in Form" visibility toggle.
  2. Replace the prompt()-based JS with a proper inline-form fetch handler.
"""

import sys

TARGET = 'app/templates/_builder_macros.html'

# ── SEARCH strings (must be character-for-character exact) ─────────────

OLD_HTML = '''    <div style="padding: .5rem; border-top: 1px solid #dee2e6; background: #f0f4ff;">
        <button type="button" id="btn-add-category" class="li-save-btn" style="margin-top:0;" data-page="{{ form_page_key }}">Add Category</button>
    </div>'''

NEW_HTML = '''    <div style="padding: .5rem; border-top: 1px solid #dee2e6; background: #f0f4ff;">
        <button type="button" id="btn-add-category" class="li-save-btn" style="margin-top:0;" data-page="{{ form_page_key }}">+ Add Category</button>
        <div id="add-cat-inline" style="display:none; margin-top:.4rem;">
            <input type="text" id="add-cat-name-input" placeholder="Category name\u2026"
                   style="width:100%; font-size:.82rem; padding:.25rem .4rem; border:1px solid #ccc; border-radius:3px; box-sizing:border-box;">
            <div style="display:flex; gap:.4rem; margin-top:.35rem;">
                <button type="button" id="btn-add-cat-confirm" class="li-save-btn" style="flex:1; margin-top:0;">Save</button>
                <button type="button" id="btn-add-cat-cancel" style="flex:1; font-size:.78rem; padding:.2rem .4rem; border:1px solid #aaa; background:#fff; border-radius:3px; cursor:pointer;">Cancel</button>
            </div>
            <label style="display:flex; align-items:center; gap:.35rem; margin-top:.4rem; font-size:.78rem; color:#444; cursor:pointer;">
                <input type="checkbox" id="add-cat-visible"
                       data-action="toggle-page-visibility"
                       data-page="{{ form_page_key }}"
                       checked style="margin:0; cursor:pointer;">
                &#128065; Include in Form
            </label>
        </div>
    </div>'''

OLD_JS = '''<script>
document.addEventListener('DOMContentLoaded', function() {
    const btnAddCat = document.getElementById('btn-add-category');
    if (btnAddCat) {
        btnAddCat.addEventListener('click', function() {
            const pageKey = this.dataset.page;
            if (!pageKey) {
                alert("Cannot add category: unknown page context.");
                return;
            }
            const catName = prompt("Enter new Category Name:");
            if (!catName) return;
            
            fetch('/builder_beta/category/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ page_key: pageKey, category_name: catName })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) { window.location.reload(); }
                else { alert("Failed to add category: " + data.error); }
            });
        });
    }
});
</script>'''

NEW_JS = '''<script>
document.addEventListener('DOMContentLoaded', function() {
    const btnAddCat    = document.getElementById('btn-add-category');
    const addCatInline = document.getElementById('add-cat-inline');
    const addCatInput  = document.getElementById('add-cat-name-input');
    const btnConfirm   = document.getElementById('btn-add-cat-confirm');
    const btnCancel    = document.getElementById('btn-add-cat-cancel');

    if (btnAddCat) {
        // Toggle inline form open/closed
        btnAddCat.addEventListener('click', function() {
            const isHidden = addCatInline.style.display === 'none' || addCatInline.style.display === '';
            addCatInline.style.display = isHidden ? 'block' : 'none';
            if (isHidden) { addCatInput.focus(); }
        });

        // Cancel — collapse and clear input
        btnCancel.addEventListener('click', function() {
            addCatInput.value = '';
            addCatInline.style.display = 'none';
        });

        // Confirm — POST category to backend
        btnConfirm.addEventListener('click', function() {
            const pageKey = btnAddCat.dataset.page;
            if (!pageKey) { alert("Cannot add category: unknown page context."); return; }
            const catName = addCatInput.value.trim();
            if (!catName) { addCatInput.focus(); return; }
            const csrf = (document.querySelector('[name=csrf_token]') || {}).value || '';
            btnConfirm.disabled = true;
            btnConfirm.textContent = 'Saving\u2026';
            fetch('/builder_beta/category/add', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                body: JSON.stringify({ page_key: pageKey, category_name: catName })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    window.location.reload();
                } else {
                    alert('Failed to add category: ' + data.error);
                    btnConfirm.disabled = false;
                    btnConfirm.textContent = 'Save';
                }
            })
            .catch(function() {
                alert('Network error — category not saved.');
                btnConfirm.disabled = false;
                btnConfirm.textContent = 'Save';
            });
        });

        // Enter key in input triggers confirm
        addCatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') { btnConfirm.click(); }
        });
    }
});
</script>'''

# ── Apply patches ──────────────────────────────────────────────────────

content = open(TARGET).read()

if OLD_HTML not in content:
    print("ERROR: OLD_HTML not found — aborting.")
    sys.exit(1)

if OLD_JS not in content:
    print("ERROR: OLD_JS not found — aborting.")
    sys.exit(1)

content = content.replace(OLD_HTML, NEW_HTML, 1)
content = content.replace(OLD_JS, NEW_JS, 1)

open(TARGET, 'w').write(content)
print("PATCH OK — both replacements applied.")
