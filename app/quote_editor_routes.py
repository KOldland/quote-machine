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
from pathlib import Path
from typing import Optional
from flask import Blueprint, request, session, jsonify, abort, send_file
from werkzeug.utils import secure_filename
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
    load_template_payload,
    _get_form_template_id,
)

quote_editor_bp = Blueprint('quote_editor', __name__)

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
    is_default = data.get('is_default', True)
    layout = create_quote_editor_layout(form_key, name=name, blocks_json=blocks, is_default=is_default)
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
    return jsonify({'success': True, 'quote': quote})


@quote_editor_bp.route('/quote_editor/quotes', methods=['GET'])
def list_quotes():
    form_key = session.get('template_key', 'builder_beta')
    user_id = session.get('user_id')
    quotes = list_saved_quotes(form_key, user_id=user_id)
    return jsonify({'success': True, 'quotes': quotes})


@quote_editor_bp.route('/quote_editor/quotes/<int:quote_id>', methods=['DELETE'])
def delete_quote_route(quote_id):
    form_key = session.get('template_key', 'builder_beta')
    ok = delete_saved_quote(quote_id, form_key)
    if not ok:
        return jsonify({'success': False, 'error': 'Quote not found'}), 404
    return jsonify({'success': True})


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
    session.setdefault('quote_editor_images', [])
    session['quote_editor_images'].append({
        'url': url,
        'filename': unique_name,
        'original_name': filename,
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
        'width': width,
        'height': height,
    })


@quote_editor_bp.route('/quote_editor/images', methods=['GET'])
def list_images():
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
    return jsonify({'success': True, 'images': all_images})


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
    snapshot_blocks = []
    for b in blocks:
        storage = b.get('storage', {})
        key = storage.get('key', str(b.get('id', '')))
        value = form_data.get(key, '')
        snapshot_blocks.append({
            'id': f"form__{page_key}__{b.get('id', key)}",
            'type': 'form',
            'source_page': page_key,
            'source_block_id': str(b.get('id', key)),
            'snapshot': {
                'label': b.get('label', ''),
                'value': value,
                'captured_at': None,
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
            },
        })
    return jsonify({'success': True, 'blocks': snapshot_blocks})


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
        },
    }
    return jsonify({'success': True, 'block': block})
