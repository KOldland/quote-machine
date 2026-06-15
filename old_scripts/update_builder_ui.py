import re

filepath = 'app/templates/_builder_macros.html'
with open(filepath, 'r') as f:
    content = f.read()

# 1. Update Category View (View One) HTML
old_cat_buttons = """        <div style="padding:0.75rem; border-top:1px solid #dee2e6; background:#fafafa;">
            <div style="display:flex; gap:10px;">
                <button type="button" id="btn-cat-add-question" class="li-save-btn" style="flex:1; margin-top:0;">ADD QUESTION</button>
                <button type="button" id="btn-cat-save" class="li-save-btn" style="flex:1; background:#6c757d; margin-top:0;">SAVE CATEGORY</button>
                <button type="button" id="btn-cat-delete" class="li-delete-btn" style="flex:0 0 auto; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; padding:0.45rem 1rem; cursor:pointer;">DELETE CATEGORY</button>
            </div>
        </div>"""

new_cat_buttons = """        <div style="padding:0.75rem; border-top:1px solid #dee2e6; background:#fafafa;">
            <div style="display:flex; justify-content:flex-end; align-items:center; margin-bottom:0.5rem;">
                <label style="font-size:.85rem; font-weight:600; color:#1b3a6b; cursor:pointer;">
                    <input type="checkbox" id="cat-visibility-checkbox" checked style="margin-right:.4rem;">Category Visible in Form
                </label>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="flex:1; text-align:left;">
                    <button type="button" id="btn-cat-add-question" class="li-save-btn" style="background:#007bff; width:auto; padding:0.45rem 1rem; margin-top:0;">ADD QUESTION</button>
                </div>
                <div style="flex:1; text-align:center;">
                    <button type="button" id="btn-cat-save" class="li-save-btn" style="width:auto; padding:0.45rem 1rem; margin-top:0;">SAVE CATEGORY</button>
                    <span id="cat-save-status" style="display:block; font-size:.7rem; color:#28a745;"></span>
                </div>
                <div style="flex:1; text-align:right;">
                    <button type="button" id="btn-cat-delete" class="li-delete-btn" style="padding:0.45rem 1rem; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; cursor:pointer;">DELETE CATEGORY</button>
                </div>
            </div>
        </div>"""

content = content.replace(old_cat_buttons, new_cat_buttons)

# 2. Update Page View JS (Render)
old_page_buttons = """        html += '<div style="display:flex; gap:10px; margin-top:1rem; padding-top:0.5rem; border-top:1px solid #eee;">';
        html += '  <button type="button" id="btn-delete-page" class="li-delete-btn" style="flex:0 0 auto; padding:0.45rem 1rem; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; cursor:pointer;">DELETE PAGE</button>';
        html += '  <button type="button" id="btn-save-template" class="li-save-btn" style="flex:1; background:#6c757d; margin-top:0;">SAVE AS TEMPLATE</button>';
        html += '  <button type="button" id="btn-save-page" class="li-save-btn" style="flex:1; margin-top:0;">SAVE PAGE</button>';
        html += '</div>';"""

new_page_buttons = """        html += '<div style="display:flex; justify-content:flex-end; align-items:center; margin-top:1rem;">';
        html += '  <label style="font-size:.85rem; font-weight:600; color:#1b3a6b; cursor:pointer;"><input type="checkbox" id="page-visibility-checkbox" ' + (data.form_visible !== false ? 'checked' : '') + ' style="margin-right:.4rem;">Page Visible in Form</label>';
        html += '</div>';
        html += '<div style="display:flex; justify-content:space-between; margin-top:0.5rem; padding-top:0.5rem; border-top:1px solid #eee; align-items:flex-start;">';
        html += '  <div style="flex:1; text-align:left;">';
        html += '    <button type="button" id="btn-save-template" class="li-save-btn" style="padding:0.45rem 1rem; width:auto; background:#6c757d; margin-top:0;">SAVE AS TEMPLATE</button>';
        html += '  </div>';
        html += '  <div style="flex:1; text-align:center;">';
        html += '    <button type="button" id="btn-save-page" class="li-save-btn" style="padding:0.45rem 1rem; width:auto; margin-top:0;">SAVE PAGE</button>';
        html += '    <br><span id="page-save-status" style="font-size:.7rem; color:#28a745;"></span>';
        html += '  </div>';
        html += '  <div style="flex:1; text-align:right;">';
        html += '    <button type="button" id="btn-delete-page" class="li-delete-btn" style="padding:0.45rem 1rem; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; cursor:pointer;">DELETE PAGE</button>';
        html += '  </div>';
        html += '</div>';"""

content = content.replace(old_page_buttons, new_page_buttons)

if "alert('Page saved!');" in content:
    content = content.replace(
        "if (d.ok) alert('Page saved!');\n                else alert('Error: ' + d.error);", 
        "if (d.ok) { let s = $id('page-save-status'); s.textContent = '✓ Saved Successfully'; setTimeout(()=>s.textContent='',2500); }\n                else alert('Error: ' + d.error);"
    )


# 3. Handle Category visibility checkbox binding via JSON response
old_cat_render = """        $id('li-category-edit-form').querySelector('textarea[name="cat_description"]').value = data.description || '';"""
new_cat_render = """        $id('li-category-edit-form').querySelector('textarea[name="cat_description"]').value = data.description || '';
        $id('cat-visibility-checkbox').checked = (data.form_visible !== false);"""
content = content.replace(old_cat_render, new_cat_render)


# 4. Handle Save Category fetch 
# We need to grab cat-visibility-checkbox
old_cat_save = """        newSaveC.addEventListener('click', function() {
            var frm = $id('li-category-edit-form');
            var desc = frm.querySelector('textarea[name="cat_description"]').value;
            var newName = frm.querySelector('input[name="cat_name"]').value;
            fetch('/builder_beta/category_details_save', {"""

new_cat_save = """        newSaveC.addEventListener('click', function() {
            var frm = $id('li-category-edit-form');
            var desc = frm.querySelector('textarea[name="cat_description"]').value;
            var newName = frm.querySelector('input[name="cat_name"]').value;
            var visible = $id('cat-visibility-checkbox').checked;
            fetch('/builder_beta/category_details_save', {"""
content = content.replace(old_cat_save, new_cat_save)

old_cat_save_body = """body: JSON.stringify({ page_key: _pageKey, old_name: catName, new_name: newName, description: desc })"""
new_cat_save_body = """body: JSON.stringify({ page_key: _pageKey, old_name: catName, new_name: newName, description: desc, form_visible: visible })"""
content = content.replace(old_cat_save_body, new_cat_save_body)

old_cat_save_response = """            }).then(r => r.json()).then(d => {
                if (d.ok) {
                    if (newName !== catName) window.location.reload();
                    else alert('Category Saved');
                }"""
new_cat_save_response = """            }).then(r => r.json()).then(d => {
                if (d.ok) {
                    if (newName !== catName) window.location.reload();
                    else {
                        let stat = $id('cat-save-status');
                        if(stat) { stat.textContent = '✓ Saved Successfully'; setTimeout(()=>stat.textContent='',2500); }
                    }
                }"""
content = content.replace(old_cat_save_response, new_cat_save_response)


# 5. Question View Update HTML (View Two)
# Remove old Form Visible line
old_q_meta = """            _field('line_code',       'Line Code',       'text',   item.line_code   || '', true),
            _selectField('category',  'Category',        item.category || '', allCats),
            _checkField('form_visible', 'Form Visible', item.form_visible === 1 || item.form_visible === '1' || item.form_visible === true),
        ]);"""
new_q_meta = """            _field('line_code',       'Line Code',       'text',   item.line_code   || '', true),
            _selectField('category',  'Category',        item.category || '', allCats)
        ]);"""
content = content.replace(old_q_meta, new_q_meta)

old_q_buttons = """        html += '<div style="display:flex; gap:10px; margin-top:1rem; padding-top:0.5rem; border-top:1px solid #eee;">';
        html += '  <button type="button" id="btn-delete-question" class="li-delete-btn" style="flex:0 0 auto; padding:0.45rem 1rem; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; cursor:pointer;">DELETE QUESTION</button>';
        html += '  <button type="submit" class="li-save-btn" style="flex:1; margin-top:0;">SAVE QUESTION</button>';
        html += '</div>';"""

new_q_buttons = """        html += '<div style="display:flex; justify-content:flex-end; align-items:center; margin-top:1rem;">';
        html += '  <label style="font-size:.85rem; font-weight:600; color:#1b3a6b; cursor:pointer;"><input type="checkbox" name="form_visible" ' + (item.form_visible === 1 || item.form_visible === '1' || item.form_visible === true ? 'checked' : '') + ' style="margin-right:.4rem;">Question Visible in Form</label>';
        html += '</div>';
        html += '<div style="display:flex; justify-content:space-between; margin-top:0.5rem; padding-top:0.5rem; border-top:1px solid #eee; align-items:flex-start;">';
        html += '  <div style="flex:1; text-align:left;">';
        html += '  </div>';
        html += '  <div style="flex:1; text-align:center;">';
        html += '    <button type="submit" class="li-save-btn" style="padding:0.45rem 1rem; width:auto; margin-top:0;">SAVE QUESTION</button>';
        html += '  </div>';
        html += '  <div style="flex:1; text-align:right;">';
        html += '    <button type="button" id="btn-delete-question" class="li-delete-btn" style="padding:0.45rem 1rem; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; cursor:pointer;">DELETE QUESTION</button>';
        html += '  </div>';
        html += '</div>';"""

content = content.replace(old_q_buttons, new_q_buttons)

# Fix Line 1: Save Line Item fix -> was reverting to Save Line Item after saving.
old_save_revert1 = """if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'SAVE LINE ITEM'; }"""
new_save_revert = """if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'SAVE QUESTION'; }"""
content = content.replace(old_save_revert1, new_save_revert)
content = content.replace(old_save_revert1, new_save_revert)
content = content.replace(old_save_revert1, new_save_revert)
# Let's just do a manual replace of 'SAVE LINE ITEM' if it exists
content = content.replace("'SAVE LINE ITEM'", "'SAVE QUESTION'")

# Wait, check for breadcrum code. The user says: 
# "When a save is made we are seeing the breadcrumb get updated with meta information e.g. new 12345678 - I am assuming this is related to the line update and valuable in the back end so lets not remove but it SHOULD NOT BE visble int he UI ata ll and deffo not in the breadcrumb"

# Let's find how breadcrumb is updated on Save Question.
old_bc_update = """                        // Refresh view-two title
                        $id('li-view-two-title').textContent = (item.line_code || '') + ' — ' + (item.output_title || item.internal_description || '');"""
new_bc_update = """                        // Refresh view-two title
                        $id('li-view-two-title').textContent = (item.output_title || item.internal_description || 'Unnamed Question');
                        $id('li-view-two-title').title = $id('li-view-two-title').textContent;"""
content = content.replace(old_bc_update, new_bc_update)


with open(filepath, 'w') as f:
    f.write(content)
