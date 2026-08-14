# Merge Tag Implementation Plan

## Goal
Replace legacy `<dm6>/<dm7>` dimension placeholders in `output_notes` and `output_guidance` with user-submitted follow-up answers using `{choice_value}` merge tags.

## Current State
- Legacy data: `output_notes` contains raw text like `"approx. size is <dm6> metres by <dm7> metres."`
- Follow-up questions store choices in `follow_up_config` JSON and user answers in session as `follow_up_<line_code>`
- No code currently substitutes these placeholders

## Proposed Solution
1. **Utility module** `app/merge_tags.py`:
   - `get_merge_tag_values(page_id, session, get_line_items_for_page)` → dict mapping choice text → user answer
   - `replace_merge_tags(text, merge_tags)` → replaces `{choice}` patterns

2. **Integration points**:
   - `app/QMapp.py:dynamic_page()` — when building `quote_editor_pending_blocks`, apply merge tags to `output_notes`/`output_guidance`
   - `app/quote_editor_routes.py:add_form_block()` — same replacement for snapshot blocks

3. **Migration path**:
   - Existing `<dm6>/<dm7>` strings remain in DB as-is
   - Merge tags only replace `{wide}`/`{deep}` style patterns
   - If no merge tags present, text passes through unchanged

## Files to modify
- `app/merge_tags.py` (new)
- `app/QMapp.py` (import + 2 call sites)
- `app/quote_editor_routes.py` (import + 2 call sites)

## Verification
- Syntax check all modified files
- Confirm `merge_tags.py` is importable
- Verify existing tests pass
