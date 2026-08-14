"""Merge tag utilities for output substitution."""
import json


def get_merge_tag_values(page_id, session, get_line_items_for_page):
    """Build a dict of merge tag values from session form data.
    
    Scans follow-up questions for the page and maps choice values
    to the user's submitted answers.
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
            cfg = {}
            if item.get('is_follow_up') and item.get('follow_up_config'):
                try:
                    cfg = json.loads(item['follow_up_config'])
                except Exception:
                    continue
            choices = cfg.get('choices', [])
            if not choices:
                continue
            field_name = f"follow_up_{item.get('line_code', '')}"
            user_answer = answers.get(field_name, '')
            if isinstance(user_answer, list):
                user_answer = user_answer[0] if user_answer else ''
            user_answer = str(user_answer or '').strip()
            for choice in choices:
                merge_tags[choice.strip()] = user_answer

    return merge_tags


def replace_merge_tags(text, merge_tags):
    """Replace {choice_value} patterns in text with user answers."""
    if not text or not merge_tags:
        return text or ''
    result = text
    for tag, value in merge_tags.items():
        result = result.replace('{' + tag + '}', value)
    return result
