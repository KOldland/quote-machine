"""Merge tag utilities for output substitution."""
import json


def get_merge_tag_values(page_id, session, get_line_items_for_page, page_blocks=None):
    """Build a dict of merge tag values from session form data.
    
    Maps:
      {selected} -> chosen dropdown answer
      {one}, {two}, {three} -> 1st, 2nd, 3rd single entry answers
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
    single_entry_count = 0
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
                cfg_type = cfg.get('type', '')
                field_name = f"follow_up_{item.get('line_code', '')}_{idx}"
                if cfg_type and cfg_type.startswith('Dropdown'):
                    user_answer = answers.get(field_name, '')
                    if not user_answer:
                        user_answer = answers.get(f"follow_up_{item.get('line_code', '')}", '')
                    if isinstance(user_answer, list):
                        user_answer = user_answer[0] if user_answer else ''
                    user_answer = str(user_answer or '').strip()
                    if user_answer:
                        merge_tags['selected'] = user_answer
                elif cfg_type and cfg_type.startswith('Single Entry'):
                    user_answer = answers.get(field_name, '')
                    if isinstance(user_answer, list):
                        user_answer = user_answer[0] if user_answer else ''
                    user_answer = str(user_answer or '').strip()
                    tag = ['one', 'two', 'three'][single_entry_count] if single_entry_count < 3 else str(single_entry_count + 1)
                    merge_tags[tag] = user_answer
                    single_entry_count += 1

    return merge_tags


def replace_merge_tags(text, merge_tags):
    """Replace {choice_value} patterns in text with user answers."""
    if not text or not merge_tags:
        return text or ''
    lowered_map = {str(k).lower(): v for k, v in merge_tags.items()}
    import re
    def repl(m):
        key = m.group(1).lower()
        if key in lowered_map:
            return lowered_map[key]
        return m.group(0)
    return re.sub(r'\{([^{}]+)\}', repl, text)
