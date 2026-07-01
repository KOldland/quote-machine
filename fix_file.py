with open("app/templates/partials/form_editor.html", "r") as f:
    text = f.read()

# Just manually reconstruct the file because it's short.
new_text = """{% import "_builder_macros.html" as builder_macros %}

<div class="builder-page-wrapper builder-line-items-layout">
    {# ────────────────────────────────────────
       LEFT column – Sections / Categories panel
       ──────────────────────────────────────── #}
    {{ builder_macros.render_li_sections_panel(
        li_categories | default([]),
        current_page_id | default('') ) }}

    {# ────────────────────────────────────────
       MIDDLE column – Canvas + vertical accordion
       ──────────────────────────────────────── #}
    {{ builder_macros.render_line_items_canvas() }}
    
    {# ────────────────────────────────────────
       RIGHT column – Question editor panel
       ──────────────────────────────────────── #}
    {{ builder_macros.render_li_question_panel(
        current_page_id | default('') ) }}
</div>

{# ── Inject builder state for the JS editor ── #}
<script>
document.addEventListener('DOMContentLoaded', function () {
    if (typeof window.initLineItemsCanvas === 'function') {
        window.initLineItemsCanvas();
    }
});

window.blocks = {{ page_config.get('blocks', []) | tojson | safe }};
window.pageId = {{ current_page_id | default('') | tojson | safe }};
window.selectedBlockId = {{ selected_block_id | default('null') | tojson | safe }};
window.builderStateQuestionTypes = {{ builder_state.question_types | default({}) | tojson | safe }};
</script>
<script src="{{ url_for('static', filename='js/builder_beta_modern.js') }}"></script>
"""

with open("app/templates/partials/form_editor.html", "w") as f:
    f.write(new_text)

