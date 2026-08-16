"""
Quote Editor Routes

Handles:
- Layout CRUD (quote_editor_layouts)
- Saved quotes CRUD
- Image upload for editor
- Source block data lookup
- Add-to-quote integration endpoints
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Optional
from flask import Blueprint, request, session, jsonify, abort, send_file, current_app
from werkzeug.utils import secure_filename
from merge_tags import get_merge_tag_values, replace_merge_tags
from template_store import (
    get_quote_editor_layout,
    list_quote_editor_layouts,
    create_quote_editor_layout,
    update_quote_editor_layout,
    delete_quote_editor_layout,
    duplicate_quote_editor_layout,
    save_quote,
    get_saved_quote,
    list_saved_quotes,
    delete_saved_quote,
    update_saved_quote,
    load_template_payload,
    _get_form_template_id,
    get_line_items_by_codes,
    get_line_items_for_page,
)

quote_editor_bp = Blueprint('quote_editor', __name__)


def _get_category_image(page_key, category_name):
    """Return the category_image URL stored on the category_templates row."""
    try:
        import sqlite3 as _sql
        conn = _sql.connect(str(DB_PATH))
        conn.row_factory = _sql.Row
        row = conn.execute(
            '''
            SELECT ct.image_url
            FROM category_templates ct
            JOIN page_templates pt ON pt.id = ct.page_template_id
            WHERE pt.page_key = ? AND ct.name = ?
            ''',
            (page_key, category_name),
        ).fetchone()
        conn.close()
        if row and row['image_url']:
            return row['image_url'] or ''
    except Exception:
        pass
    return ''


DB_PATH = Path(__file__).parent / "template_store.sqlite3"
UPLOAD_DIR = Path(__file__).parent / "static" / "uploads" / "quote_editor"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ── Layout CRUD ─────────────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/layouts', methods=['GET'])
def list_layouts():
    form_key = session.get('template_key', 'builder_beta')
    layouts = list_quote_editor_layouts(form_key)
    return jsonify({'success': True, 'layouts': layouts})


@quote_editor_bp.route('/quote_editor/layouts', methods=['POST'])
def create_layout():
    form_key = session.get('template_key', 'builder_beta')
    data = request.get_json(force=True) or {}
    name = data.get('name', 'Default')
    blocks = data.get('blocks_json', [])
    settings = data.get('settings_json') or {'document_styles': data.get('document_styles', {})}
    is_default = data.get('is_default', True)
    layout = create_quote_editor_layout(form_key, name=name, blocks_json=blocks, is_default=is_default, settings=settings)
    if not layout:
        return jsonify({'success': False, 'error': 'Form template not found'}), 404
    return jsonify({'success': True, 'layout': layout}), 201


@quote_editor_bp.route('/quote_editor/layouts/<int:layout_id>', methods=['PUT'])
def update_layout(layout_id):
    form_key = session.get('template_key', 'builder_beta')
    data = request.get_json(force=True) or {}
    blocks = data.get('blocks_json')
    settings = data.get('settings_json')
    name = data.get('name')
    ok = update_quote_editor_layout(
        layout_id,
        form_key,
        blocks_json=blocks,
        settings=settings,
        name=name,
    )
    if not ok:
        return jsonify({'success': False, 'error': 'Layout not found or no changes'}), 404
    return jsonify({'success': True})


@quote_editor_bp.route('/quote_editor/layouts/<int:layout_id>/set-default', methods=['POST'])
def set_layout_default(layout_id):
    form_key = session.get('template_key', 'builder_beta')
    ok = set_quote_editor_layout_default(layout_id, form_key)
    if not ok:
        return jsonify({'success': False, 'error': 'Layout not found'}), 404
    return jsonify({'success': True})


@quote_editor_bp.route('/quote_editor/layouts/<int:layout_id>', methods=['DELETE'])
def delete_layout(layout_id):
    form_key = session.get('template_key', 'builder_beta')
    ok = delete_quote_editor_layout(layout_id, form_key)
    if not ok:
        return jsonify({'success': False, 'error': 'Layout not found'}), 404
    return jsonify({'success': True})


@quote_editor_bp.route('/quote_editor/layouts/<int:layout_id>/duplicate', methods=['POST'])
def duplicate_layout(layout_id):
    form_key = session.get('template_key', 'builder_beta')
    data = request.get_json(force=True) or {}
    new_name = data.get('name', 'Copy of Layout')
    layout = duplicate_quote_editor_layout(layout_id, form_key, new_name)
    if not layout:
        return jsonify({'success': False, 'error': 'Layout not found'}), 404
    return jsonify({'success': True, 'layout': layout}), 201


# ── Saved Quotes ────────────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/save-quote', methods=['POST'])
def save_quote_route():
    form_key = session.get('template_key', 'builder_beta')
    data = request.get_json(force=True) or {}
    name = data.get('name', 'Untitled Quote')
    client_name = data.get('client_name', '')
    notes = data.get('notes', '')
    blocks = data.get('blocks_json', [])
    settings = data.get('settings_json', {})
    layout_id = data.get('layout_id')
    user_id = session.get('user_id')
    quote = save_quote(
        form_key,
        blocks_json=blocks,
        name=name,
        client_name=client_name,
        notes=notes,
        layout_id=layout_id,
        user_id=user_id,
        settings=settings,
    )
    if not quote:
        return jsonify({'success': False, 'error': 'Form template not found'}), 404
    return jsonify({'success': True, 'quote': quote}), 201


@quote_editor_bp.route('/quote_editor/load-quote/<int:quote_id>', methods=['GET'])
def load_quote_route(quote_id):
    form_key = session.get('template_key', 'builder_beta')
    quote = get_saved_quote(quote_id, form_key)
    if not quote:
        return jsonify({'success': False, 'error': 'Quote not found'}), 404
    session['active_quote_id'] = quote_id
    session.modified = True
    return jsonify({'success': True, 'quote': quote})


@quote_editor_bp.route('/quote_editor/quotes', methods=['GET'])
def list_quotes():
    form_key = session.get('template_key', 'builder_beta')
    user_id = session.get('user_id')
    quotes = list_saved_quotes(form_key, user_id=user_id)
    return jsonify({'success': True, 'quotes': quotes})


@quote_editor_bp.route('/quote_editor/quotes', methods=['POST'])
def create_quote():
    form_key = session.get('template_key', 'builder_beta')
    user_id = session.get('user_id')
    data = request.get_json(force=True) or {}
    name = data.get('name', 'Untitled')
    blocks = data.get('blocks_json', [])
    settings = data.get('settings_json') or {}
    quote = save_quote(
        form_key=form_key,
        blocks_json=blocks,
        name=name,
        settings=settings,
        user_id=user_id,
    )
    if not quote:
        return jsonify({'success': False, 'error': 'Failed to save quote'}), 500
    return jsonify({'success': True, 'quote': quote}), 201


@quote_editor_bp.route('/quote_editor/quotes/<int:quote_id>', methods=['DELETE'])
def delete_quote_route(quote_id):
    form_key = session.get('template_key', 'builder_beta')
    ok = delete_saved_quote(quote_id, form_key)
    if not ok:
        return jsonify({'success': False, 'error': 'Quote not found'}), 404
    return jsonify({'success': True})


@quote_editor_bp.route('/quote_editor/quotes/<int:quote_id>', methods=['PUT'])
def update_quote_route(quote_id):
    form_key = session.get('template_key', 'builder_beta')
    data = request.get_json(force=True) or {}
    name = data.get('name')
    blocks = data.get('blocks_json')
    settings = data.get('settings_json')
    client_name = data.get('client_name', '')
    notes = data.get('notes', '')
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    updated = update_saved_quote(
        quote_id=quote_id,
        form_key=form_key,
        name=name,
        blocks_json=blocks or [],
        settings=settings or {},
        client_name=client_name,
        notes=notes,
    )
    if not updated:
        return jsonify({'success': False, 'error': 'Quote not found'}), 404
    return jsonify({'success': True, 'quote': updated})


# ── Image Upload ────────────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400
    filename = secure_filename(file.filename)
    import uuid
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    dest = UPLOAD_DIR / unique_name
    file.save(str(dest))
    url = f"/static/uploads/quote_editor/{unique_name}"
    raw_tags = request.form.get('tags', '')
    tags = [t.strip().lower() for t in raw_tags.split(',') if t.strip()]
    category = (request.form.get('category') or '').strip()
    session.setdefault('quote_editor_images', [])
    session['quote_editor_images'].append({
        'url': url,
        'filename': unique_name,
        'original_name': filename,
        'tags': tags,
        'category': category,
    })
    session.modified = True
    try:
        from PIL import Image as PILImage
        with PILImage.open(dest) as img:
            width, height = img.size
    except Exception:
        width, height = None, None
    return jsonify({
        'success': True,
        'url': url,
        'filename': unique_name,
        'original_name': filename,
        'tags': tags,
        'category': category,
        'width': width,
        'height': height,
    })


@quote_editor_bp.route('/quote_editor/images', methods=['GET'])
def list_images():
    tag_filter = (request.args.get('tag') or '').strip().lower()
    category_filter = (request.args.get('category') or '').strip().lower()
    q_filter = (request.args.get('q') or '').strip().lower()
    editor_images = session.get('quote_editor_images', [])
    files = []
    if UPLOAD_DIR.exists():
        for f in sorted(UPLOAD_DIR.iterdir()):
            if f.is_file():
                files.append({
                    'url': f"/static/uploads/quote_editor/{f.name}",
                    'filename': f.name,
                })
    all_images = editor_images + [f for f in files if f['filename'] not in {i['filename'] for i in editor_images}]

    # Ensure all entries have tags/category keys
    for img in all_images:
        img.setdefault('tags', [])
        img.setdefault('category', '')

    if tag_filter:
        all_images = [i for i in all_images if tag_filter in i['tags']]
    if category_filter:
        all_images = [i for i in all_images if i['category'].lower() == category_filter]
    if q_filter:
        all_images = [
            i for i in all_images
            if q_filter in (i.get('original_name') or '').lower()
            or q_filter in (i.get('category') or '').lower()
            or any(q_filter in t for t in i.get('tags', []))
        ]

    # Collect available tags + categories for filter UI
    all_tags = sorted({t for i in all_images for t in i.get('tags', [])})
    all_categories = sorted({i.get('category') for i in all_images if i.get('category')})

    return jsonify({
        'success': True,
        'images': all_images,
        'tags': all_tags,
        'categories': all_categories,
    })


# ── Source Block Data ───────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/source/<page_key>/<block_id>', methods=['GET'])
def get_source_block(page_key, block_id):
    form_key = session.get('template_key', 'builder_beta')
    payload = load_template_payload(form_key)
    if not payload:
        return jsonify({'success': False, 'error': 'Template payload not found'}), 404
    pages = payload.get('builder_beta', {}).get('pages', payload.get('pages', {}))
    page = pages.get(page_key, {})
    blocks = page.get('blocks', page.get('fields', []))
    target = None
    for b in blocks:
        if str(b.get('id', '')) == str(block_id):
            target = b
            break
    if not target:
        return jsonify({'success': False, 'error': 'Block not found'}), 404
    form_data = session.get('data', {})
    storage = target.get('storage', {})
    key = storage.get('key', block_id)
    value = form_data.get(key, '')
    return jsonify({
        'success': True,
        'block': {
            'id': block_id,
            'label': target.get('label', ''),
            'type': target.get('type', ''),
            'value': value,
            'raw': target,
        }
    })


# ── Add-to-Quote Integration ────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/add-form-block', methods=['GET'])
def add_form_block():
    page_key = request.args.get('page')
    if not page_key:
        return jsonify({'success': False, 'error': 'Missing page parameter'}), 400
    form_key = session.get('template_key', 'builder_beta')
    payload = load_template_payload(form_key)
    if not payload:
        return jsonify({'success': False, 'error': 'Template payload not found'}), 404
    pages = payload.get('builder_beta', {}).get('pages', payload.get('pages', {}))
    page = pages.get(page_key, {})
    blocks = page.get('blocks', page.get('fields', []))
    form_data = session.get('data', {})
    checkbox_data = session.get('checkbox_data', {})
    snapshot_blocks = []
    seen_pages = set()
    seen_categories = set()
    for b in blocks:
        block_type = b.get('block_type', b.get('type', ''))
        storage = b.get('storage', {})
        key = storage.get('key', str(b.get('id', '')))
        raw_value = checkbox_data.get(key) or form_data.get(key) or ''
        if isinstance(raw_value, dict):
            raw_value = raw_value.get('preselected', [])
        if not raw_value:
            raw_value = ''

        if block_type == 'line_items_by_category' and isinstance(raw_value, list):
            selected_codes = [v for v in raw_value if isinstance(v, str) and v.strip()]
            if not selected_codes:
                continue
            items = get_line_items_by_codes(selected_codes)
            if not items:
                continue

            merge_tags = get_merge_tag_values(page_key, session, get_line_items_for_page, page_blocks=page.get('blocks', []))

            page_title = page.get('title') or page_key.replace('_', ' ').title()
            if page_title not in seen_pages:
                seen_pages.add(page_title)
                snapshot_blocks.append({
                    'id': f"form__{page_key}__page_title",
                    'type': 'page_title',
                    'source_page': page_key,
                    'source_block_id': '__page_title__',
                    'snapshot': {'title': page_title},
                    'editor_overrides': {},
                    'flags': { 'source_dirty': False, 'editor_dirty': False },
                    'settings': { 'margin_top': 10, 'margin_bottom': 10, 'padding': 12, 'alignment': 'left' },
                })

            page_categories = {c['name']: c.get('sort_order', 0) for c in page.get('categories', [])}
            items.sort(key=lambda x: (
                page_categories.get(x.get('category', ''), 999),
                x.get('sort_order', 0),
                x.get('line_code', '')
            ))

            current_category = None
            for item in items:
                category = item.get('category', '')
                if category and category != current_category:
                    current_category = category
                    if category not in seen_categories:
                        seen_categories.add(category)
                        category_image = _get_category_image(page_key, category)
                        snapshot_blocks.append({
                            'id': f"form__{page_key}__category__{category}",
                            'type': 'category_title',
                            'source_page': page_key,
                            'source_block_id': '__category_title__',
                            'snapshot': {'title': category, 'category_image': category_image},
                            'editor_overrides': {},
                            'flags': { 'source_dirty': False, 'editor_dirty': False },
                            'settings': { 'margin_top': 5, 'margin_bottom': 5, 'padding': 12, 'alignment': 'left', 'font_size': 20 },
                        })

                output_title = item.get('output_title', '') or item.get('line_code', '')
                output_notes = replace_merge_tags(item.get('output_notes', ''), merge_tags)
                output_guidance = replace_merge_tags(item.get('output_guidance', ''), merge_tags)
                value_text = output_notes or ''

                snapshot_blocks.append({
                    'id': f"form__{page_key}__{key}__{item.get('line_code', '')}",
                    'type': 'form_question',
                    'source_page': page_key,
                    'source_block_id': str(key),
                    'snapshot': {
                        'label': output_title,
                        'value': value_text,
                        'output_notes': output_notes,
                        'output_guidance': output_guidance,
                        'line_code': item.get('line_code', ''),
                        'category': category,
                    },
                    'editor_overrides': {},
                    'flags': { 'source_dirty': False, 'editor_dirty': False },
                    'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left' },
                })
            continue

        if block_type in ('checkbox_group', 'text_input', 'number_currency_input', 'dropdown_select'):
            page_title = page.get('title') or page_key.replace('_', ' ').title()
            if page_title not in seen_pages:
                seen_pages.add(page_title)
                snapshot_blocks.append({
                    'id': f"form__{page_key}__page_title",
                    'type': 'page_title',
                    'source_page': page_key,
                    'source_block_id': '__page_title__',
                    'snapshot': {'title': page_title},
                    'editor_overrides': {},
                    'flags': { 'source_dirty': False, 'editor_dirty': False },
                    'settings': { 'margin_top': 10, 'margin_bottom': 10, 'padding': 12, 'alignment': 'left', 'font_size': 24 },
                })

            snapshot_blocks.append({
                'id': f"form__{page_key}__{b.get('id', key)}",
                'type': 'form_question',
                'source_page': page_key,
                'source_block_id': str(b.get('id', key)),
                'snapshot': {
                    'label': b.get('standard', {}).get('label', b.get('label', key)),
                    'value': raw_value if isinstance(raw_value, str) else ', '.join(raw_value),
                },
                'editor_overrides': {},
                'flags': { 'source_dirty': False, 'editor_dirty': False },
                'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left', 'font_size': 16 },
            })
    
    if snapshot_blocks:
        session['quote_editor_pending_blocks'] = snapshot_blocks
        session.modified = True
    
    return jsonify({'success': True, 'blocks': snapshot_blocks, 'redirect': '/quote_editor'})


@quote_editor_bp.route('/quote_editor/add-calc-block', methods=['GET'])
def add_calc_block():
    form_key = session.get('template_key', 'builder_beta')
    form_data = session.get('data', {})
    session_overrides = session.get('session_overrides', {})
    try:
        import calculator
        calc_result = calculator.calculate_quote(form_key, form_data, session_overrides)
    except Exception:
        calc_result = {}
    block = {
        'id': f"calculator__{int(__import__('time').time())}",
        'type': 'calculator',
        'snapshot': calc_result,
        'editor_overrides': {},
        'flags': {
            'source_dirty': False,
            'editor_dirty': False,
        },
        'settings': {
            'margin_top': 8,
            'margin_bottom': 8,
            'padding': 12,
            'alignment': 'left',
            'font_size': 14,
        },
    }
    return jsonify({'success': True, 'block': block})


@quote_editor_bp.route('/quote_editor/add-image-group-block', methods=['GET'])
def add_image_group_block():
    images = session.get('uploaded_images', [])
    editor_images = session.get('quote_editor_images', [])
    all_images = editor_images + [img for img in images if img not in editor_images]
    block = {
        'id': f"image_group__{int(__import__('time').time())}",
        'type': 'image_group',
        'snapshot': {
            'images': all_images,
            'columns': 2,
        },
        'editor_overrides': {},
        'flags': {
            'source_dirty': False,
            'editor_dirty': False,
        },
        'settings': {
            'margin_top': 8,
            'margin_bottom': 8,
            'padding': 12,
            'alignment': 'left',
            'font_size': 14,
        },
    }
    return jsonify({'success': True, 'block': block})


@quote_editor_bp.route('/quote_editor/set-pending-block', methods=['POST'])
def set_pending_block():
    data = request.get_json(force=True) or {}
    block = data.get('block')
    if block:
        session['quote_editor_pending_block'] = block
        session.modified = True
    return jsonify({'success': True, 'redirect': '/quote_editor'})


@quote_editor_bp.route('/quote_editor/themes', methods=['GET'])
def list_themes():
    theme_dir = os.path.join(current_app.root_path, 'themes')
    themes = []
    if os.path.isdir(theme_dir):
        for fn in os.listdir(theme_dir):
            if fn.endswith('.json'):
                path = os.path.join(theme_dir, fn)
                try:
                    with open(path, 'r') as f:
                        themes.append(json.load(f))
                except Exception:
                    pass
    return jsonify({'success': True, 'themes': themes})


@quote_editor_bp.route('/quote_editor/themes/<path:theme_name>', methods=['GET'])
def get_theme(theme_name):
    theme_dir = os.path.join(current_app.root_path, 'themes')
    filename = f"{theme_name.replace(' ', '_').lower()}.json"
    path = os.path.join(theme_dir, filename)
    if not os.path.isfile(path):
        return jsonify({'success': False, 'error': 'Theme not found'}), 404
    try:
        with open(path, 'r') as f:
            theme = json.load(f)
        return jsonify({'success': True, 'theme': theme})
    except Exception:
        return jsonify({'success': False, 'error': 'Failed to load theme'}), 500


@quote_editor_bp.route('/quote_editor/themes', methods=['POST'])
def create_theme():
    data = request.get_json(force=True) or {}
    name = data.get('name', 'Default')
    settings = data.get('settings_json') or {}
    is_default = data.get('is_default', False)
    theme_dir = os.path.join(current_app.root_path, 'themes')
    os.makedirs(theme_dir, exist_ok=True)
    theme_data = {
        'name': name,
        'settings': settings,
        'is_default': is_default,
        'created_at': __import__('datetime').datetime.utcnow().isoformat(),
    }
    filename = f"{name.replace(' ', '_').lower()}.json"
    with open(os.path.join(theme_dir, filename), 'w') as f:
        json.dump(theme_data, f, indent=2)
    return jsonify({'success': True})


def _build_page_blocks(page_key, page, form_data, checkbox_data):
    """Generate quote-editor blocks for a single form page."""
    blocks = page.get('blocks', page.get('fields', []))
    snapshot_blocks = []
    seen_pages = set()
    seen_categories = set()

    page_title = page.get('title') or page_key.replace('_', ' ').title()
    if page_title not in seen_pages:
        seen_pages.add(page_title)
        snapshot_blocks.append({
            'id': f"form__{page_key}__page_title",
            'type': 'page_title',
            'source_page': page_key,
            'source_block_id': '__page_title__',
            'snapshot': {'title': page_title},
            'editor_overrides': {},
            'flags': { 'source_dirty': False, 'editor_dirty': False, 'hidden': False },
            'settings': { 'margin_top': 0, 'margin_bottom': 0, 'padding': 0, 'alignment': 'left' },
        })
        snapshot_blocks.append({
            'id': f"form__{page_key}__page_heading",
            'type': 'page_heading',
            'source_page': page_key,
            'source_block_id': '__page_heading__',
            'snapshot': {'title': page_title},
            'editor_overrides': {},
            'flags': { 'source_dirty': False, 'editor_dirty': False },
            'settings': { 'margin_top': 10, 'margin_bottom': 10, 'padding': 12, 'alignment': 'left', 'font_size': 24 },
        })

    for b in blocks:
        block_type = b.get('block_type', b.get('type', ''))
        storage = b.get('storage', {})
        key = storage.get('key', str(b.get('id', '')))
        raw_value = checkbox_data.get(key) or form_data.get(key) or ''
        if isinstance(raw_value, dict):
            raw_value = raw_value.get('preselected', [])
        if not raw_value:
            raw_value = ''

        if block_type == 'line_items_by_category' and isinstance(raw_value, list):
            selected_codes = [v for v in raw_value if isinstance(v, str) and v.strip()]
            if not selected_codes:
                continue
            items = get_line_items_by_codes(selected_codes)
            if not items:
                continue

            merge_tags = get_merge_tag_values(page_key, session, get_line_items_for_page, page_blocks=page.get('blocks', []))
            page_categories = {c['name']: c.get('sort_order', 0) for c in page.get('categories', [])}
            items.sort(key=lambda x: (
                page_categories.get(x.get('category', ''), 999),
                x.get('sort_order', 0),
                x.get('line_code', '')
            ))

            current_category = None
            for item in items:
                category = item.get('category', '')
                if category and category != current_category:
                    current_category = category
                    if category not in seen_categories:
                        seen_categories.add(category)
                        category_image = _get_category_image(page_key, category)
                        snapshot_blocks.append({
                            'id': f"form__{page_key}__category__{category}",
                            'type': 'category_title',
                            'source_page': page_key,
                            'source_block_id': '__category_title__',
                            'snapshot': {'title': category, 'category_image': category_image},
                            'editor_overrides': {},
                            'flags': { 'source_dirty': False, 'editor_dirty': False },
                            'settings': { 'margin_top': 5, 'margin_bottom': 5, 'padding': 12, 'alignment': 'left', 'font_size': 20 },
                        })

                output_title = item.get('output_title', '') or item.get('line_code', '')
                output_notes = replace_merge_tags(item.get('output_notes', ''), merge_tags)
                output_guidance = replace_merge_tags(item.get('output_guidance', ''), merge_tags)
                value_text = output_notes or ''

                snapshot_blocks.append({
                    'id': f"form__{page_key}__{key}__{item.get('line_code', '')}",
                    'type': 'form_question',
                    'source_page': page_key,
                    'source_block_id': str(key),
                    'snapshot': {
                        'label': output_title,
                        'value': value_text,
                        'output_notes': output_notes,
                        'output_guidance': output_guidance,
                        'line_code': item.get('line_code', ''),
                        'category': category,
                    },
                    'editor_overrides': {},
                    'flags': { 'source_dirty': False, 'editor_dirty': False },
                    'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left' },
                })
            continue

        if block_type in ('checkbox_group', 'text_input', 'number_currency_input', 'dropdown_select'):
            snapshot_blocks.append({
                'id': f"form__{page_key}__{b.get('id', key)}",
                'type': 'form_question',
                'source_page': page_key,
                'source_block_id': str(b.get('id', key)),
                'snapshot': {
                    'label': b.get('standard', {}).get('label', b.get('label', key)),
                    'value': raw_value if isinstance(raw_value, str) else ', '.join(raw_value),
                },
                'editor_overrides': {},
                'flags': { 'source_dirty': False, 'editor_dirty': False },
                'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left', 'font_size': 16 },
            })

    return snapshot_blocks


def build_quote_editor_blocks_for_all_pages():
    """Build blocks for every page in the current form template."""
    form_key = session.get('template_key', 'builder_beta')
    payload = load_template_payload(form_key)
    if not payload:
        return []
    pages = payload.get('builder_beta', {}).get('pages', payload.get('pages', {}))
    if not pages:
        return []

    form_data = session.get('data', {})
    checkbox_data = session.get('checkbox_data', {})
    all_blocks = []
    for page_key, page in pages.items():
        page_blocks = _build_page_blocks(page_key, page, form_data, checkbox_data)
        all_blocks.extend(page_blocks)
    return all_blocks


def get_quote_editor_blocks():
    """Return the full set of blocks for the quote editor.

    This always includes every page from the form template, plus any
    manually-added blocks the user has created in the quote editor itself
    (calculator, image groups, etc.).
    """
    form_blocks = build_quote_editor_blocks_for_all_pages()
    manual_blocks = [
        b for b in session.get('quote_editor_pending_blocks', [])
        if b.get('type') not in ('page_title', 'category_title', 'form_question')
    ]
    return form_blocks + manual_blocks


# ── Active Quote Tracking ────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/active-quote', methods=['POST'])
def set_active_quote():
    data = request.get_json(force=True) or {}
    quote_id = data.get('quote_id')
    if quote_id:
        session['active_quote_id'] = int(quote_id)
        session.modified = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'quote_id required'}), 400


@quote_editor_bp.route('/quote_editor/active-quote', methods=['GET'])
def get_active_quote():
    quote_id = session.get('active_quote_id')
    if quote_id:
        return jsonify({'success': True, 'quote_id': quote_id})
    return jsonify({'success': False, 'error': 'No active quote'}), 404


# ── Form Drafts ──────────────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/drafts', methods=['GET'])
def list_drafts():
    user_id = session.get('user_id')
    db_path = DB_PATH
    rows = []
    if db_path.exists():
        try:
            conn = db_path.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            sql = 'SELECT id, name, created_at FROM form_drafts WHERE user_id = ? ORDER BY created_at DESC'
            if user_id is None:
                sql = 'SELECT id, name, created_at FROM form_drafts WHERE user_id IS NULL ORDER BY created_at DESC'
            rows = conn.execute(sql, (user_id,)).fetchall()
            conn.close()
        except Exception:
            pass
    drafts = [{'id': r['id'], 'name': r['name'], 'created_at': r['created_at']} for r in rows]
    return jsonify({'success': True, 'drafts': drafts})


@quote_editor_bp.route('/quote_editor/drafts', methods=['POST'])
def save_draft():
    name = (request.get_json(force=True) or {}).get('name', '').strip() or f"Draft {int(__import__('time').time())}"
    data_to_save = {
        'data': session.get('data', {}),
        'checkbox_data': session.get('checkbox_data', {}),
        'session_overrides': session.get('session_overrides', {}),
        'template_key': session.get('template_key'),
    }
    db_path = DB_PATH
    if not db_path.exists():
        return jsonify({'success': False, 'error': 'Database not found'}), 500
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute('''
            CREATE TABLE IF NOT EXISTS form_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                draft_data TEXT NOT NULL,
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute(
            'INSERT INTO form_drafts (name, draft_data, user_id) VALUES (?, ?, ?)',
            (name, json.dumps(data_to_save), session.get('user_id'))
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@quote_editor_bp.route('/quote_editor/drafts/<int:draft_id>/load', methods=['POST'])
def load_draft(draft_id):
    db_path = DB_PATH
    if not db_path.exists():
        return jsonify({'success': False, 'error': 'Database not found'}), 500
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute('SELECT id, draft_data FROM form_drafts WHERE id = ?', (draft_id,)).fetchone()
        conn.close()
        if row:
            loaded = json.loads(row['draft_data'])
            session['data'] = loaded.get('data', {})
            session['checkbox_data'] = loaded.get('checkbox_data', {})
            session['session_overrides'] = loaded.get('session_overrides', {})
            if loaded.get('template_key'):
                session['template_key'] = loaded['template_key']
            session.modified = True
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Draft not found'}), 404
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@quote_editor_bp.route('/quote_editor/drafts/<int:draft_id>', methods=['DELETE'])
def delete_draft(draft_id):
    db_path = DB_PATH
    if not db_path.exists():
        return jsonify({'success': False, 'error': 'Database not found'}), 500
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute('DELETE FROM form_drafts WHERE id = ?', (draft_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


# ── Form → Quote Live Sync ───────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/sync-form-to-quote', methods=['POST'])
def sync_form_to_quote():
    data = request.get_json(force=True) or {}
    quote_id = data.get('quote_id') or session.get('active_quote_id')
    if not quote_id:
        return jsonify({'success': False, 'error': 'No active quote'}), 400

    form_data = data.get('form_data', {})
    checkbox_data = data.get('checkbox_data', {})
    form_key = session.get('template_key', 'builder_beta')

    quote = get_saved_quote(int(quote_id), form_key)
    if not quote:
        return jsonify({'success': False, 'error': 'Quote not found'}), 404

    blocks = quote.get('blocks_json', [])
    updated = 0

    for block in blocks:
        if not block.get('source_page') or not block.get('source_block_id'):
            continue
        if block.get('flags', {}).get('editor_dirty'):
            continue

        source_page = block['source_page']
        source_block_id = block['source_block_id']
        block_type = block.get('type')

        if block_type == 'page_title':
            title = form_data.get('client_address') or block.get('snapshot', {}).get('title', '')
            if title:
                block['snapshot'] = block.get('snapshot', {})
                block['snapshot']['title'] = title
                block['flags'] = block.get('flags', {})
                block['flags']['source_dirty'] = True
                updated += 1

        elif block_type == 'page_heading':
            title = form_data.get('client_address') or block.get('snapshot', {}).get('title', '')
            if title:
                block['snapshot'] = block.get('snapshot', {})
                block['snapshot']['title'] = title
                block['flags'] = block.get('flags', {})
                block['flags']['source_dirty'] = True
                updated += 1

        elif block_type == 'category_title':
            continue

        elif block_type == 'form_question':
            value = ''
            cb = checkbox_data.get(source_block_id)
            if isinstance(cb, dict):
                value = cb.get('preselected', [])
            elif cb:
                value = cb
            else:
                value = form_data.get(source_block_id, '')

            block['snapshot'] = block.get('snapshot', {})
            block['snapshot']['value'] = value if isinstance(value, str) else ', '.join(value)
            block['flags'] = block.get('flags', {})
            block['flags']['source_dirty'] = True
            updated += 1

    if updated > 0:
        update_saved_quote(
            quote_id=int(quote_id),
            form_key=form_key,
            name=quote.get('name', 'Quote'),
            blocks_json=blocks,
            settings=quote.get('settings_json', {}),
        )

    return jsonify({'success': True, 'updated': updated})
