import re

with open("app/templates/_builder_macros.html", "r") as f:
    text = f.read()

html_part = """<div class="li-question-panel" id="li-question-panel" data-page="{{ form_page_key }}">

    {# View Page — Page Details #}
    <div id="li-view-page" style="display:none;flex-direction:column;height:100%;">
        <div class="li-qp-header" style="display:flex;align-items:center;gap:.5rem;padding:.6rem .75rem;min-height:44px;border-bottom:1px solid #dee2e6;background:#f0f4ff;">
            <span style="font-weight:700;font-size:.85rem;color:#1b3a6b;flex:1;" class="page-title-label">Page Details</span>
        </div>
        <div id="li-page-editor-content" style="overflow-y:auto;flex:1;padding:.75rem;">
            {# populated via JS #}
        </div>
    </div>

    {# View One — Category Details #}
    <div id="li-view-one" style="display:none;flex-direction:column;height:100%; max-width:100%; overflow-x:hidden;">
        <div class="li-qp-header" style="display:flex;align-items:center;gap:.5rem;padding:.6rem .75rem;min-height:44px;border-bottom:1px solid #dee2e6;background:#f0f4ff;">
            <span class="breadcrumb-trail" style="font-weight:600;font-size:.85rem;color:#6c757d;flex:1;">
                <a href="#" class="bc-page" style="color:#1b3a6b;text-decoration:none;">Page Details</a> 
                <span style="margin:0 4px;">›</span> 
                <span id="li-view-one-title" style="color:#333;">Category</span>
            </span>
            <span id="li-view-one-count" style="font-size:.75rem;color:#6c757d;"></span>
        </div>
        
        <div id="li-category-content-wrap" style="flex:1; overflow-y:auto; overflow-x:hidden; padding:0 0 4rem 0;">
            <div id="li-category-editor" style="padding:0.75rem;">
                {# populated via JS #}
            </div>
            
            <div style="padding: 0.75rem 0.75rem 0 0.75rem; font-weight:700; color:#444; font-size:0.85rem; border-top: 1px solid #eee;">Questions in Category</div>
            <div id="li-question-list" style="padding:.25rem 0;">
                <p style="color:#999;font-size:.85rem;padding:.5rem .75rem;">Loading questions...</p>
            </div>
        </div>
        
    </div>

    {# View Two — question editor for selected question #}
    <div id="li-view-two" style="display:none;flex-direction:column;height:100%;">
        <div class="li-qp-header" style="display:flex;align-items:center;gap:.5rem;padding:.6rem .75rem;min-height:44px;border-bottom:1px solid #dee2e6;background:#f0f4ff;">
            <span class="breadcrumb-trail" style="font-weight:600;font-size:.85rem;color:#6c757d;flex:1;">
                <a href="#" class="bc-page" style="color:#1b3a6b;text-decoration:none;">Page Details</a> 
                <span style="margin:0 4px;">›</span> 
                <a href="#" class="bc-cat" style="color:#1b3a6b;text-decoration:none;">Category</a>
                <span style="margin:0 4px;">›</span> 
                <span id="li-view-two-title" style="color:#333;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Question</span>
            </span>
            <span id="li-save-status-v2" style="font-size:.75rem;color:#28a745;min-width:60px;text-align:right;"></span>
        </div>
        <div id="li-editor-content" style="overflow-y:auto;flex:1;padding:.75rem;">
            {# populated via JS #}
        </div>
    </div>

    {# Empty state #}
    <div id="li-view-empty" style="display:flex;flex:1;align-items:center;justify-content:center;color:#aaa;font-size:.9rem;">
        Select a category to begin editing
    </div>
</div>"""

new_html = """<!-- COLUMNS 2 & 3: DETAILS AND QUESTIONS -->
<div class="li-question-panel" id="li-question-panel" data-page="{{ form_page_key }}" style="display: flex; flex: 1; flex-direction: row; min-width: 0;">

    <!-- ====== COLUMN 2: Meta (Category / Page) ====== -->
    <div id="col2-meta" style="flex: 1; border-right: 1px solid #dee2e6; display: flex; flex-direction: column; overflow-y: auto; background: #fff;">
        <div id="li-view-empty" style="display:flex;flex:1;align-items:center;justify-content:center;color:#aaa;font-size:.9rem;">
            Select a category or page details
        </div>
        
        {# View Page — Page Details #}
        <div id="li-view-page" style="display:none;flex-direction:column;height:100%;">
            <div class="li-qp-header" style="display:flex;align-items:center;gap:.5rem;padding:.6rem .75rem;min-height:44px;border-bottom:1px solid #dee2e6;background:#f0f4ff;">
                <span style="font-weight:700;font-size:.85rem;color:#1b3a6b;flex:1;" class="page-title-label">Page Details</span>
            </div>
            <div id="li-page-editor-content" style="overflow-y:auto;flex:1;padding:.75rem;">
                {# populated via JS #}
            </div>
        </div>

        {# View One — Category Details #}
        <div id="li-view-one" style="display:none;flex-direction:column;height:100%;">
            <div class="li-qp-header" style="display:flex;align-items:center;gap:.5rem;padding:.6rem .75rem;min-height:44px;border-bottom:1px solid #dee2e6;background:#f0f4ff;">
                <span class="breadcrumb-trail" style="font-weight:600;font-size:.85rem;color:#6c757d;flex:1;">
                    <span id="li-view-one-title" style="color:#333;">Category Details</span>
                </span>
            </div>
            <div id="li-category-content-wrap" style="flex:1; overflow-y:auto; overflow-x:hidden; padding:0;">
                <div id="li-category-editor" style="padding:0.75rem;">
                    {# populated via JS #}
                </div>
            </div>
        </div>
    </div>

    <!-- ====== COLUMN 3: Questions List & Question Meta ====== -->
    <div id="col3-questions" style="flex: 1.2; display: flex; flex-direction: column; overflow: hidden; background: #fafafa;">
        
        <!-- Top Half: Question List -->
        <div id="qlist-section" style="flex: 0 1 45%; display: flex; flex-direction: column; border-bottom: 2px solid #dee2e6; background: #fff;">
            <div style="padding: 0.6rem 0.75rem; font-weight:700; color:#1b3a6b; font-size:0.85rem; background:#f0f4ff; border-bottom:1px solid #dee2e6; display: flex; justify-content: space-between; align-items: center;">
                <span>Questions in Category</span>
                <span id="li-view-one-count" style="font-size: 0.75rem; font-weight: normal; color: #666;"></span>
            </div>
            <div id="li-question-list" style="overflow-y: auto; flex: 1; padding: 0;">
                <p style="color:#aaa; font-size:0.85rem; text-align:center; margin-top:2rem;">Select a category to see questions</p>
            </div>
            <div id="add-question-wrap" style="padding: 0.5rem; background: #fff; border-top: 1px solid #eee; display: none;">
                <button type="button" id="btn-add-question" style="width: 100%; padding: 0.4rem; background: #1b3a6b; color: #fff; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">+ Add Question to Category</button>
            </div>
        </div>

        <!-- Bottom Half: Question Editor -->
        <div id="qmeta-section" style="flex: 1 1 55%; display: flex; flex-direction: column; overflow-y: auto; background: #fff;">
             <div id="li-view-empty-q" style="display:flex;flex:1;align-items:center;justify-content:center;color:#aaa;font-size:.9rem;">
                 Select a question to edit
             </div>
             <div id="li-view-two" style="display:none;flex-direction:column;height:100%;">
                <div class="li-qp-header" style="display:flex;align-items:center;gap:.5rem;padding:.6rem .75rem;min-height:44px;border-bottom:1px solid #dee2e6;background:#f0f4ff;">
                    <span id="li-view-two-title" style="font-weight:700;font-size:.85rem;color:#1b3a6b;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">Question Properties</span>
                    <span id="li-save-status-v2" style="font-size:.75rem;color:#28a745;min-width:60px;text-align:right;"></span>
                </div>
                <div id="li-editor-content" style="padding:.75rem; background: #fff; flex: 1;">
                    {# populated via JS #}
                </div>
             </div>
        </div>
    </div>

</div>"""

text = text.replace(html_part, new_html)

# Also let's update the Javascript view swapping methods
js_old_views = """    // ── View switching ─────────────────────────────────────────────────────
    function showEmpty() {
        $id('li-view-empty').style.display = 'flex';
        $id('li-view-page').style.display  = 'none';
        $id('li-view-one').style.display   = 'none';
        $id('li-view-two').style.display   = 'none';
    }
    function showViewPage() {
        $id('li-view-empty').style.display = 'none';
        $id('li-view-page').style.display  = 'flex';
        $id('li-view-one').style.display   = 'none';
        $id('li-view-two').style.display   = 'none';
        renderPageEditor();
    }
    function showViewOne(title) {
        $id('li-view-empty').style.display = 'none';
        $id('li-view-page').style.display  = 'none';
        $id('li-view-one').style.display   = 'flex';
        $id('li-view-two').style.display   = 'none';
        if (title) {
            $id('li-view-one-title').textContent = title;
            renderCategoryEditor(title);
        }
        document.querySelectorAll('.bc-page').forEach(function(el) { el.textContent = __getCleanPageTitle(); });
    }
    function showViewTwo(item) {
        $id('li-view-empty').style.display = 'none';
        $id('li-view-page').style.display  = 'none';
        $id('li-view-one').style.display   = 'none';
        $id('li-view-two').style.display   = 'flex';
        var name = (item.output_title || item.internal_description || 'Unnamed Question');
        $id('li-view-two-title').textContent = name;
        $id('li-view-two-title').title = name;
        document.querySelectorAll('.bc-cat').forEach(function(el) { el.textContent = _activeCategory; });
        renderEditorForm(item);
    }"""

js_new_views = """    // ── View switching ─────────────────────────────────────────────────────
    
    function hideQuestionEditor() {
        if ($id('li-view-empty-q')) $id('li-view-empty-q').style.display = 'flex';
        if ($id('li-view-two')) $id('li-view-two').style.display = 'none';
        _activeItem = null;
        document.querySelectorAll('.li-qlist-row').forEach(function(r) { r.classList.remove('selected'); });
    }

    function showEmpty() {
        $id('li-view-empty').style.display = 'flex';
        $id('li-view-page').style.display  = 'none';
        $id('li-view-one').style.display   = 'none';
        
        $id('li-question-list').innerHTML = '<p style="color:#aaa; font-size:0.85rem; text-align:center; margin-top:2rem;">Select a category to see questions</p>';
        $id('li-view-one-count').textContent = '';
        if ($id('add-question-wrap')) $id('add-question-wrap').style.display = 'none';

        hideQuestionEditor();
    }
    function showViewPage() {
        $id('li-view-empty').style.display = 'none';
        $id('li-view-page').style.display  = 'flex';
        $id('li-view-one').style.display   = 'none';
        
        $id('li-question-list').innerHTML = '<p style="color:#aaa; font-size:0.85rem; text-align:center; margin-top:2rem;">Page Details selected.<br>Select a category to see its questions.</p>';
        $id('li-view-one-count').textContent = '';
        if ($id('add-question-wrap')) $id('add-question-wrap').style.display = 'none';

        hideQuestionEditor();
        renderPageEditor();
    }
    function showViewOne(title) {
        $id('li-view-empty').style.display = 'none';
        $id('li-view-page').style.display  = 'none';
        $id('li-view-one').style.display   = 'flex';
        
        if ($id('add-question-wrap')) $id('add-question-wrap').style.display = 'block';

        if (title) {
            if ($id('li-view-one-title')) $id('li-view-one-title').textContent = title;
            renderCategoryEditor(title);
        }
        hideQuestionEditor();
        
        // Let lists show their components
    }
    function showViewTwo(item) {
        // Keeps the list layer open (ViewOne handles list and cat details now independently of ViewTwo)
        $id('li-view-empty-q').style.display = 'none';
        $id('li-view-two').style.display   = 'flex';
        
        var name = (item.output_title || item.internal_description || 'Unnamed Question');
        if ($id('li-view-two-title')) {
            $id('li-view-two-title').textContent = name;
            $id('li-view-two-title').title = name;
        }
        
        renderEditorForm(item);
    }"""

text = text.replace(js_old_views, js_new_views)


# Add the Add Question listener
js_add_hook_start = "    var pageDetailsBtn = $id('btn-page-details');"
js_add_hook_new = """    var btnAddQuestion = $id('btn-add-question');
    if (btnAddQuestion) {
        btnAddQuestion.addEventListener('click', function() {
            if (!_activeCategory) { alert("Please select a category first."); return; }
            
            var payload = {
                page_key: _pageKey,
                category: _activeCategory,
                internal_description: "New Question",
                block_type: "text_input"
            };
            
            btnAddQuestion.disabled = true;
            btnAddQuestion.textContent = 'Adding...';
            
            fetch('/builder_beta/line_item_add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': (document.querySelector('[name=csrf_token]') || {}).value || ''},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(d => {
                btnAddQuestion.disabled = false;
                btnAddQuestion.textContent = '+ Add Question to Category';
                if (d.success) {
                    var activeBtn = document.querySelector('.li-section-btn[data-category="'+_activeCategory+'"]');
                    if (activeBtn) activeBtn.click();
                } else {
                    alert('Error adding question: ' + (d.error || 'Unknown error'));
                }
            }).catch(e => {
                btnAddQuestion.disabled = false;
                btnAddQuestion.textContent = '+ Add Question to Category';
                alert('Network error adding question');
            });
        });
    }

    var pageDetailsBtn = $id('btn-page-details');"""
text = text.replace(js_add_hook_start, js_add_hook_new)


# Re-selecting item on refresh
render_list_update = """            row.addEventListener('click', function (e) {
                if (e.target.closest('.li-move-btn')) return;
                list.querySelectorAll('.li-qlist-row').forEach(function (r) { r.classList.remove('selected'); });
                row.classList.add('selected');
                var id = parseInt(row.dataset.id, 10);
                _activeItem = items.find(function (i) { return i.id === id; }) || null;
                if (_activeItem) { showViewTwo(_activeItem); }
            });
        });
    }"""
    
render_list_new = """            row.addEventListener('click', function (e) {
                if (e.target.closest('.li-move-btn')) return;
                list.querySelectorAll('.li-qlist-row').forEach(function (r) { r.classList.remove('selected'); });
                row.classList.add('selected');
                var id = parseInt(row.dataset.id, 10);
                _activeItem = items.find(function (i) { return i.id === id; }) || null;
                if (_activeItem) { showViewTwo(_activeItem); }
            });
        });
        
        // Re-select active item if applicable
        if (_activeItem) {
            var el = list.querySelector('.li-qlist-row[data-id="'+_activeItem.id+'"]');
            if (el) { el.classList.add('selected'); showViewTwo(_activeItem); }
        }
    }"""

text = text.replace(render_list_update, render_list_new)


with open("app/templates/_builder_macros.html", "w") as f:
    f.write(text)

print("Updated question panel wrapper and JS successfully!")
