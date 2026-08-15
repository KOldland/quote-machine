"""Merge tag utilities for output substitution."""
import json


def get_merge_tag_values(page_id, session, get_line_items_for_page, page_blocks=None):
    """Build a dict of merge tag values from session form data.
    
    Scans follow-up questions for the page and maps choice values
    to the user's submitted answers. Supports multiple follow-ups per question.
    Also supports {selected} for any dropdown_select block on the page.
    """
    try:
        page_items = get_line_items_for_page(page_id)
    except Exception:
        return {}

    checkbox_data = session.get('checkbox_data', {})
    form_data = session.get('data', {})
    answers = dict(form_data)
    answers.update(checkbox_data)

    merge_tags = {}
    for category_items in page_items.values():
        for item in category_items:
            follow_up_config = item.get('follow_up_config')
            if not follow_up_config:
                continue
            configs = []
            if isinstance(follow_up_config, str):
                try:
                    parsed = json.loads(follow_up_config)
                    configs = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    continue
            elif isinstance(follow_up_config, list):
                configs = follow_up_config
            else:
                continue

            for idx, cfg in enumerate(configs):
                choices = cfg.get('choices', [])
                if not choices:
                    continue
                if len(configs) == 1:
                    field_name = f"follow_up_{item.get('line_code', '')}"
                else:
                    field_name = f"follow_up_{item.get('line_code', '')}_{idx}"
                user_answer = answers.get(field_name, '')
                if not user_answer:
                    user_answer = answers.get(f"follow_up_{item.get('line_code', '')}", '')
                if isinstance(user_answer, list):
                    user_answer = user_answer[0] if user_answer else ''
                user_answer = str(user_answer or '').strip()
                for choice in choices:
                    merge_tags[choice.strip()] = user_answer
                if len(configs) == 1:
                    merge_tags['__selected__'] = user_answer

    if page_blocks:
        for block in page_blocks:
            if block.get('block_type') != 'dropdown_select':
                continue
            field_name = block.get('standard', {}).get('name') or block.get('id')
            if not field_name:
                continue
            user_answer = answers.get(field_name, '')
            if isinstance(user_answer, list):
                user_answer = user_answer[0] if user_answer else ''
            user_answer = str(user_answer or '').strip()
            choices = block.get('standard', {}).get('dropdown_choices', []) or []
            for choice in choices:
                choice_value = choice.get('value', '') if isinstance(choice, dict) else str(choice)
                merge_tags[choice_value.strip()] = user_answer
            merge_tags['__selected__'] = user_answer

    return merge_tags


def replace_merge_tags(text, merge_tags):
    """Replace {choice_value} patterns in text with user answers."""
    if not text or not merge_tags:
        return text or ''
    result = text
    for tag, value in merge_tags.items():
        result = result.replace('{' + tag + '}', value)
    return result
