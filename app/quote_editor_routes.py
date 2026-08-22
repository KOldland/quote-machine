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
    get_all_pages,
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


def _get_page_category_order(page_key):
    """Return dict of category_name -> display_order from category_templates."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            '''
            SELECT ct.name, ct.display_order
            FROM category_templates ct
            JOIN page_templates pt ON pt.id = ct.page_template_id
            WHERE pt.page_key = ?
            ORDER BY ct.display_order ASC
            ''',
            (page_key,),
        ).fetchall()
        conn.close()
        return {r['name']: r['display_order'] for r in rows}
    except Exception:
        return {}


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
    form_data = data.get('form_data') or {
        'data': session.get('data', {}),
        'checkbox_data': session.get('checkbox_data', {}),
        'template_key': form_key,
    }
    quote = save_quote(
        form_key,
        blocks_json=blocks,
        name=name,
        client_name=client_name,
        notes=notes,
        layout_id=layout_id,
        user_id=user_id,
        settings=settings,
        form_data=form_data,
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
    form_data = quote.get('form_data') or {}
    if 'data' not in session:
        session['data'] = form_data.get('data', {})
    if 'checkbox_data' not in session:
        session['checkbox_data'] = form_data.get('checkbox_data', {})
    if form_data.get('template_key') and 'template_key' not in session:
        session['template_key'] = form_data['template_key']
    session.pop('legacy_spreadsheet_data', None)
    session.pop('old_form_answers', None)
    session.modified = True
    fresh_blocks = get_quote_editor_blocks()
    fresh_blocks = _resort_blocks_by_db_category_order(fresh_blocks)
    quote = _resort_quote_blocks_json_by_db_category_order(quote)
    return jsonify({'success': True, 'quote': quote, 'fresh_blocks': fresh_blocks})


def _resort_quote_blocks_json_by_db_category_order(quote):
    """Re-sort a saved quote's stored blocks_json by DB category display_order.

    Used as a fallback when fresh_blocks cannot be regenerated (e.g. the saved
    quote has no form_data). Keeps the stored structure but fixes category order
    to match BUILD MODE.
    """
    if not isinstance(quote, dict):
        return quote
    raw = quote.get('blocks_json')
    if isinstance(raw, str):
        try:
            blocks = json.loads(raw)
        except (TypeError, ValueError):
            return quote
    elif isinstance(raw, list):
        blocks = raw
    else:
        return quote
    if not isinstance(blocks, list):
        return quote
    quote = dict(quote)
    quote['blocks_json'] = json.dumps(_resort_blocks_by_db_category_order(blocks))
    return quote


def _resort_blocks_by_db_category_order(blocks):
    """Re-order both pages and categories using DB display_order.

    Repairs stale saved-quote blocks_json that may have:
      - pages in the wrong order
      - categories in the wrong order within a page
      - blocks assigned to the wrong page group (e.g. after a category rename)

    Each block's source_page is validated against the DB: if a block's category
    does not exist on its assigned page, it is moved to the page that actually
    owns that category. Blocks without a known source_page (manual editor blocks
    like calculator/image_group) are appended at the end in their original order.
    """
    if not blocks:
        return blocks

    # Build category -> page_key mapping from DB (used to reassign misplaced blocks).
    # Also build a rename map for known stale category names that were changed
    # in BUILD MODE but still appear in old saved quotes.
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT pt.page_key, ct.name
            FROM category_templates ct
            JOIN page_templates pt ON pt.id = ct.page_template_id
            ORDER BY pt.display_order ASC, ct.display_order ASC
            """
        ).fetchall()
        cat_to_page = {r['name']: r['page_key'] for r in rows}
        conn.close()
    except Exception:
        cat_to_page = {}

    # Known stale -> current name mappings (from BUILD MODE renames).
    # These let us repair old blocks_json without dropping data.
    rename_map = {
        'Building Works': 'Work Summary',
    }

    # Build line_code -> output_title mapping from DB for ALL pages.
    # Used to repair stale blocks whose snapshot.label was saved as the raw
    # line_code (spreadsheet artifact) instead of the proper output_title.
    line_code_to_title = {}
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT line_code, output_title
            FROM line_items
            WHERE output_title IS NOT NULL AND TRIM(output_title) != ''
            """
        ).fetchall()
        for r in rows:
            line_code_to_title[r['line_code']] = r['output_title']
        conn.close()
    except Exception:
        pass

    # Separate form blocks (have source_page) from manual blocks (no source_page).
    form_blocks = []
    manual_blocks = []
    for b in blocks:
        if b.get('source_page'):
            form_blocks.append(b)
        else:
            manual_blocks.append(b)

    # Apply known renames to stale blocks before reassignment.
    renamed = 0
    for b in form_blocks:
        sp = b['source_page']
        cat = None
        if b.get('type') == 'category_title':
            cat = b.get('snapshot', {}).get('title')
        elif b.get('type') == 'form_question':
            cat = b.get('snapshot', {}).get('category')
        if cat and cat in rename_map:
            b = dict(b)
            if b.get('type') == 'category_title':
                b.setdefault('snapshot', {})['title'] = rename_map[cat]
            elif b.get('type') == 'form_question':
                b.setdefault('snapshot', {})['category'] = rename_map[cat]
            renamed += 1
    if renamed:
        print(f"[_resort_blocks] Renamed {renamed} stale category blocks: {rename_map}")

    # Repair stale snapshot.label values that were saved as raw line codes
    # (spreadsheet artifacts like "bw0^", "pp1@"). Replace with the proper
    # output_title from the DB when available; otherwise blank the label.
    relabel_count = 0
    for b in form_blocks:
        if b.get('type') != 'form_question':
            continue
        snapshot = b.get('snapshot') or {}
        label = (snapshot.get('label') or '').strip()
        line_code = (snapshot.get('line_code') or '').strip()
        if not label or not line_code:
            continue
        # If label equals line_code, it's a raw spreadsheet code — repair it.
        if label == line_code and line_code in line_code_to_title:
            b = dict(b)
            b.setdefault('snapshot', {})['label'] = line_code_to_title[line_code]
            relabel_count += 1
        elif label == line_code and line_code not in line_code_to_title:
            # No proper title in DB — blank it so the UI shows a placeholder
            # instead of exposing the raw spreadsheet code.
            b = dict(b)
            b.setdefault('snapshot', {})['label'] = ''
            relabel_count += 1
    if relabel_count:
        print(f"[_resort_blocks] Relabeled {relabel_count} stale line-code labels")

    # Reassign misplaced blocks: if a block's category does not belong to its
    # declared source_page in the DB, move it to the correct page.
    # Drop blocks whose category no longer exists anywhere in the DB and has
    # no known rename (truly orphaned data).
    reassigned = []
    dropped = 0
    for b in form_blocks:
        sp = b['source_page']
        cat = None
        if b.get('type') == 'category_title':
            cat = b.get('snapshot', {}).get('title')
        elif b.get('type') == 'form_question':
            cat = b.get('snapshot', {}).get('category')
        if cat:
            if cat not in cat_to_page:
                dropped += 1
                continue
            if cat_to_page[cat] != sp:
                b = dict(b)
                b['source_page'] = cat_to_page[cat]
        reassigned.append(b)

    # Group form blocks by (possibly corrected) source_page.
    page_buckets = {}
    page_order = []
    for b in reassigned:
        sp = b['source_page']
        if sp not in page_buckets:
            page_buckets[sp] = []
            page_order.append(sp)
        page_buckets[sp].append(b)

    # Sort pages by DB display_order.
    try:
        ordered_pages = get_all_pages(template_key=session.get('template_key', 'builder_beta'))
        page_db_order = {pg['page_key']: pg['display_order'] for pg in ordered_pages}
    except Exception:
        page_db_order = {}

    def _page_rank(sp):
        return page_db_order.get(sp, 999)

    sorted_pages = sorted(page_order, key=_page_rank)

    # Within each page, sort categories by DB display_order.
    ordered = []
    for sp in sorted_pages:
        group = page_buckets[sp]
        db_order = _get_page_category_order(sp)

        # Collect page_title/page_break blocks (keep first one as the page header).
        page_separators = [b for b in group if b.get('type') in ('page_title', 'page_break')]
        page_header = page_separators[0] if page_separators else None

        # Group remaining blocks by category.
        category_buckets = {}
        cat_order = []
        loose = []
        for b in group:
            if b.get('type') in ('page_title', 'page_break'):
                continue  # handled above
            cat = None
            if b.get('type') == 'category_title':
                cat = b.get('snapshot', {}).get('title')
            elif b.get('type') == 'form_question':
                cat = b.get('snapshot', {}).get('category')
            if cat:
                if cat not in category_buckets:
                    category_buckets[cat] = []
                    cat_order.append(cat)
                category_buckets[cat].append(b)
            else:
                loose.append(b)

        def _cat_rank(c):
            if c in db_order:
                return db_order[c]
            return 999

        sorted_cats = sorted(cat_order, key=_cat_rank)

        if page_header:
            ordered.append(page_header)
        for b in loose:
            ordered.append(b)
        for cat in sorted_cats:
            ordered.extend(category_buckets[cat])

    # Append manual blocks (calculator, image_group, etc.) at the end.
    ordered.extend(manual_blocks)

    # Filter out form_question blocks with empty labels — these are spreadsheet
    # artifacts with no proper output_title and should not appear in QUOTE MODE.
    filtered = []
    dropped = 0
    for b in ordered:
        if b.get('type') == 'form_question' and not (b.get('snapshot') or {}).get('label', '').strip():
            dropped += 1
            continue
        filtered.append(b)
    if dropped:
        print(f"[_resort_blocks] Dropped {dropped} form_question blocks with empty labels")

    return filtered


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
    form_data = data.get('form_data') or {
        'data': session.get('data', {}),
        'checkbox_data': session.get('checkbox_data', {}),
        'template_key': form_key,
    }
    quote = save_quote(
        form_key=form_key,
        blocks_json=blocks,
        name=name,
        settings=settings,
        user_id=user_id,
        form_data=form_data,
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
    form_data = data.get('form_data') or {
        'data': session.get('data', {}),
        'checkbox_data': session.get('checkbox_data', {}),
        'template_key': form_key,
    }
    updated = update_saved_quote(
        quote_id=quote_id,
        form_key=form_key,
        name=name,
        blocks_json=blocks or [],
        settings=settings or {},
        client_name=client_name,
        notes=notes,
        form_data=form_data,
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
    db_category_order = _get_page_category_order(page_key)
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
                    'category_sort_order': -1,
                })

            items.sort(key=lambda x: (
                db_category_order.get(x.get('category', ''), 999),
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
                            'category_sort_order': db_category_order.get(category, 999),
                        })

                output_title = item.get('output_title', '') or ''
                if not output_title.strip():
                    continue  # skip items with no display text — spreadsheet artifacts
                raw_notes = item.get('output_notes', '')
                item_merge_tags = dict(page_merge_tags)
                follow_up_config = item.get('follow_up_config')
                if follow_up_config:
                    configs = []
                    if isinstance(follow_up_config, str):
                        try:
                            parsed = json.loads(follow_up_config)
                            configs = parsed if isinstance(parsed, list) else [parsed]
                        except Exception:
                            pass
                    elif isinstance(follow_up_config, list):
                        configs = follow_up_config
                    for idx, cfg in enumerate(configs):
                        cfg_type = cfg.get('type', '')
                        field_name = f"follow_up_{item.get('line_code', '')}_{idx}"
                        user_answer = checkbox_data.get(field_name) or form_data.get(field_name) or ''
                        if isinstance(user_answer, dict):
                            user_answer = user_answer.get('preselected', [])
                        if isinstance(user_answer, list):
                            user_answer = user_answer[0] if user_answer else ''
                        user_answer = str(user_answer or '').strip()
                        if cfg_type and cfg_type.startswith('Dropdown') and user_answer:
                            item_merge_tags['select'] = user_answer
                        elif cfg_type and cfg_type.startswith('Single Entry') and user_answer:
                            tag = ['one', 'two', 'three'][idx] if idx < 3 else str(idx + 1)
                            item_merge_tags[tag] = user_answer
                output_notes = replace_merge_tags(raw_notes, item_merge_tags)
                output_guidance = replace_merge_tags(item.get('output_guidance', ''), item_merge_tags)
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
                    'category_sort_order': db_category_order.get(category, 999),
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
    follow_up_data = session.get('checkbox_data', {})
    session_overrides = session.get('session_overrides', {})
    try:
        import calculator
        calc_result = calculator.calculate_quote(form_key, form_data, session_overrides, follow_up_data)
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
    db_category_order = _get_page_category_order(page_key)

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
            'category_sort_order': -1,
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
            'category_sort_order': -1,
        })

    page_merge_tags = get_merge_tag_values(page_key, session, get_line_items_for_page, page_blocks=page.get('blocks', []))

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

            items.sort(key=lambda x: (
                db_category_order.get(x.get('category', ''), 999),
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
                            'category_sort_order': db_category_order.get(category, 999),
                        })

                output_title = item.get('output_title', '') or ''
                if not output_title.strip():
                    continue  # skip items with no display text — spreadsheet artifacts
                raw_notes = item.get('output_notes', '')
                item_merge_tags = dict(page_merge_tags)
                follow_up_config = item.get('follow_up_config')
                if follow_up_config:
                    configs = []
                    if isinstance(follow_up_config, str):
                        try:
                            parsed = json.loads(follow_up_config)
                            configs = parsed if isinstance(parsed, list) else [parsed]
                        except Exception:
                            pass
                    elif isinstance(follow_up_config, list):
                        configs = follow_up_config
                    for idx, cfg in enumerate(configs):
                        cfg_type = cfg.get('type', '')
                        field_name = f"follow_up_{item.get('line_code', '')}_{idx}"
                        user_answer = checkbox_data.get(field_name) or form_data.get(field_name) or ''
                        if isinstance(user_answer, dict):
                            user_answer = user_answer.get('preselected', [])
                        if isinstance(user_answer, list):
                            user_answer = user_answer[0] if user_answer else ''
                        user_answer = str(user_answer or '').strip()
                        if cfg_type and cfg_type.startswith('Dropdown') and user_answer:
                            item_merge_tags['select'] = user_answer
                        elif cfg_type and cfg_type.startswith('Single Entry') and user_answer:
                            tag = ['one', 'two', 'three'][idx] if idx < 3 else str(idx + 1)
                            item_merge_tags[tag] = user_answer
                output_notes = replace_merge_tags(raw_notes, item_merge_tags)
                output_guidance = replace_merge_tags(item.get('output_guidance', ''), item_merge_tags)
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
                    'category_sort_order': db_category_order.get(category, 999),
                })
            continue

        if block_type in ('checkbox_group', 'text_input', 'number_currency_input', 'dropdown_select'):
            label = b.get('standard', {}).get('label', b.get('label', key))
            label = replace_merge_tags(label, page_merge_tags)
            snapshot_blocks.append({
                'id': f"form__{page_key}__{b.get('id', key)}",
                'type': 'form_question',
                'source_page': page_key,
                'source_block_id': str(b.get('id', key)),
                'snapshot': {
                    'label': label,
                    'value': raw_value if isinstance(raw_value, str) else ', '.join(raw_value),
                },
                'editor_overrides': {},
                'flags': { 'source_dirty': False, 'editor_dirty': False },
                'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left', 'font_size': 16 },
                'category_sort_order': 999,
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

    try:
        ordered_pages = get_all_pages(template_key=form_key)
        page_display_orders = {pg['page_key']: pg['display_order'] for pg in ordered_pages}
        pages = dict(sorted(pages.items(), key=lambda x: page_display_orders.get(x[0], 999)))
    except Exception:
        pass

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
            pass

        elif block_type == 'page_heading':
            pass

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
