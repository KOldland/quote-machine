import re

content = open('/Users/krisoldland/Documents/QM_web_app/.continue/calculator.md', 'r').read()

old = (
    '**Missing / needs creation:**\n'
    '- ❌ Routes: `'
    '/materials_page'
    '`, `'
    '/further_requirements_page'
    '`, `'
    '/additional_building_work_page'
    '`, `'
    '/additional_costs_page'
    '`, `'
    '/optional_extras_page'
    '`, `'
    '/image_upload_page'
    '`, `'
    '/review'
    '`, `'
    '/submit'
    '`, `'
    '/trigger_production'
    '`, `'
    '/production-page'
    '`\n'
    '- ❌ `review.html` cost matrix (interactive version)\n'
    '- ❌ `form.html` price override inputs for checkbox_options with `allow_user_override=True`\n'
    '- ❌ `form.html` payment schedule overrides at runtime\n'
    '- ❌ Context passing (`session_overrides`, `payment_schedule`) to form/review templates\n'
    '- ❌ JS handlers for price override submission and payment schedule live recalculation'
)

new = (
    '**Already exists (previously marked missing - now verified complete):**\n'
    '- ✅ **All 10 routes now exist** (`materials_page`, `further_requirements_page`, `additional_building_work_page`, `additional_costs_page`, `optional_extras_page`, `image_upload_page`, `review`, `submit`, `trigger_production`, `production-page`) - lines 2993-3430 in QMapp.py\n'
    '- ✅ **`_get_runtime_quote_context()` helper exists** (line 2977) - returns `session_overrides` and `payment_schedule` for templates\n'
    '- ✅ **Context passing wired** - `_get_runtime_quote_context()` is included in all runtime render_template calls across all routes\n'
    '- ✅ **`/submit` route exists** (line 3394) - collects session data into `proposal_data`, redirects to `trigger_production`\n'
    '- ✅ **`/trigger_production` route exists** (line 3414) - POST endpoint, stores trigger event, redirects to `production_page`\n'
    '- ✅ **`/production-page` route exists** (line 3430) - GET endpoint, renders production page\n'
    '\n'
    '**Still missing / needs creation:**\n'
    '- ❌ `form.html` price override inputs for checkbox_options with `allow_user_override=True`\n'
    '- ❌ `form.html` payment schedule overrides at runtime\n'
    '- ❌ `review.html` cost matrix (interactive version with output_group grouping, discounts, payment schedule)\n'
    '- ❌ JS handlers for price override submission and payment schedule live recalculation'
)

if old in content:
    content = content.replace(old, new, 1)
    open('/Users/krisoldland/Documents/QM_web_app/.continue/calculator.md', 'w').write(content)
    print('REPLACED OK')
else:
    print('NOT FOUND - checking for partial match...')
    idx = content.find('**Missing / needs creation:**')
    if idx >= 0:
        print(f'Found at position {idx}')
        print(repr(content[idx:idx+300]))
    else:
        print('Header NOT FOUND either')