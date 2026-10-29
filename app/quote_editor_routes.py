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
    _default_db_path,
    get_line_items_by_codes,
    get_line_items_for_page,
    get_all_pages,
    list_output_templates,
    save_theme,
    get_theme,
    apply_theme_to_blocks,
    delete_theme,
    _connect,
)

quote_editor_bp = Blueprint('quote_editor', __name__)


def _get_category_image(page_key, category_name):
    """Return the first category image URL for a category (backwards compat)."""
    images = _get_category_images(page_key, category_name)
    return images[0] if images else ''


def _get_category_images(page_key, category_name):
    """Return list of image URLs for a category, in sort_order."""
    try:
        conn = _connect()
        rows = conn.execute(
            '''
            SELECT ci.image_url
            FROM category_images ci
            JOIN page_templates pt ON pt.id = ci.page_template_id
            WHERE pt.page_key = ? AND ci.category_name = ?
            ORDER BY ci.sort_order, ci.id
            ''',
            (page_key, category_name),
        ).fetchall()
        conn.close()
        return [r['image_url'] for r in rows if r['image_url']]
    except Exception:
        pass
    return []


def _get_page_category_order(page_key):
    """Return dict of category_name -> display_order from category_templates."""
    try:
        conn = _connect()
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


def _default_line_codes_for_page(page_key):
    """Return line codes whose include_default='Y' for a page.

    These are the BUILD-mode preselected items — the baseline for both FORM
    and QUOTE mode before the user explicitly changes a page's selections.
    """
    codes = []
    try:
        items_by_cat = get_line_items_for_page(page_key)
        for _cat, items_list in items_by_cat.items():
            for item in items_list:
                if item.get('include_default') == 'Y' and item.get('line_code'):
                    code = str(item['line_code']).strip()
                    if code and code not in codes:
                        codes.append(code)
    except Exception:
        pass
    return codes


DB_PATH = Path(__file__).parent / "template_store.sqlite3"
UPLOAD_DIR = Path(__file__).parent / "static" / "uploads" / "quote_editor"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_line_item_labels(codes):
    """Resolve a list of line codes to human-readable labels.

    Never return raw line codes to the user — always resolve via
    get_line_items_by_codes() so the quote output shows item descriptions
    (output_title / internal_description) instead of legacy codes like
    bw2^, cs1#, pp1@.
    """
    if not isinstance(codes, list):
        return codes
    if not codes:
        return []
    try:
        items = get_line_items_by_codes(codes)
        by_code = {it.get('line_code'): it for it in items if it.get('line_code')}
        labels = []
        for code in codes:
            item = by_code.get(code)
            if item:
                labels.append(item.get('output_title') or item.get('internal_description') or code)
            else:
                labels.append(code)
        return labels
    except Exception:
        return codes


# ── Layout CRUD ─────────────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/layouts', methods=['GET'])
def build_quote_block_identity(block_type, source_page, category):
    """Canonical identity for a regenerable title block.

    Used by the persistent hide-on-delete mechanism: `page_title`,
    `page_heading` and `category_title` blocks are re-derived from FORM state
    on every QUOTE load, so a deletion is persisted as a "hidden identity"
    rather than as an absent block.

    Line-item (form_question) blocks are NOT supported — they are protected in
    QUOTE mode and can only be removed by unchecking in FORM mode.
    """
    if block_type == 'page_title':
        return 'page:' + source_page
    if block_type == 'page_heading':
        return 'heading:' + source_page
    if block_type == 'category_title':
        return 'category:' + source_page + ':' + (category or '')
    return ''


# Only title blocks participate in persistent deletion. Anything else (e.g.
# line-item blocks, images that belong to FORM questions) is rejected.
_HIDDEN_IDENTITY_PREFIXES = ('page:', 'heading:', 'category:')


def _validate_hidden_identity(identity):
    """Return True when the identity is one of the supported title blocks."""
    return bool(identity) and identity.startswith(_HIDDEN_IDENTITY_PREFIXES)


@quote_editor_bp.route('/quote_editor/hide-block', methods=['POST'])
def hide_quote_block():
    """Persist the deletion of a regenerable title block in the session."""
    data = request.get_json(force=True) or {}
    identity = data.get('identity') or build_quote_block_identity(
        data.get('block_type', ''),
        data.get('source_page', ''),
        data.get('category', ''),
    )
    if not _validate_hidden_identity(identity):
        # Line items / questions cannot be deleted this way.
        return jsonify({'success': False, 'error': 'Block identity not deletable'}), 400
    hidden = session.setdefault('quote_editor_hidden_blocks', [])
    if identity not in hidden:
        hidden.append(identity)
        session.modified = True
    return jsonify({'success': True})


@quote_editor_bp.route('/quote_editor/unhide-block', methods=['POST'])
def unhide_quote_block():
    """Undo a persisted title-block deletion (used by editor undo)."""
    data = request.get_json(force=True) or {}
    identity = data.get('identity') or build_quote_block_identity(
        data.get('block_type', ''),
        data.get('source_page', ''),
        data.get('category', ''),
    )
    if not _validate_hidden_identity(identity):
        return jsonify({'success': False, 'error': 'Block identity not deletable'}), 400
    hidden = session.get('quote_editor_hidden_blocks', [])
    if identity in hidden:
        hidden.remove(identity)
        session.modified = True
    return jsonify({'success': True})


def list_layouts():
    form_key = session.get('template_key')
    layouts = list_quote_editor_layouts(form_key)
    return jsonify({'success': True, 'layouts': layouts})


@quote_editor_bp.route('/quote_editor/layouts', methods=['POST'])
def create_layout():
    form_key = session.get('template_key')
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
    form_key = session.get('template_key')
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
    form_key = session.get('template_key')
    ok = set_quote_editor_layout_default(layout_id, form_key)
    if not ok:
        return jsonify({'success': False, 'error': 'Layout not found'}), 404
    return jsonify({'success': True})


@quote_editor_bp.route('/quote_editor/layouts/<int:layout_id>', methods=['DELETE'])
def delete_layout(layout_id):
    form_key = session.get('template_key')
    ok = delete_quote_editor_layout(layout_id, form_key)
    if not ok:
        return jsonify({'success': False, 'error': 'Layout not found'}), 404
    return jsonify({'success': True})


@quote_editor_bp.route('/quote_editor/layouts/<int:layout_id>/duplicate', methods=['POST'])
def duplicate_layout(layout_id):
    form_key = session.get('template_key')
    data = request.get_json(force=True) or {}
    new_name = data.get('name', 'Copy of Layout')
    layout = duplicate_quote_editor_layout(layout_id, form_key, new_name)
    if not layout:
        return jsonify({'success': False, 'error': 'Layout not found'}), 404
    return jsonify({'success': True, 'layout': layout}), 201


# ── Saved Quotes ────────────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/save-quote', methods=['POST'])
def save_quote_route():
    form_key = session.get('template_key')
    data = request.get_json(force=True) or {}
    name = data.get('name', 'Untitled Quote')
    client_name = data.get('client_name', '')
    notes = data.get('notes', '')
    blocks = data.get('blocks_json', [])
    settings = data.get('settings_json', {})
    layout_id = data.get('layout_id')
    user_id = session.get('user_id')
    # Always use live form data — selections from FORM mode flow into QUOTE mode
    default_form_data = {
        'data': session.get('data', {}),
        'checkbox_data': session.get('checkbox_data', {}),
        'session_overrides': session.get('session_overrides', {}),
        'hidden_blocks': session.get('quote_editor_hidden_blocks', []),
        'template_key': form_key,
    }
    form_data = data.get('form_data') or default_form_data
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
# ── Quote Themes ───────────────────────────────────────────────────

@quote_editor_bp.route('/quote_editor/themes', methods=['GET'])
def themes_list():
    form_key = session.get('template_key')
    themes = list_output_templates(form_key)
    return jsonify({'success': True, 'themes': themes})


@quote_editor_bp.route('/quote_editor/themes/<int:theme_id>', methods=['GET'])
def get_theme_route(theme_id):
    form_key = session.get('template_key')
    theme = get_theme(theme_id, form_key)
    if not theme:
        return jsonify({'success': False, 'error': 'Theme not found'}), 404
    return jsonify({'success': True, 'theme': {
        **theme,
        'settings': {'document_styles': theme.get('css', {})},
    }})


# Look up theme by name (used by existing JS that passes theme name)
@quote_editor_bp.route('/quote_editor/themes/by-name/<name>', methods=['GET'])
def get_theme_by_name_route(name):
    form_key = session.get('template_key')
    themes = list_output_templates(form_key)
    for t in themes:
        if t.get('name') == name:
            return get_theme_route(t['id'])
    return jsonify({'success': False, 'error': 'Theme not found'}), 404


@quote_editor_bp.route('/quote_editor/themes', methods=['POST'])
def save_theme_route():
    """Save a theme from the current quote's block formatting.

    Compatible with both the JS format (settings_json.document_styles)
    and the new format (blocks, css).
    """
    form_key = session.get('template_key')
    data = request.get_json(force=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Theme name is required'}), 400

    # Extract CSS from whichever format the client sends
    css = data.get('css', {})
    settings_json = data.get('settings_json', {})
    if isinstance(settings_json, dict) and settings_json.get('document_styles'):
        css = settings_json['document_styles']

    blocks = data.get('blocks', [])
    result = save_theme(
        form_key,
        name=name,
        css_json=css,
        source_blocks=blocks,
        is_default=data.get('is_default', False),
    )
    if not result:
        return jsonify({'success': False, 'error': 'Could not save theme'}), 500
    return jsonify({'success': True, 'theme': result})


@quote_editor_bp.route('/quote_editor/themes/<int:theme_id>/apply', methods=['POST'])
def apply_theme_route(theme_id):
    """Apply a theme's block defaults to the given blocks and return them."""
    form_key = session.get('template_key')
    data = request.get_json(force=True) or {}
    blocks = data.get('blocks', [])
    updated = apply_theme_to_blocks(theme_id, blocks, form_key)
    return jsonify({'success': True, 'blocks': updated})


@quote_editor_bp.route('/quote_editor/themes/<int:theme_id>', methods=['DELETE'])
def delete_theme_route(theme_id):
    form_key = session.get('template_key')
    ok = delete_theme(theme_id, form_key)
    if not ok:
        return jsonify({'success': False, 'error': 'Theme not found'}), 404
    return jsonify({'success': True})
    if not quote:
        return jsonify({'success': False, 'error': 'Form template not found'}), 404
    return jsonify({'success': True, 'quote': quote}), 201


@quote_editor_bp.route('/quote_editor/load-quote/<int:quote_id>', methods=['GET'])
def load_quote_route(quote_id):
    form_key = session.get('template_key')
    quote = get_saved_quote(quote_id, form_key)
    if not quote:
        return jsonify({'success': False, 'error': 'Quote not found'}), 404
    session['active_quote_id'] = quote_id
    form_data = quote.get('form_data') or {}
    # Load saved form data into the live session so FORM mode and QUOTE mode
    # share the same state — selections made in either mode are visible in both.
    session['data'] = form_data.get('data', {})
    session['checkbox_data'] = form_data.get('checkbox_data', {})
    session['session_overrides'] = form_data.get('session_overrides', {})
    # Persisted title-block deletions travel with the saved state.
    session['quote_editor_hidden_blocks'] = form_data.get('hidden_blocks', [])
    if form_data.get('template_key'):
        session['template_key'] = form_data['template_key']
    session['_auto_restored'] = True
    # Restore manual blocks (calculator, image groups, payment schedule, etc.)
    all_blocks = quote.get('blocks_json', [])
    manual_blocks = [
        b for b in all_blocks
        if b.get('type') not in ('page_title', 'category_title', 'form_question')
    ]
    session['quote_editor_pending_blocks'] = manual_blocks
    session.pop('legacy_spreadsheet_data', None)
    session.pop('old_form_answers', None)
    session.pop('quote_editor_data', None)
    session.pop('quote_editor_checkbox_data', None)
    session.pop('quote_editor_template_key', None)
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
        conn = _connect()
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
        conn = _connect()
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
        ordered_pages = get_all_pages(template_key=session.get('template_key'))
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
    form_key = session.get('template_key')
    user_id = session.get('user_id')
    quotes = list_saved_quotes(form_key, user_id=user_id)
    # Hide internal bookkeeping rows (auto-saves) from the user-facing list.
    quotes = [q for q in quotes if not str(q.get('name') or '').startswith('_')]
    return jsonify({'success': True, 'quotes': quotes})


@quote_editor_bp.route('/quote_editor/quotes', methods=['POST'])
def create_quote():
    form_key = session.get('template_key')
    user_id = session.get('user_id')
    data = request.get_json(force=True) or {}
    name = data.get('name', 'Untitled')
    blocks = data.get('blocks_json', [])
    settings = data.get('settings_json') or {}
    # Always use live form data — selections from FORM mode flow into QUOTE mode
    default_form_data = {
        'data': session.get('data', {}),
        'checkbox_data': session.get('checkbox_data', {}),
        'session_overrides': session.get('session_overrides', {}),
        'hidden_blocks': session.get('quote_editor_hidden_blocks', []),
        'template_key': form_key,
    }
    form_data = data.get('form_data') or default_form_data
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
    form_key = session.get('template_key')
    ok = delete_saved_quote(quote_id, form_key)
    if not ok:
        return jsonify({'success': False, 'error': 'Quote not found'}), 404
    return jsonify({'success': True})


@quote_editor_bp.route('/quote_editor/quotes/<int:quote_id>', methods=['PUT'])
def update_quote_route(quote_id):
    form_key = session.get('template_key')
    data = request.get_json(force=True) or {}
    name = data.get('name')
    blocks = data.get('blocks_json')
    settings = data.get('settings_json')
    client_name = data.get('client_name', '')
    notes = data.get('notes', '')
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    # Always use live form data — selections from FORM mode flow into QUOTE mode
    default_form_data = {
        'data': session.get('data', {}),
        'checkbox_data': session.get('checkbox_data', {}),
        'session_overrides': session.get('session_overrides', {}),
        'hidden_blocks': session.get('quote_editor_hidden_blocks', []),
        'template_key': form_key,
    }
    form_data = data.get('form_data') or default_form_data
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
    form_key = session.get('template_key')
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
    # Always read from live form data
    form_data = session.get('data', {})
    checkbox_data = session.get('checkbox_data', {})
    storage = target.get('storage', {})
    key = storage.get('key', block_id)
    standard_name = target.get('standard', {}).get('name', '')
    value = checkbox_data.get(key) or form_data.get(key) or ''
    # FORM mode saves under standard.name (or block.id if no standard.name).
    # Try standard.name as fallback when key differs from standard_name.
    if not value and standard_name and standard_name != key:
        value = checkbox_data.get(standard_name) or form_data.get(standard_name) or ''
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
    form_key = session.get('template_key')
    payload = load_template_payload(form_key)
    if not payload:
        return jsonify({'success': False, 'error': 'Template payload not found'}), 404
    pages = payload.get('builder_beta', {}).get('pages', payload.get('pages', {}))
    page = pages.get(page_key, {})
    blocks = page.get('blocks', page.get('fields', []))
    # Always read from live form data
    form_data = session.get('data', {})
    checkbox_data = session.get('checkbox_data', {})
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
            'flags': { 'source_dirty': False, 'editor_dirty': False },
            'settings': { 'margin_top': 10, 'margin_bottom': 10, 'padding': 12, 'alignment': 'left' },
            'category_sort_order': -1,
        })

    for b in blocks:
        block_type = b.get('block_type', b.get('type', ''))
        storage = b.get('storage', {})
        key = storage.get('key', str(b.get('id', '')))
        standard_name = b.get('standard', {}).get('name', '')
        raw_value = checkbox_data.get(key) or form_data.get(key) or ''
        # FORM mode saves under standard.name (or block.id if no standard.name).
        # Try standard.name as fallback when key differs from standard_name.
        if not raw_value and standard_name and standard_name != key:
            _fallback = checkbox_data.get(standard_name) or form_data.get(standard_name) or ''
            if _fallback:
                raw_value = _fallback
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
                        category_images = _get_category_images(page_key, category)
                        snapshot_blocks.append({
                            'id': f"form__{page_key}__category__{category}",
                            'type': 'category_title',
                            'source_page': page_key,
                            'source_block_id': '__category_title__',
                            'snapshot': {'title': category},
                            'editor_overrides': {},
                            'flags': { 'source_dirty': False, 'editor_dirty': False },
                            'settings': { 'margin_top': 5, 'margin_bottom': 5, 'padding': 12, 'alignment': 'left', 'font_size': 20 },
                            'category_sort_order': db_category_order.get(category, 999),
                        })
                        for idx, img_url in enumerate(category_images):
                            snapshot_blocks.append({
                                'id': f"form__{page_key}__category__{category}__image__{idx}",
                                'type': 'image',
                                'source_page': page_key,
                                'source_block_id': '__category_image__',
                                'snapshot': {'url': img_url},
                                'editor_overrides': {},
                                'flags': { 'source_dirty': False, 'editor_dirty': False },
                                'settings': { 'margin_top': 4, 'margin_bottom': 8, 'padding': 0, 'alignment': 'left', 'font_size': 16 },
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
                if output_guidance:
                    value_text = (value_text + ' ' + output_guidance).strip() if value_text else output_guidance

                snapshot_blocks.append({
                    'id': f"form__{page_key}__{key}__{item.get('line_code', '')}",
                    'type': 'form_question',
                    'source_page': page_key,
                    'source_block_id': str(key),
                    'source_standard_name': standard_name,
                    'snapshot': {
                        'label': output_title,
                        'value': value_text,
                        'output_notes': '',
                        'output_guidance': '',
                        'category': category,
                    },
                    'editor_overrides': {},
                    'flags': { 'source_dirty': False, 'editor_dirty': False },
                    'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left' },
                    'category_sort_order': db_category_order.get(category, 999),
                })

                question_images = item.get('question_images') or []
                if isinstance(question_images, list):
                    for idx, img_url in enumerate(question_images):
                        if not img_url:
                            continue
                        snapshot_blocks.append({
                            'id': f"form__{page_key}__{key}__{item.get('line_code', '')}__image__{idx}",
                            'type': 'image',
                            'source_page': page_key,
                            'source_block_id': f"__question_image__{item.get('line_code', '')}__{idx}",
                            'snapshot': {'url': img_url},
                            'editor_overrides': {},
                            'flags': { 'source_dirty': False, 'editor_dirty': False },
                            'settings': { 'margin_top': 4, 'margin_bottom': 8, 'padding': 0, 'alignment': 'left', 'font_size': 16 },
                        })
            continue

    
    if snapshot_blocks:
        session['quote_editor_pending_blocks'] = snapshot_blocks
        session.modified = True
    
    return jsonify({'success': True, 'blocks': snapshot_blocks, 'redirect': '/quote_editor'})


@quote_editor_bp.route('/quote_editor/add-calc-block', methods=['GET'])
def add_calc_block():
    form_key = session.get('template_key')
    # Always read from live form data — FORM mode selections flow into QUOTE mode
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


@quote_editor_bp.route('/quote_editor/add-payment-schedule-block', methods=['GET'])
def add_payment_schedule_block():
    """Return a payment_schedule block with current calculator snapshot data."""
    form_key = session.get('template_key')
    # Always read from live form data — FORM mode selections flow into QUOTE mode
    form_data = session.get('data', {})
    follow_up_data = session.get('checkbox_data', {})
    session_overrides = session.get('session_overrides', {})
    try:
        import calculator
        calc_result = calculator.calculate_quote(form_key, form_data, session_overrides, follow_up_data)
    except Exception:
        calc_result = {}
    # Ensure payment_schedule key exists
    if 'payment_schedule' not in calc_result:
        calc_result['payment_schedule'] = []
    block = {
        'id': f"payment_schedule__{int(__import__('time').time())}",
        'type': 'payment_schedule',
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
    # Title-block deletions are persisted in QUOTE mode as hidden identities,
    # so title blocks stay deleted across reloads / saves / loads.
    hidden_blocks = session.get('quote_editor_hidden_blocks', []) or []

    # Bottom-up filtering: a page's title/heading blocks are emitted AFTER the
    # page's content is built, and only when the page has content (at least one
    # selected question / category) — or for the quote's cover page (index /
    # Project Details), which always appears.
    page_title = page.get('title') or page_key.replace('_', ' ').title()
    page_has_content = False

    page_merge_tags = get_merge_tag_values(page_key, session, get_line_items_for_page, page_blocks=page.get('blocks', []))

    for b in blocks:
        block_type = b.get('block_type', b.get('type', ''))
        storage = b.get('storage', {})
        key = storage.get('key', str(b.get('id', '')))
        standard_name = b.get('standard', {}).get('name', '')
        raw_value = checkbox_data.get(key) or form_data.get(key) or ''
        # FORM mode saves under standard.name (or block.id if no standard.name).
        # Try standard.name as fallback when key differs from standard_name.
        if not raw_value and standard_name and standard_name != key:
            _fallback = checkbox_data.get(standard_name) or form_data.get(standard_name) or ''
            if _fallback:
                raw_value = _fallback
        if isinstance(raw_value, dict):
            raw_value = raw_value.get('preselected', [])
        if not raw_value:
            raw_value = ''

        if block_type == 'line_items_by_category':
            # Always show categories — quote editor must display page structure
            # regardless of whether form data exists.
            selected_codes = []
            if isinstance(raw_value, list):
                selected_codes = [v for v in raw_value if isinstance(v, str) and v.strip()]
            # BUILD-mode preselected items (include_default='Y') are the QUOTE
            # baseline whenever this field has never been explicitly saved
            # (no entry in checkbox_data / form_data). Once a FORM page is
            # saved, the exact checkbox state is respected — including an
            # explicit empty selection.
            if not selected_codes and key not in checkbox_data and key not in form_data:
                for _def_code in _default_line_codes_for_page(page_key):
                    if _def_code not in selected_codes:
                        selected_codes.append(_def_code)
            items = get_line_items_by_codes(selected_codes) if selected_codes else []

            items.sort(key=lambda x: (
                db_category_order.get(x.get('category', ''), 999),
                x.get('sort_order', 0),
                x.get('line_code', '')
            ))

            # Group items by category
            items_by_category = {}
            for item in items:
                cat = item.get('category', '')
                items_by_category.setdefault(cat, []).append(item)

            # Bottom-up: only categories that actually have selected items appear.
            all_cats = list(items_by_category.keys())

            for category in all_cats:
                if category in seen_categories:
                    continue
                seen_categories.add(category)
                category_items = items_by_category.get(category, [])
                if not category_items:
                    continue  # category with no selected questions is omitted
                page_has_content = True
                category_images = _get_category_images(page_key, category)
                # Persisted deletion: hide the category title (and its category
                # images) but keep the line items — they still mirror FORM.
                category_title_hidden = f'category:{page_key}:{category}' in hidden_blocks
                if not category_title_hidden:
                    snapshot_blocks.append({
                        'id': f"form__{page_key}__category__{category}",
                        'type': 'category_title',
                        'source_page': page_key,
                        'source_block_id': '__category_title__',
                        'snapshot': {'title': category},
                        'editor_overrides': {},
                        'flags': { 'source_dirty': False, 'editor_dirty': False },
                        'settings': { 'margin_top': 5, 'margin_bottom': 5, 'padding': 12, 'alignment': 'left', 'font_size': 20 },
                        'category_sort_order': db_category_order.get(category, 999),
                    })
                if not category_title_hidden:
                    for idx, img_url in enumerate(category_images):
                        snapshot_blocks.append({
                            'id': f"form__{page_key}__category__{category}__image__{idx}",
                            'type': 'image',
                            'source_page': page_key,
                            'source_block_id': '__category_image__',
                            'snapshot': {'url': img_url},
                            'editor_overrides': {},
                            'flags': { 'source_dirty': False, 'editor_dirty': False },
                            'settings': { 'margin_top': 4, 'margin_bottom': 8, 'padding': 0, 'alignment': 'left', 'font_size': 16 },
                        })
                for item in category_items:
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
                                configs = json.loads(follow_up_config)
                                if not isinstance(configs, list):
                                    configs = [configs]
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
                    if output_guidance:
                        value_text = (value_text + ' ' + output_guidance).strip() if value_text else output_guidance

                    snapshot_blocks.append({
                        'id': f"form__{page_key}__{key}__{item.get('line_code', '')}",
                        'type': 'form_question',
                        'source_page': page_key,
                        'source_block_id': str(key),
                        'source_standard_name': standard_name,
                        'snapshot': {
                            'label': output_title,
                            'value': value_text,
                            'output_notes': '',
                            'output_guidance': '',
                            'category': category,
                        },
                        'editor_overrides': {},
                        'flags': { 'source_dirty': False, 'editor_dirty': False },
                        'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left' },
                        'category_sort_order': db_category_order.get(category, 999),
                    })

                    question_images = item.get('question_images') or []
                    if isinstance(question_images, list):
                        for idx, img_url in enumerate(question_images):
                            if not img_url:
                                continue
                            snapshot_blocks.append({
                                'id': f"form__{page_key}__{key}__{item.get('line_code', '')}__image__{idx}",
                                'type': 'image',
                                'source_page': page_key,
                                'source_block_id': f"__question_image__{item.get('line_code', '')}__{idx}",
                                'snapshot': {'url': img_url},
                                'editor_overrides': {},
                                'flags': { 'source_dirty': False, 'editor_dirty': False },
                                'settings': { 'margin_top': 4, 'margin_bottom': 8, 'padding': 0, 'alignment': 'left', 'font_size': 16 },
                            })
            continue

    # Bottom-up: emit the page title/heading only when this page produced
    # content — or always for the quote's cover page (index / Project Details),
    # so the document header is always present.
    if page_has_content or page_key == 'index':
        if f'page:{page_key}' not in hidden_blocks:
            snapshot_blocks.insert(0, {
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
        if f'heading:{page_key}' not in hidden_blocks:
            snapshot_blocks.insert(1, {
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

    return snapshot_blocks


def _get_page_visibility(page_key: str) -> dict:
    """Return {form_visible, quote_visible} for a page, defaulting both to True."""
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT metadata_json FROM page_templates WHERE page_key = ? "
            "AND form_template_version_id IN (SELECT id FROM form_template_versions "
            "WHERE form_template_id = (SELECT id FROM form_templates WHERE key = ?) "
            "ORDER BY version DESC LIMIT 1)",
            (page_key, session.get('template_key'))
        ).fetchone()
        conn.close()
        if row and row[0]:
            try:
                meta = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                return {
                    'form_visible': meta.get('form_visible', True),
                    'quote_visible': meta.get('quote_visible', True),
                }
            except Exception:
                pass
    except Exception:
        pass
    return {'form_visible': True, 'quote_visible': True}


def build_quote_editor_blocks_for_all_pages():
    """Build blocks for every page in the current form template.
    
    Always reads from live form data (session['data'] / session['checkbox_data'])
    so that selections made in FORM mode immediately appear in QUOTE mode.
    """
    form_key = session.get('template_key')
    form_data = session.get('data', {})
    checkbox_data = session.get('checkbox_data', {})
    payload = load_template_payload(form_key)
    if not payload:
        # Stale filesystem sessions persist across deployments and may hold an
        # obsolete template_key that no longer has a payload in the database.
        # Repair the session and rebuild against the active default template so
        # Quote Mode never renders a blank "No blocks yet." editor.
        from config import TEMPLATE_STORE_KEY as _active_key
        form_key = _active_key
        session['template_key'] = form_key
        session['quote_editor_template_key'] = form_key
        session.modified = True
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
    
    all_blocks = []
    for page_key, page in pages.items():
        vis = _get_page_visibility(page_key)
        if not vis.get('quote_visible', True):
            continue
        # Image Upload is a step page (uploaded images become image blocks),
        # not a page of the quote document — keep it out of the page order.
        if page_key == 'image_upload_page':
            continue
        page_blocks = _build_page_blocks(page_key, page, form_data, checkbox_data)
        all_blocks.extend(page_blocks)
    return all_blocks


def get_quote_editor_blocks():
    """Build blocks fresh from session form data.

    Always builds fresh from session data (checkbox_data / form_data) so that
    selections made in FORM mode immediately appear in QUOTE mode.

    Never returns saved blocks from the database — "Load" is an explicit
    user action handled by load_quote_route(), not an automatic fallback.
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
    rows = []
    try:
        conn = _connect()
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
    try:
        conn = _connect()
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
    try:
        conn = _connect()
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
    try:
        conn = _connect()
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
    form_key = session.get('template_key')

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
            # Line items are the only form_question blocks in quote mode.
            # Their values come from the DB build (output_notes + output_guidance),
            # not from form session data — skip sync to preserve them.
            continue

    if updated > 0:
        update_saved_quote(
            quote_id=int(quote_id),
            form_key=form_key,
            name=quote.get('name', 'Quote'),
            blocks_json=blocks,
            settings=quote.get('settings_json', {}),
        )

    return jsonify({'success': True, 'updated': updated})
