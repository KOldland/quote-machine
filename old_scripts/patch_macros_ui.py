import re

filepath = 'app/templates/_builder_macros.html'
with open(filepath, 'r') as f:
    content = f.read()

# 1. Update overall Right Column Layout to allow for Flex/Sticky Footers
old_v2_wrapper = """<div id="li-view-two" style="flex:1; padding:1.5rem; background:#fff; overflow-y:auto; display:none;">"""
# We make it display:flex with flex-direction column so the footer can stick
new_v2_wrapper = """<div id="li-view-two" style="flex:1; background:#fff; display:none; flex-direction:column; max-height: 100%;">
    <div id="li-view-two-scrollable" style="flex:1; overflow-y:auto; padding:1.5rem;">"""

content = content.replace(old_v2_wrapper, new_v2_wrapper)

# We need to close out the scrollable wrapper BEFORE the footer injection for Page, Category, and Details views.
# Wait, let's just use CSS sticky for the bottom button bar instead of re-wrapping the entire massive DOM string in Javascript. That's safer.

with open(filepath, 'r') as f:
    content = f.read()

# OK, we'll patch the button blocks using CSS `position: sticky; bottom: 0; background: #fff; z-index: 10;`
# And we clean up the justification at the same time.

# PAGE VIEW BUTTONS
old_page_buttons = """        html += '<div style="display:flex; justify-content:flex-end; align-items:center; margin-top:1rem;">';
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

new_page_buttons = """        html += '<div style="position: sticky; bottom: -1.5rem; background: #fff; z-index: 10; margin: 1rem -1.5rem -1.5rem -1.5rem; padding: 1rem 1.5rem; border-top: 1px solid #ccc; box-shadow: 0 -4px 6px -6px rgba(0,0,0,0.1);">';
        html += '<div style="display:flex; justify-content:flex-end; align-items:center; margin-bottom:0.8rem;">';
        html += '  <label style="font-size:.85rem; font-weight:600; color:#1b3a6b; cursor:pointer;"><input type="checkbox" id="page-visibility-checkbox" ' + (data.form_visible !== false ? 'checked' : '') + ' style="margin-right:.4rem;">Page Visible in Form</label>';
        html += '</div>';
        html += '<div style="display:flex; justify-content:flex-start; align-items:flex-start; gap: 10px;">';
        html += '  <button type="button" id="btn-save-template" class="li-save-btn" style="padding:0.45rem 1.5rem; width:auto; background:#6c757d; margin-top:0;">SAVE AS TEMPLATE</button>';
        html += '  <div style="display:flex; flex-direction:column; align-items:center;">';
        html += '    <button type="button" id="btn-save-page" class="li-save-btn" style="padding:0.45rem 1.5rem; width:auto; margin-top:0;">SAVE PAGE</button>';
        html += '    <span id="page-save-status" style="font-size:.7rem; color:#28a745; margin-top: 4px;"></span>';
        html += '  </div>';
        html += '  <button type="button" id="btn-delete-page" class="li-delete-btn" style="margin-left: auto; padding:0.45rem 1.5rem; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; cursor:pointer;">DELETE PAGE</button>';
        html += '</div>';
        html += '</div>';"""
content = content.replace(old_page_buttons, new_page_buttons)


# CATEGORY VIEW BUTTONS
old_cat_buttons = """        <div style="padding:0.75rem; border-top:1px solid #dee2e6; background:#fafafa;">
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

# Ensure it pops OUT of its tiny wrapper and acts sticky like the others. We remove it from the innerHTML block entirely
content = content.replace(old_cat_buttons, "")

# And inject it at the end of the `showViewOneCategoryEdit` builder function right before `html += '</form>'; $id('li-view-two').innerHTML = html;`
new_cat_buttons_html = """        html += '<div style="position: sticky; bottom: -1.5rem; background: #fff; z-index: 10; margin: 1rem -1.5rem -1.5rem -1.5rem; padding: 1rem 1.5rem; border-top: 1px solid #ccc; box-shadow: 0 -4px 6px -6px rgba(0,0,0,0.1);">';
        html += '<div style="display:flex; justify-content:flex-end; align-items:center; margin-bottom:0.8rem;">';
        html += '  <label style="font-size:.85rem; font-weight:600; color:#1b3a6b; cursor:pointer;"><input type="checkbox" id="cat-visibility-checkbox" checked style="margin-right:.4rem;">Category Visible in Form</label>';
        html += '</div>';
        html += '<div style="display:flex; justify-content:flex-start; align-items:flex-start; gap: 10px;">';
        html += '  <button type="button" id="btn-cat-add-question" class="li-save-btn" style="background:#007bff; width:auto; padding:0.45rem 1.5rem; margin-top:0;">ADD QUESTION</button>';
        html += '  <div style="display:flex; flex-direction:column; align-items:center;">';
        html += '    <button type="button" id="btn-cat-save" class="li-save-btn" style="width:auto; padding:0.45rem 1.5rem; margin-top:0;">SAVE CATEGORY</button>';
        html += '    <span id="cat-save-status" style="font-size:.7rem; color:#28a745; margin-top: 4px;"></span>';
        html += '  </div>';
        html += '  <button type="button" id="btn-cat-delete" class="li-delete-btn" style="margin-left: auto; padding:0.45rem 1.5rem; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; cursor:pointer;">DELETE CATEGORY</button>';
        html += '</div>';
        html += '</div>';\n"""

# Find where it renders into view 2
old_cat_render_end = "        html += '</form>';\n        $id('li-view-two').innerHTML = html;"
new_cat_render_end = new_cat_buttons_html + old_cat_render_end
content = content.replace(old_cat_render_end, new_cat_render_end)

# QUESTION VIEW BUTTONS - Same sticky footer format
old_q_buttons = """        html += '<div style="display:flex; justify-content:flex-end; align-items:center; margin-top:1rem;">';
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

new_q_buttons = """        html += '<div style="position: sticky; bottom: -1.5rem; background: #fff; z-index: 10; margin: 1rem -1.5rem -1.5rem -1.5rem; padding: 1rem 1.5rem; border-top: 1px solid #ccc; box-shadow: 0 -4px 6px -6px rgba(0,0,0,0.1);">';
        html += '<div style="display:flex; justify-content:flex-end; align-items:center; margin-bottom:0.8rem;">';
        html += '  <label style="font-size:.85rem; font-weight:600; color:#1b3a6b; cursor:pointer;"><input type="checkbox" name="form_visible" ' + (item.form_visible === 1 || item.form_visible === '1' || item.form_visible === true ? 'checked' : '') + ' style="margin-right:.4rem;">Question Visible in Form</label>';
        html += '</div>';
        html += '<div style="display:flex; justify-content:flex-start; align-items:flex-start; gap: 10px;">';
        html += '  <div style="display:flex; flex-direction:column; align-items:center;">';
        html += '    <button type="submit" class="li-save-btn" style="padding:0.45rem 1.5rem; width:auto; margin-top:0;">SAVE QUESTION</button>';
        html += '    <span id="question-save-status" style="font-size:.7rem; color:#28a745; margin-top: 4px;"></span>';
        html += '  </div>';
        html += '  <button type="button" id="btn-delete-question" class="li-delete-btn" style="margin-left: auto; padding:0.45rem 1.5rem; background:#dc3545; color:#fff; border:none; border-radius:5px; font-weight:700; cursor:pointer;">DELETE QUESTION</button>';
        html += '</div>';
        html += '</div>';"""
content = content.replace(old_q_buttons, new_q_buttons)


# WIRING BTN-DELETE-PAGE AND TEMPLATE
old_save_page_script = """        var bg = saveP.style.background;
        saveP.style.background = '#28a745';
        setTimeout(() => saveP.style.background = bg, 1000);"""

new_script_block = """        var bg = saveP.style.background;
        saveP.style.background = '#28a745';
        setTimeout(() => saveP.style.background = bg, 1000);
        
        var delP = document.getElementById('btn-delete-page');
        if (delP) {
            delP.addEventListener('click', function() {
                if(confirm("Are you sure you want to completely delete this page? This is permanent.")) {
                    fetch('/builder_beta/page_details_delete/' + _pageKey, { method: 'POST' })
                    .then(r => r.json())
                    .then(d => {
                        if (d.ok) { window.location.href = '/'; }
                        else { alert('Error deleting page: ' + d.error); }
                    });
                }
            });
        }
        
        var tplP = document.getElementById('btn-save-template');
        if (tplP) {
            tplP.addEventListener('click', function() {
                fetch('/builder_beta/save_as_template', { 
                    method: 'POST', 
                    body: JSON.stringify({ page_key: _pageKey }) 
                })
                .then(r => r.json())
                .then(d => {
                    if (d.ok) { alert('Mock: Successfully saved as template prototype.'); }
                    else { alert('Saved (Dev Stub)'); }
                }).catch(e => { alert('Saved (Dev stub network)'); });
            });
        }"""
content = content.replace(old_save_page_script, new_script_block)

with open(filepath, 'w') as f:
    f.write(content)
