new_text = """{% import "_builder_macros.html" as builder_macros %}

<div class="builder-page-wrapper builder-line-items-layout" style="display: flex; flex-direction: row; height: calc(100vh - 155px); width: 100%; border: 1px solid #dee2e6; background: #fff; overflow: hidden; margin-top: 1rem;">
    
    {# ────────────────────────────────────────
       LEFT column – Sections / Categories panel
       ──────────────────────────────────────── #}
    {{ builder_macros.render_li_sections_panel(
        li_categories | default([]),
        current_page_id | default('') ) }}

    {# ────────────────────────────────────────
       COLUMNS 2 & 3 - Meta + Questions Panel
       ──────────────────────────────────────── #}
    {{ builder_macros.render_li_question_panel(
        current_page_id | default('') ) }}

</div>

{# ── Inject builder state for the JS editor ── #}
<script>
window.blocks = {{ page_config.get('blocks', []) | tojson | safe }};
window.pageId = {{ current_page_id | default('') | tojson | safe }};
window.selectedBlockId = {{ selected_block_id | default('null') | tojson | safe }};
window.builderStateQuestionTypes = {{ builder_state.question_types | default({}) | tojson | safe }};
</script>

"""

with open("app/templates/partials/form_editor.html", "w") as f:
    f.write(new_text)
