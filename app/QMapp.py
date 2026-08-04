#!/usr/bin/env python3

# Built-in Modules
from templates import TEMPLATE_COORDINATES, get_layout_definition
from PIL import Image, ImageOps
import os
import re
import subprocess
import time
import json
import functools
import sqlite3
import logging
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually read .env file if python-dotenv not available
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip())
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, Response
from datetime import datetime
import traceback
from typing import Optional

# Third-party Modules
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from templates import generate_template_svg
from pathlib import Path
from copy import deepcopy
import calculator
from template_store import (
    initialize_template_store,
    load_template_payload,
    get_latest_template_version,
    get_template_store_status,
    get_template_store_overview,
    clone_template,
    load_option_set,
    import_sheet_rows_to_catalog,
    get_line_items_by_codes,
    get_all_pages,
    get_line_items_for_page,
)
from config import (
    TEMPLATE_STORE_READ_ENABLED,
    TEMPLATE_STORE_KEY,
    TEMPLATE_STORE_DB_PATH,
    FLASK_SECRET_KEY,
)

app = Flask(__name__)
csrf = CSRFProtect(app)

# Helper: parse builder form floats with bounds


def _parse_builder_float(value, default, min_val, max_val):
    try:
        val = float(value)
        return val if min_val <= val <= max_val else default
    except (ValueError, TypeError):
        return default

# Helper: parse builder form ints with bounds


def _parse_builder_int(value, default, min_val, max_val):
    try:
        val = int(value)
        return val if min_val <= val <= max_val else default
    except (ValueError, TypeError):
        return default


def is_truthy_env(name: str) -> bool:
    return os.getenv(name, '').strip().lower() in {'1', 'true', 'yes', 'on'}


TEST_MODE = is_truthy_env('QM_TEST_MODE')
SHEETS_DISABLED = is_truthy_env('QM_DISABLE_SHEETS')
# QM_CATALOG_SOURCE: 'auto' (default) = DB first, Sheets fallback;
#                    'db'   = DB only (demo-safe, no Sheets needed);
#                    'sheets' = live Sheets always (debug/override)
CATALOG_SOURCE = os.getenv('QM_CATALOG_SOURCE', 'auto').strip().lower()


# Auth / Role system

# Bootstrap credential: set QM_ADMIN_PASSWORD env var on first run.
# Use POST /admin/promote to elevate a session to admin role thereafter.
ADMIN_PASSWORD = os.getenv('QM_ADMIN_PASSWORD', '')

# <-- DEBUG INFO -->
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"[QMapp] ADMIN_PASSWORD (redacted) = {'*' * len(ADMIN_PASSWORD)}")

VALID_ROLES = {'admin', 'user'}
def require_role(*roles):
    """Decorator: redirect to /login when session role is not in `roles`."""
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            current_role = session.get('role')
            if current_role not in roles:
                session['_login_next'] = request.url
                flash('Please log in to access that page.', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# Define upload folder path
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB total (if batch)
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the filesystem
app.config['SESSION_FILE_DIR'] = str(Path(__file__).parent / 'flask_session')
app.config['SECRET_KEY'] = os.getenv(
    'QM_SECRET_KEY', 'dev-insecure-key-change-me')

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize the session extension
Session(app)

# inject current user role and edit mode into every template context
@app.context_processor
def inject_ui_context():
    """Inject auth and edit-mode state into every template context."""
    role = session.get('role')
    is_admin = role == 'admin'
    edit_requested = request.args.get('edit', '').lower() in {
        '1', 'true', 'yes'}
    edit_mode = is_admin and edit_requested

    # ✅ Always load db_pages so navigation works for all users
    db_pages = get_all_pages(template_key=TEMPLATE_STORE_KEY)

    return dict(
        current_user_role=role,
        current_username=session.get('username'),
        is_admin=is_admin,
        edit_mode=edit_mode,
        db_pages=db_pages,
    )


# Get line items for a page, grouped by category, from the template store.


def _get_line_items_for_page(page_id: str):
    """Return line items for a page, grouped by category.
    Wraps get_line_items_for_page()."""
    try:
        return get_line_items_for_page(page_id)
    except Exception:
        return {}

# Get list of category names for a page from the schema, fallback to keys
# from get_line_items_for_page().


def _get_li_categories_from_schema(page_id: str):
    """Return list of category names for a page from the schema.
    Falls back to keys from get_line_items_for_page()."""
    try:
        items = get_line_items_for_page(page_id)
        return list(items.keys()) if items else []
    except Exception:
        return []


# Legacy: page_schemas.json – will be replaced by template store in
# subsequent chunks
page_schema_path = Path(__file__).parent / 'page_schemas.json'
with page_schema_path.open() as f:
    page_schemas = json.load(f)

print(
    f"[CONFIG] Using TEMPLATE_STORE_KEY={TEMPLATE_STORE_KEY}, READ_ENABLED={TEMPLATE_STORE_READ_ENABLED}")

try:
    template_store_bootstrap = initialize_template_store(
        page_schemas, template_key=TEMPLATE_STORE_KEY)
    print(
        "Template store ready:",
        f"pages={template_store_bootstrap.get('pages', 0)}",
        f"questions={template_store_bootstrap.get('questions', 0)}",
        f"db={template_store_bootstrap.get('db_path', '')}",
    )
except Exception as exc:
    template_store_bootstrap = {'error': str(exc)}
    print(f"Template store bootstrap skipped: {exc}")

# Sync catalog data (sheet rows -> option_sets / option_items) on every
# startup.
if TEMPLATE_STORE_READ_ENABLED:
    try:
        db_payload = load_template_payload(template_key=TEMPLATE_STORE_KEY)
        if db_payload:
            page_schemas = db_payload
            print(
                "Template store read enabled:",
                f"template={TEMPLATE_STORE_KEY}",
                f"version={get_latest_template_version(TEMPLATE_STORE_KEY)}",
            )
        else:
            print(
                "Template store read enabled, but no payload found. Using JSON schema file.")
    except Exception as exc:
        print(
            f"Template store read failed, falling back to JSON schema: {exc}")


def get_builder_settings():
    """Read builder settings from template store DB.

    Primary: form_templates.settings_json in SQLite.
    Fallback: page_schemas['settings'] in-memory dict.
    """
    db_path = Path(__file__).parent / 'template_store.sqlite3'
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                'SELECT settings_json FROM form_templates WHERE key = ?',
                (TEMPLATE_STORE_KEY,),
            ).fetchone()
            conn.close()
            if row and row['settings_json']:
                settings = json.loads(row['settings_json'])
                if isinstance(settings, dict):
                    page_schemas['settings'] = settings  # keep in-memory sync
                    return settings
        except Exception as exc:
            print(f"[get_builder_settings] DB read failed: {exc}")
    # Legacy fallback: read from page_schemas dict
    settings = page_schemas.setdefault('settings', {})
    if not isinstance(settings, dict):
        settings = {}
        page_schemas['settings'] = settings
    return settings


def save_builder_settings(settings: dict):
    """Persist builder settings to both DB and JSON file.

    Primary: form_templates.settings_json in SQLite.
    Also updates page_schemas['settings'] for in-memory consistency.
    """
    # 1. Write to DB
    db_path = Path(__file__).parent / 'template_store.sqlite3'
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute(
                'UPDATE form_templates SET settings_json = ? WHERE key = ?',
                (json.dumps(settings, indent=2), TEMPLATE_STORE_KEY),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            print(f"[save_builder_settings] DB write failed: {exc}")
    # 2. Keep JSON dict in sync
    page_schemas['settings'] = settings


def save_page_schemas():
    with page_schema_path.open('w') as f:
        json.dump(page_schemas, f, indent=2)
    try:
        initialize_template_store(
            page_schemas, template_key=TEMPLATE_STORE_KEY)
    except Exception as exc:
        print(f"Template store sync skipped after save: {exc}")


def save_field_override(
    page_id: str,
    field_id: str,
    hidden: Optional[bool] = None,
    label_override: Optional[str] = None,
    option_overrides: Optional[dict] = None,
    format_options: Optional[dict] = None,
) -> bool:
    """Patch field overrides in DB (question_templates.metadata_json).

    Returns True if the field was found and saved, False if page/field not found.
    """
    db_path = Path(__file__).parent / 'template_store.sqlite3'
    if not db_path.exists():
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            '''SELECT qt.id, qt.metadata_json FROM question_templates qt
               JOIN page_templates pt ON pt.id = qt.page_template_id
               JOIN form_template_versions ftv ON ftv.id = pt.form_template_version_id
               JOIN form_templates ft ON ft.id = ftv.form_template_id
               WHERE ft.key = ? AND pt.page_key = ? AND qt.question_key = ?
               ORDER BY ftv.version DESC LIMIT 1''',
            (TEMPLATE_STORE_KEY, page_id, field_id),
        ).fetchone()

        if not row:
            conn.close()
            return False

        meta = json.loads(row['metadata_json'] or '{}')

        if hidden is not None:
            meta['hidden'] = bool(hidden)
        if label_override is not None:
            meta['label_override'] = label_override.strip()
        if format_options is not None:
            meta['format_options'] = dict(format_options)
        if option_overrides is not None:
            existing = meta.setdefault('option_overrides', {})
            for val, overrides in option_overrides.items():
                entry = existing.setdefault(str(val), {})
                if 'hidden' in overrides:
                    entry['hidden'] = bool(overrides['hidden'])
                if 'deleted' in overrides:
                    entry['deleted'] = bool(overrides['deleted'])
                if 'label_override' in overrides:
                    entry['label_override'] = str(
                        overrides['label_override']).strip()
                if 'format_options' in overrides and isinstance(
                        overrides['format_options'], dict):
                    entry['format_options'] = dict(overrides['format_options'])
                elif 'format' in overrides and isinstance(overrides['format'], dict):
                    entry['format_options'] = dict(overrides['format'])
                if 'pricing_options' in overrides and isinstance(
                        overrides['pricing_options'], dict):
                    entry['pricing_options'] = dict(
                        overrides['pricing_options'])
                if 'output_options' in overrides and isinstance(
                        overrides['output_options'], dict):
                    entry['output_options'] = dict(overrides['output_options'])

        conn.execute(
            'UPDATE question_templates SET metadata_json = ? WHERE id = ?',
            (json.dumps(meta), int(row['id'])),
        )
        conn.commit()
        conn.close()

        # Sync full page_schemas dict (including builder_beta) to JSON + DB
        save_page_schemas()
        return True

    except Exception as exc:
        print(f'[save_field_override] DB write failed: {exc}')
        return False


def save_field_inspector(
    page_id: str,
    field_id: str,
    pricing_options: Optional[dict] = None,
    output_options: Optional[dict] = None,
) -> bool:
    """Patch pricing/out options in DB (question_templates.metadata_json).

    Returns True if the field was found and saved, False if page/field not found.
    Validates pricing mode against ALLOWED_BLOCK_PRICING_MODES before saving.
    """
    db_path = Path(__file__).parent / 'template_store.sqlite3'
    if not db_path.exists():
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            '''SELECT qt.id, qt.metadata_json FROM question_templates qt
      JOIN page_templates pt ON pt.id = qt.page_template_id
      JOIN form_template_versions ftv ON ftv.id = pt.form_template_version_id
      JOIN form_templates ft ON ft.id = ftv.form_template_id
      WHERE ft.key = ? AND pt.page_key = ? AND qt.question_key = ?
      ORDER BY ftv.version DESC LIMIT 1''',
            (TEMPLATE_STORE_KEY, page_id, field_id),
        ).fetchone()

        if not row:
            conn.close()
            return False

        meta = json.loads(row['metadata_json'] or '{}')

        if pricing_options is not None:
            mode = str(pricing_options.get('mode', 'none')).strip()
            if mode not in ALLOWED_BLOCK_PRICING_MODES:
                mode = 'none'
            po = meta.setdefault('pricing_options', {
                'enabled': False, 'mode': 'none', 'fixed_amount': 0.0,
                'entered_key': '', 'quantity_key': '', 'rate': 0.0,
            })
            po['mode'] = mode
            po['enabled'] = mode != 'none'
            for key in ('fixed_amount', 'rate', 'percent_of_subtotal'):
                if key in pricing_options:
                    try:
                        po[key] = float(pricing_options[key])
                    except (TypeError, ValueError):
                        pass
            for key in ('entered_key', 'quantity_key'):
                if key in pricing_options:
                    po[key] = str(pricing_options[key]).strip()

        if output_options is not None:
            oo = meta.setdefault('output_options', {
                'include_in_output': True, 'output_label': '',
                'group': '', 'sort_order': 0, 'value_mode': 'show_value',
            })
            if 'include_in_output' in output_options:
                oo['include_in_output'] = bool(
                    output_options['include_in_output'])
            if 'output_label' in output_options:
                oo['output_label'] = str(
                    output_options['output_label']).strip()
            if 'group' in output_options:
                oo['group'] = str(output_options['group']).strip()
            if 'value_mode' in output_options:
                oo['value_mode'] = str(output_options['value_mode']).strip()

        conn.execute(
            'UPDATE question_templates SET metadata_json = ? WHERE id = ?',
            (json.dumps(meta), int(row['id'])),
        )
        conn.commit()
        conn.close()

        # Sync full page_schemas dict (including builder_beta) to JSON + DB
        save_page_schemas()
        return True

    except Exception as exc:
        print(f'[save_field_inspector] DB write failed: {exc}')
        return False


# ---------------------------------------------------------------------------
# Phase 5 — Draft / Publish helpers (legacy JSON snapshot)
# ---------------------------------------------------------------------------
# Published snapshot path — used by publish/rollback (re-seeds DB via
# save_page_schemas())
published_schema_path = Path(__file__).parent / 'page_schemas_published.json'


def publish_current_draft() -> dict:
    """Snapshot the current draft to JSON file and sync to DB.

    Returns a summary dict with published_at, db_version.
    """
    import datetime as _dt

    # 1. Snapshot current page_schemas to JSON file for backward compatibility
    snapshot = json.loads(json.dumps(page_schemas))
    with published_schema_path.open('w') as f:
        json.dump(snapshot, f, indent=2)

    # 2. Record publish metadata
    db_version = None
    try:
        db_version = get_latest_template_version(TEMPLATE_STORE_KEY)
    except Exception:
        pass

    meta = {
        'published_at': _dt.datetime.utcnow().isoformat() + 'Z',
        'published_by': 'admin',
        'db_version': db_version,
    }
    settings = get_builder_settings()
    settings['last_publish'] = meta

    # 3. Persist settings to DB (so it survives restart)
    save_builder_settings(settings)

    # 4. Also sync full schema to JSON + re-seed DB from JSON
    save_page_schemas()
    return meta

# Reads published JSON snapshot, then re-seeds DB via save_page_schemas()


def rollback_to_published() -> dict:
    """Restore page_schemas from the last published snapshot.

    Returns a summary dict. Raises FileNotFoundError if no publish exists.
    """
    if not published_schema_path.exists():
        raise FileNotFoundError('No published snapshot found. Publish first.')

    with published_schema_path.open() as f:
        restored = json.load(f)

    page_schemas.clear()
    page_schemas.update(restored)
    save_page_schemas()
    return {'rolledback_at': __import__(
        'datetime').datetime.utcnow().isoformat() + 'Z'}


DEFAULT_BUILDER_BETA_QUESTION_TYPES = {
    'checkbox_group': {
        'label': 'Checkbox Group',
        'default_label': 'New checkbox group',
        'supports': {'logic': True, 'pricing': True, 'output': True},
    },
    'text_input': {
        'label': 'Text Input',
        'default_label': 'New text input',
        'supports': {'logic': True, 'pricing': True, 'output': True},
    },
    'number_currency_input': {
        'label': 'Number/Currency Input',
        'default_label': 'New number/currency input',
        'supports': {'logic': True, 'pricing': True, 'output': True},
    },
    'dropdown_select': {
        'label': 'Dropdown Select',
        'default_label': 'New dropdown select',
        'supports': {'logic': True, 'pricing': True, 'output': True},
    },
    'static_text_heading': {
        'label': 'Static Text/Heading',
        'default_label': 'New static text',
        'supports': {'logic': False, 'pricing': False, 'output': True},
    },
}

ALLOWED_BLOCK_PRICING_MODES = {
    'none',
    'fixed',
    'entered',
    'quantity_rate',
    'percent_subtotal'}


def get_builder_beta_state():
    """
    Load the Builder‑Beta state from the *schema* (page_schemas) rather than
    always starting from the hard‑coded defaults.
    """
    # 1️⃣  Grab the raw schema dict – it already contains the default
    #     categories/blocks defined in page_schemas.json (or the DB payload).
    raw_state = page_schemas.get('builder_beta', {})

    # 2️⃣  If the schema does not define a builder_beta entry, fall back to
    #     the built‑in defaults so the app never crashes.
    if not isinstance(raw_state, dict):
        raw_state = deepcopy(DEFAULT_BUILDER_BETA_QUESTION_TYPES)

    # 3️⃣  Ensure the version field exists (required by the rest of the code)
    state = raw_state.copy()
    state.setdefault('version', 1)

    # 4️⃣  Load/initialise question‑type definitions
    question_types = state.get('question_types')
    if not isinstance(question_types, dict):
        state['question_types'] = deepcopy(DEFAULT_BUILDER_BETA_QUESTION_TYPES)
        for k, v in DEFAULT_BUILDER_BETA_QUESTION_TYPES.items():
            question_types.setdefault(k, deepcopy(v))

    # 5️⃣  Load the *pages* from the schema – this is the crucial part.
    #     If the schema contains a 'pages' mapping we honour it; otherwise we
    #     fall back to an empty dict (so the UI still works but is empty).
    schema_pages = page_schemas.get('pages', {})
    if isinstance(schema_pages, dict):
        pages = schema_pages.copy()
    else:
        pages = {}

    # 6️⃣  Ensure the 'pages' key exists in the state and that each page
    #     has the required keys (id, title, navigation, blocks).
    #     Only use state.get('pages') if it has actual content; otherwise
    #     keep the pages from schema_pages above.
    state_pages = state.get('pages', {})
    if isinstance(state_pages, dict) and state_pages:
        pages = state_pages
    # else: keep pages from schema_pages (already set above)

    # Populate any missing defaults for each page.
    for pid, pg in pages.items():
        pg.setdefault('id', pid)
        pg.setdefault('title', pid.replace('_', ' ').title())
        pg.setdefault('navigation', {})
        if not isinstance(pg.get('blocks'), list):
            pg['blocks'] = []   # make sure a list exists

    # 7️⃣  Finally return the fully‑populated state.
    return state

def _find_block(page, block_id):
    for index, block in enumerate(page.get('blocks', [])):
        if block.get('id') == block_id:
            return index, block
    return None, None


def _new_block_template(block_type, page_id, position):
    type_meta = get_builder_beta_state()['question_types'].get(block_type, {})
    default_label = type_meta.get('default_label', 'New block')
    timestamp = int(time.time() * 1000)
    block_id = f'{page_id}__{block_type}_{timestamp}'

    return {
        'id': block_id,
        'block_type': block_type,
        'standard': {
            'label': default_label,
            'name': block_id,
            'required': False,
            'help_text': '',
            'source_prefix': '',
            'placeholder': '',
            'dropdown_choices': [],
            'static_content': '',
            'static_variant': 'body',
        },
        'logic_options': {
            'visibility': 'always',
            'depends_on_field': '',
            'depends_on_value': '',
        },
        'pricing_options': {
            'enabled': False,
            'mode': 'none',
            'fixed_amount': 0.0,
            'entered_key': '',
            'rate': 0.0,
            'quantity_key': '',
            'percent_of_subtotal': 0.0,
        },
        'output_options': {
            'include_in_output': True,
            'output_label': default_label,
            'group': 'General',
            'sort_order': position,
            'value_mode': 'show_value',
        },
    }

# Persists builder beta changes to JSON and re-seeds DB via save_page_schemas()


def update_builder_beta_page_from_form(page_id, form_data):
    state = get_builder_beta_state()
    page = state.get('pages', {}).get(page_id)
    if not page:
        return [f"Unknown builder beta page '{page_id}'."], None

    warnings = []
    action = (form_data.get('action') or '').strip()
    selected_block_id = (form_data.get('selected_block_id') or '').strip()

    if action == 'add_block':
        block_type = (form_data.get('new_block_type') or '').strip()
        if block_type not in state.get('question_types', {}):
            warnings.append(f"Unsupported block type '{block_type}'.")
        else:
            new_block = _new_block_template(
                block_type, page_id, len(page['blocks']))
            page['blocks'].append(new_block)
            selected_block_id = new_block['id']

    elif action == 'delete_block':
        delete_id = (form_data.get('block_id') or '').strip()
        delete_index, _delete_block = _find_block(page, delete_id)
        if _delete_block is None:
            warnings.append('Block to delete was not found.')
        else:
            del page['blocks'][delete_index]
            if selected_block_id == delete_id:
                selected_block_id = page['blocks'][0]['id'] if page['blocks'] else ''

    elif action in {'move_block_up', 'move_block_down'}:
        move_id = (form_data.get('block_id') or '').strip()
        move_index, _move_block = _find_block(page, move_id)
        if _move_block is None:
            warnings.append('Block to move was not found.')
        else:
            swap_index = move_index - 1 if action == 'move_block_up' else move_index + 1
            if swap_index < 0 or swap_index >= len(page['blocks']):
                warnings.append('Cannot move block further in that direction.')
            else:
                page['blocks'][move_index], page['blocks'][swap_index] = \
                    page['blocks'][swap_index], page['blocks'][move_index]

    elif action == 'save_block':
        edit_id = (form_data.get('block_id') or '').strip()
        _edit_index, edit_block = _find_block(page, edit_id)
        if edit_block is None:
            warnings.append('Block to save was not found.')
        else:
            standard = edit_block.setdefault('standard', {})
            logic_options = edit_block.setdefault('logic_options', {})
            pricing_options = edit_block.setdefault('pricing_options', {})
            output_options = edit_block.setdefault('output_options', {})

            standard['label'] = (
                form_data.get('standard_label') or standard.get(
                    'label', '')).strip()
            standard['name'] = (
                form_data.get('standard_name') or standard.get(
                    'name', '')).strip() or standard.get(
                'name', '')
            standard['help_text'] = (
                form_data.get('standard_help_text') or standard.get(
                    'help_text', '')).strip()
            standard['source_prefix'] = (
                form_data.get('standard_source_prefix') or standard.get(
                    'source_prefix', '')).strip()
            standard['placeholder'] = (
                form_data.get('standard_placeholder') or standard.get(
                    'placeholder', '')).strip()
            standard['required'] = form_data.get('standard_required') == 'on'

            static_variant = (
                form_data.get('standard_static_variant') or standard.get(
                    'static_variant', 'body')).strip() or 'body'
            if static_variant not in {'heading', 'subheading', 'body', 'note'}:
                static_variant = 'body'
            standard['static_variant'] = static_variant
            standard['static_content'] = (
                form_data.get('standard_static_content') or standard.get(
                    'static_content', '')).strip()

            raw_choices = form_data.get('standard_dropdown_choices', '')
            if isinstance(raw_choices, str):
                standard['dropdown_choices'] = [
                    c.strip() for c in raw_choices.splitlines() if c.strip()]

            logic_options['visibility'] = (
                form_data.get('logic_visibility') or logic_options.get(
                    'visibility', 'always')).strip() or 'always'
            logic_options['depends_on_field'] = (
                form_data.get('logic_depends_on_field') or logic_options.get(
                    'depends_on_field', '')).strip()
            logic_options['depends_on_value'] = (
                form_data.get('logic_depends_on_value') or logic_options.get(
                    'depends_on_value', '')).strip()

            pricing_enabled = form_data.get('pricing_enabled') == 'on'
            pricing_mode = (
                form_data.get('pricing_mode') or pricing_options.get(
                    'mode', 'none')).strip()
            if pricing_mode not in ALLOWED_BLOCK_PRICING_MODES:
                warnings.append(
                    f"Invalid pricing mode '{pricing_mode}'. Using 'none'.")
                pricing_mode = 'none'

            pricing_options['enabled'] = pricing_enabled
            pricing_options['mode'] = pricing_mode
            pricing_options['fixed_amount'] = _parse_builder_float(
                form_data.get('pricing_fixed_amount'), pricing_options.get('fixed_amount', 0.0), 0, 1000000)
            pricing_options['entered_key'] = (
                form_data.get('pricing_entered_key') or pricing_options.get(
                    'entered_key', '')).strip()
            pricing_options['rate'] = _parse_builder_float(
                form_data.get('pricing_rate'), pricing_options.get('rate', 0.0), 0, 1000000)
            pricing_options['quantity_key'] = (
                form_data.get('pricing_quantity_key') or pricing_options.get(
                    'quantity_key', '')).strip()
            pricing_options['percent_of_subtotal'] = _parse_builder_float(
                form_data.get('pricing_percent_of_subtotal'), pricing_options.get('percent_of_subtotal', 0.0), 0, 100)

            output_options['include_in_output'] = form_data.get(
                'output_include_in_output') == 'on'
            output_options['output_label'] = (
                form_data.get('output_label') or output_options.get(
                    'output_label', '')).strip()
            output_options['group'] = (
                form_data.get('output_group') or output_options.get(
                    'group', 'General')).strip() or 'General'
            output_options['sort_order'] = _parse_builder_int(
                form_data.get('output_sort_order'), output_options.get('sort_order', 0), 0, 100000)
            output_options['value_mode'] = (
                form_data.get('output_value_mode') or output_options.get(
                    'value_mode', 'show_value')).strip() or 'show_value'

            selected_block_id = edit_id

    for index, block in enumerate(page.get('blocks', [])):
        block.setdefault('output_options', {})['sort_order'] = index

    save_page_schemas()
    return warnings, selected_block_id


def compile_builder_beta_page_to_runtime_schema(page_id):
    state = get_builder_beta_state()
    page = state.get('pages', {}).get(page_id)
    if not page:
        return None

    compiled_fields = []
    for block in page.get('blocks', []):
        block_type = block.get('block_type', 'checkbox_group')
        standard = block.get('standard', {})
        field_name = standard.get('name') or block.get('id')
        field_label = standard.get('label') or field_name
        common_payload = {
            'id': block.get('id'),
            'name': field_name,
            'label': field_label,
            'note': standard.get('help_text', ''),
            'hidden': block.get('hidden', False),
            'builder_beta_meta': {
                'block_type': block_type,
                'placeholder': standard.get('placeholder', ''),
                'dropdown_choices': standard.get('dropdown_choices', []),
                'static_content': standard.get('static_content', ''),
                'static_variant': standard.get('static_variant', 'body'),
                'logic_options': deepcopy(block.get('logic_options', {})),
                'pricing_options': deepcopy(block.get('pricing_options', {})),
                'output_options': deepcopy(block.get('output_options', {})),
            },
        }

        if block_type == 'checkbox_group':
            compiled_fields.append({
                **common_payload,
                'type': 'checkbox_group',
                'source': {
                    'type': 'sheet_prefix',
                    'prefix': standard.get('source_prefix', ''),
                    'suffix': 'digits',
                },
            })
        elif block_type == 'line_items_by_category':
            compiled_fields.append({
                **common_payload,
                'type': 'line_items_by_category',
                'config': deepcopy(block.get('config', {})),
            })
        else:
            compiled_fields.append({
                **common_payload,
                'type': block_type,
                'label': f"[beta:{block_type}] {field_label}",
            })

    return {
        'id': page_id,
        'title': page.get('title', page_id.replace('_', ' ').title()),
        'navigation': deepcopy(page.get('navigation', {})),
        'fields': compiled_fields,
    }

# Dynamic – prefers template store, falls back to sheet data


def _builder_beta_checkbox_options(field_schema, sheet_data):
    source = field_schema.get('source', {})
    prefix = str(source.get('prefix', '') or '')

    if TEMPLATE_STORE_READ_ENABLED and prefix:
        db_options = load_option_set(prefix, TEMPLATE_STORE_KEY)
        if db_options is not None:
            return db_options

    options = []

    for row in sheet_data:
        line_code = row.get('Line Code', '').strip()
        internal_description = row.get('Internal Description', '').strip()
        include = row.get('Include', '').strip()

        if not line_code_matches_source(
                line_code, prefix, source.get('suffix')):
            continue

        options.append({
            'value': line_code,
            'label': internal_description,
            'is_included': include == 'Y',
        })

    return options


def build_builder_beta_runtime_context(page_id, sheet_data, page_answers):
    compiled_page = compile_builder_beta_page_to_runtime_schema(page_id)
    if not compiled_page:
        return None

    # If page_answers is a complex checkbox_data dict, extract the specific field preselection
    # or fallback to direct name access if it's a flat dict.
    def get_preselected(name):
        if not isinstance(page_answers, dict):
            return []
        # If we passed the whole checkbox_data dict
        if name in page_answers and isinstance(
                page_answers[name], dict) and 'preselected' in page_answers[name]:
            return page_answers[name]['preselected']
        # If we passed a flat answers dict
        return page_answers.get(name, [])

    runtime_fields = []
    for field in compiled_page.get('fields', []):
        meta = field.get('builder_beta_meta', {})
        block_type = meta.get('block_type', 'checkbox_group')
        field_name = field.get('name')
        field_entry = {
            'id': field.get('id'),
            'name': field_name,
            'label': field.get('label', field_name),
            'note': field.get('note', ''),
            'block_type': block_type,
            'type': block_type,
            'builder_beta_meta': deepcopy(meta),
            'placeholder': meta.get('placeholder', ''),
            'static_content': meta.get('static_content', ''),
            'static_variant': meta.get('static_variant', 'body'),
        }

        if block_type == 'checkbox_group':
            options = _builder_beta_checkbox_options(field, sheet_data)
            stored = get_preselected(field_name)
            if not isinstance(stored, list):
                stored = []
            if not stored:
                stored = [option['value']
                          for option in options if option.get('is_included')]
            field_entry['options'] = options
            field_entry['value'] = stored

        elif block_type == 'dropdown_select':
            choices = meta.get('dropdown_choices', [])
            if not isinstance(choices, list):
                choices = []
            field_entry['choices'] = choices
            field_entry['value'] = str(page_answers.get(field_name, '') or '')

        elif block_type in {'text_input', 'number_currency_input'}:
            field_entry['value'] = str(page_answers.get(field_name, '') or '')
        elif block_type == 'line_items_by_category':
            _li_raw = _get_line_items_for_page(page_id)
            if isinstance(_li_raw, dict):
                li_groups = [
                    {'category': c, 'items': [
                        {'value': r.get('line_code', ''),
                         'label': r.get('internal_description') or r.get('line_code', ''),
                         'include_default': r.get('include_default') or 'N',
                         'is_follow_up': r.get('is_follow_up') or 0,
                         'follow_up_type': r.get('follow_up_type') or '',
                         'follow_up_config': r.get('follow_up_config') or '{}'}
                        for r in v
                    ]}
                    for c, v in _li_raw.items()
                ]
            else:
                li_groups = _li_raw
            stored = get_preselected(field_name)
            if not isinstance(stored, list):
                stored = []
            if not stored:
                stored = []
                for grp in (li_groups or []):
                    if not isinstance(grp, dict):
                        continue
                    for item in (grp.get('items') or []):
                        if not isinstance(item, dict):
                            continue
                        if item.get('include_default') == 'Y' and item.get(
                                'value'):
                            stored.append(item['value'])
            field_entry['li_groups'] = li_groups
            field_entry['value'] = stored

        runtime_fields.append(field_entry)

    compiled_page['fields'] = runtime_fields
    return compiled_page

def resolve_builder_beta_navigation_targets(page_id, runtime_page):
    state = get_builder_beta_state()
    pages = state.get('pages', {})
    navigation = runtime_page.get(
        'navigation',
        {}) if isinstance(
        runtime_page,
        dict) else {}
    previous_endpoint = str(
        navigation.get(
            'previous_endpoint',
            '') or '').strip()
    next_endpoint = str(navigation.get('next_endpoint', '') or '').strip()

    previous_page_id = previous_endpoint if previous_endpoint in pages else None
    next_page_id = next_endpoint if next_endpoint in pages else None

    return {
        'current_page_id': page_id,
        'previous_page_id': previous_page_id,
        'next_page_id': next_page_id,
    }


def _build_builder_beta_output_value(field, answers_for_page):
    name = field.get('name')
    if not name:
        return ''

    block_type = field.get('block_type')
    value = answers_for_page.get(name)

    if block_type == 'checkbox_group':
        if not isinstance(value, list):
            value = []
        return ', '.join(value)

    return str(value or '')


def _build_builder_beta_page_payload_preview(
        page_id, runtime_page, answers_for_page):
    if not isinstance(runtime_page, dict):
        return {
            'page_id': page_id,
            'page_title': page_id.replace('_', ' ').title(),
            'line_items': [],
            'subtotal_before_percent': 0.0,
            'percent_adjustments': 0.0,
            'total_pricing_amount': 0.0,
        }

    if not isinstance(answers_for_page, dict):
        answers_for_page = {}

    line_items = []
    subtotal_before_percent = 0.0
    percent_adjustments = 0.0
    percent_entries = []

    for field in runtime_page.get('fields', []):
        meta = field.get('builder_beta_meta', {})
        pricing = meta.get(
            'pricing_options',
            {}) if isinstance(
            meta,
            dict) else {}
        output = meta.get(
            'output_options',
            {}) if isinstance(
            meta,
            dict) else {}

        include_in_output = bool(output.get('include_in_output', True))
        if not include_in_output:
            continue

        output_label = str(
            output.get(
                'output_label',
                '') or field.get(
                'label',
                field.get(
                    'name',
                    'Field')))
        pricing_enabled = bool(pricing.get('enabled', False))
        pricing_mode = str(pricing.get('mode', 'none') or 'none')

        amount = 0.0
        if pricing_enabled:
            if pricing_mode == 'fixed':
                amount = to_float(pricing.get('fixed_amount'), 0.0)
            elif pricing_mode == 'entered':
                entered_key = str(
                    pricing.get(
                        'entered_key',
                        '') or field.get(
                        'name',
                        ''))
                amount = to_float(answers_for_page.get(entered_key), 0.0)
            elif pricing_mode == 'quantity_rate':
                quantity_key = str(
                    pricing.get(
                        'quantity_key',
                        '') or field.get(
                        'name',
                        ''))
                quantity = to_float(answers_for_page.get(quantity_key), 0.0)
                rate = to_float(pricing.get('rate'), 0.0)
                amount = quantity * rate
            elif pricing_mode == 'percent_subtotal':
                percent_entries.append((field, output_label, pricing, output))

        line_item = {
            'field_id': field.get('id'),
            'field_name': field.get('name'),
            'output_label': output_label,
            'output_value': _build_builder_beta_output_value(field, answers_for_page),
            'pricing_enabled': pricing_enabled,
            'pricing_mode': pricing_mode,
            'amount': round(amount, 2),
            'output_group': str(output.get('group', 'General') or 'General'),
            'sort_order': int(output.get('sort_order', 0) or 0),
        }

        if pricing_enabled and pricing_mode != 'percent_subtotal':
            subtotal_before_percent += amount

        line_items.append(line_item)

    for field, output_label, pricing, output in percent_entries:
        percent_value = to_float(pricing.get('percent_of_subtotal'), 0.0)
        amount = subtotal_before_percent * (percent_value / 100.0)
        percent_adjustments += amount
        line_items.append({
            'field_id': field.get('id'),
            'field_name': field.get('name'),
            'output_label': output_label,
            'output_value': _build_builder_beta_output_value(field, answers_for_page),
            'pricing_enabled': True,
            'pricing_mode': 'percent_subtotal',
            'amount': round(amount, 2),
            'output_group': str(output.get('group', 'General') or 'General'),
            'sort_order': int(output.get('sort_order', 0) or 0),
            'percent_of_subtotal': round(percent_value, 2),
        })

    line_items.sort(
        key=lambda item: (
            item.get(
                'output_group', 'General'), item.get(
                'sort_order', 0), item.get(
                    'output_label', '')))
    total_pricing_amount = round(
        subtotal_before_percent + percent_adjustments, 2)

    return {
        'page_id': page_id,
        'page_title': runtime_page.get('title', page_id.replace('_', ' ').title()),
        'line_items': line_items,
        'subtotal_before_percent': round(subtotal_before_percent, 2),
        'percent_adjustments': round(percent_adjustments, 2),
        'total_pricing_amount': total_pricing_amount,
    }


def build_builder_beta_runtime_payload_preview(
        page_id, runtime_page, builder_beta_answers, sheet_data):
    state = get_builder_beta_state()
    all_pages = state.get('pages', {})
    ordered_page_ids = list(all_pages.keys())

    answers_map = builder_beta_answers if isinstance(
        builder_beta_answers, dict) else {}
    pages_with_answers = [
        pid for pid in ordered_page_ids if isinstance(
            answers_map.get(pid), dict)]

    pages_to_process = []
    for candidate_page_id in [page_id] + pages_with_answers:
        if candidate_page_id in all_pages and candidate_page_id not in pages_to_process:
            pages_to_process.append(candidate_page_id)

    page_summaries = []
    aggregated_line_items = []
    global_subtotal_before_percent = 0.0
    global_percent_adjustments = 0.0

    for target_page_id in pages_to_process:
        answers_for_page = answers_map.get(
            target_page_id, {}) if isinstance(
            answers_map.get(
                target_page_id, {}), dict) else {}
        target_runtime_page = runtime_page if target_page_id == page_id else build_builder_beta_runtime_context(
            target_page_id, sheet_data, answers_for_page)
        page_preview = _build_builder_beta_page_payload_preview(
            target_page_id, target_runtime_page, answers_for_page)
        page_summaries.append(page_preview)

        global_subtotal_before_percent += page_preview.get(
            'subtotal_before_percent', 0.0)
        global_percent_adjustments += page_preview.get(
            'percent_adjustments', 0.0)

        for line_item in page_preview.get('line_items', []):
            aggregated_line_items.append({
                **line_item,
                'page_id': target_page_id,
                'page_title': page_preview.get('page_title', target_page_id.replace('_', ' ').title()),
            })

    aggregated_line_items.sort(
        key=lambda item: (
            item.get(
                'page_title', ''), item.get(
                'output_group', 'General'), item.get(
                    'sort_order', 0), item.get(
                        'output_label', '')))

    current_page_preview = next(
        (page_summary for page_summary in page_summaries if page_summary.get(
            'page_id') == page_id),
        None)
    if current_page_preview is None:
        current_page_preview = _build_builder_beta_page_payload_preview(
            page_id, runtime_page, answers_map.get(page_id, {}))

    return {
        'page_id': page_id,
        'page_title': current_page_preview.get('page_title', page_id.replace('_', ' ').title()),
        'line_items': aggregated_line_items,
        'page_summaries': page_summaries,
        'current_page': current_page_preview,
        'subtotal_before_percent': round(global_subtotal_before_percent, 2),
        'percent_adjustments': round(global_percent_adjustments, 2),
        'total_pricing_amount': round(global_subtotal_before_percent + global_percent_adjustments, 2),
    }


def fetch_catalog_from_db() -> list:
    """Read all catalog rows from SQLite option_sets/option_items.

    Returns rows in the same dict format as fetch_data():
        [{'Line Code': 'bw1', 'Internal Description': '...', 'Include': 'Y'}, ...]
    Returns [] if the DB has no rows for the current template key.
    """
    try:
        import sqlite3 as _sqlite3
        db_path = os.path.join(
            os.path.dirname(__file__),
            'template_store.sqlite3')
        conn = _sqlite3.connect(db_path)
        conn.row_factory = _sqlite3.Row
        rows = conn.execute(
            """
            SELECT oi.line_code, oi.label, oi.is_included
            FROM option_items oi
            JOIN option_sets os ON os.id = oi.option_set_id
            JOIN form_template_versions ftv ON ftv.id = os.form_template_version_id
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            ORDER BY os.prefix ASC, oi.sort_order ASC
            """,
            (TEMPLATE_STORE_KEY,),
        ).fetchall()
        conn.close()
        return [
            {
                'Line Code': row['line_code'],
                'Internal Description': row['label'],
                'Include': 'Y' if row['is_included'] else 'N',
            }
            for row in rows
        ]
    except Exception as e:
        print(f'[catalog_db] Error reading catalog from DB: {e}')
        return []


def get_catalog() -> list:
    """Catalog source — now DB-only (template_store).

    Respects QM_CATALOG_SOURCE for logging, but always reads from DB.
    """
    rows = fetch_catalog_from_db()
    if rows:
        return rows

    # Log why DB was empty, but never fall back to Sheets
    source_log = CATALOG_SOURCE if 'CATALOG_SOURCE' in globals() else 'auto'
    print(f'[catalog] DB empty (source={source_log}) — returning []')
    return []


def allowed_file(filename):
    return '.' in filename and filename.rsplit(
        '.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to check if a line code is included (i.e., marked with 'Y')


def is_included(line_code):
    sheet_data = get_catalog()
    for row in sheet_data:
        if row.get('Line Code') == line_code and row.get('Include') == 'Y':
            return True
    return False

# Alphanumeric function - to return only alphanumeric characters from line
# codes


def to_alphanumeric_code(line_code):
    # Remove all non-alphanumeric characters
    return re.sub(r'[^a-zA-Z0-9]', '', line_code)


def parse_line_code_format(line_code: str) -> dict:
    """Split a line code into base code + trailing legacy format markers.

    Legacy markers are kept for compatibility with QM_Production.py:
      ^ bullet, # single break, * remove preceding break, @ no break
    """
    raw_code = str(line_code or '').strip()
    base_code = raw_code
    markers = ''
    while base_code and base_code[-1] in '#*^@':
        markers = base_code[-1] + markers
        base_code = base_code[:-1]

    return {
        'raw_code': raw_code,
        'base_code': base_code,
        'markers': markers,
        'format_options': {
            'bullet': '^' in markers,
            'single_break': '#' in markers,
            'remove_preceding_break': '*' in markers,
            'no_break': '@' in markers,
        },
    }


def line_code_matches_source(
        line_code: str, prefix: str, suffix_rule: Optional[str] = None) -> bool:
    """Marker-aware prefix/suffix matching used by schema and page filters.

    Matches against the base code (marker suffixes removed).
    """
    parsed = parse_line_code_format(line_code)
    base = parsed['base_code'].lower()
    prefix_norm = str(prefix or '').lower()

    if prefix_norm and not base.startswith(prefix_norm):
        return False

    suffix = base[len(prefix_norm):] if prefix_norm else base
    if suffix_rule == 'digits':
        return suffix.isdigit()

    return True


def is_primary_numeric_code(line_code: str, prefix: str) -> bool:
    """True for base numeric codes only (e.g. oe1, fw12), excluding marker variants."""
    parsed = parse_line_code_format(line_code)
    if parsed['raw_code'] != parsed['base_code']:
        return False
    return line_code_matches_source(line_code, prefix, 'digits')


def infer_output_role(line_code: str, label: str = '') -> str:
    """Infer output role from legacy markers/labels."""
    parsed = parse_line_code_format(line_code)
    markers = parsed.get('markers', '')
    label_norm = str(label or '').lower()

    if '(advisory)' in label_norm or '*' in markers:
        return 'additional_notes'
    if '(notes)' in label_norm or '#' in markers or '@' in markers or '^' in markers:
        return 'description'
    return 'title'

# Function to handle SINGLE dropdown selections (stored in session['data'])


def handle_single_dropdown_session(session, dropdown_key):
    data = session.setdefault('data', {})

    selected_value = request.form.get(dropdown_key, "").strip()  # Single value

    if selected_value:
        data[dropdown_key] = selected_value
    else:
        data.pop(dropdown_key, None)  # Remove if nothing is selected

    session['data'] = data


# Function to handle MULTIPLE dropdown selections (stored in
# session['checkbox_data'])
def handle_multi_dropdown_session(checkbox_data, dropdown_key, selected_list):
    selected_values = request.form.getlist(
        dropdown_key)  # Always returns a list

    if selected_values:
        checkbox_data[dropdown_key] = {"preselected": selected_values}
    else:
        checkbox_data[dropdown_key] = {
            "preselected": []}  # Explicitly store empty

    session['checkbox_data'] = checkbox_data

# Float conversion handling


def to_float(value, default=0.0):
    """
    Converts a string to a float, handling empty values and errors gracefully.
    - If value is a valid number, returns it as a float.
    - If value is empty or invalid, returns the default (0.0 by default).
    """
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return default


@app.route('/builder_beta/page_details_json/<page_key>')
@require_role('admin')
def builder_page_details_json(page_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT title, description FROM page_templates WHERE page_key = ?",
        [page_key]).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({})

@app.route('/form_editor')
@app.route('/edit_home')
@require_role('admin')
def form_editor():
    """Form Editor view combining Form Details and Page Order management."""
    import template_store as ts
    state = get_builder_beta_state()

    # Needs Edit Mode flag enforced since this is an admin-only path
    edit_mode = request.args.get('edit', '0') == '1'
    if not edit_mode:
        return redirect(url_for('index'))

    # Load form level schema configuration
    form_data = ts.get_form_template(TEMPLATE_STORE_KEY)

    form_details = {
        'title': form_data['name'] if form_data else 'Unnamed Form',
        'description': form_data['description'] if form_data else '',
        'key': form_data['key'] if form_data else 'builder_beta'
    }

    # Fetch pages ordered by display_order
    ordered_pages = ts.get_all_pages(TEMPLATE_STORE_KEY)

    return render_template('form.html',
                           form_editor_mode=True,
                           edit_mode=True,
                           builder_state=state,
                           form_details=form_details,
                           db_pages=ordered_pages)


@app.route('/builder_beta/update_form_details', methods=['POST'])
@require_role('admin')
def update_form_details():
    import template_store as ts
    data = request.json
    title = data.get('title')
    description = data.get('description')

    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400

    ts.update_form_template('builder_beta', title, description)
    return jsonify({'success': True})


@app.route('/builder_beta/list_forms')
@require_role('admin')
def list_forms():
    import template_store as ts
    overview = ts.get_template_store_overview()
    forms = overview.get('templates', [])
    return jsonify({'success': True, 'forms': [
                   {'key': f['template_key'], 'name': f['name']} for f in forms]})


@app.route('/builder_beta/switch_form', methods=['POST'])
@require_role('admin')
def switch_form():
    data = request.json
    form_key = data.get('form_key')
    if not form_key:
        return jsonify({'success': False, 'error': 'Form key required'}), 400

    # In a fully fleshed out system, we would store the active working form_key in session
    # Currently builder_beta assumes a single global form or pulls from a specific route
    # For now, we update session['active_form_key'] = form_key
    session['active_form_key'] = form_key
    return jsonify({'success': True})


@app.route('/builder_beta/save_form_as', methods=['POST'])
@require_role('admin')
def save_form_as():
    import template_store as ts
    data = request.json
    old_key = data.get('old_key')
    new_title = data.get('new_title')
    new_description = data.get('new_description', '')

    if not old_key or not new_title:
        return jsonify(
            {'success': False, 'error': 'Old key and new title are required'}), 400

    try:
        new_key = ts.duplicate_form(old_key, new_title, new_description)
        return jsonify({'success': True, 'new_key': new_key})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/builder_beta/delete_form', methods=['POST'])
@require_role('admin')
def delete_form_route():
    import template_store as ts
    data = request.json
    form_key = data.get('form_key')

    if not form_key:
        return jsonify(
            {'success': False, 'error': 'Form key is required'}), 400

    try:
        ts.delete_form(form_key)
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ── Quote Calculator: session override endpoint ──────────────────────────


@app.route('/quote/session-override', methods=['POST'])
def session_override():
    """Accept user price overrides and payment-schedule parameter overrides."""
    data = request.get_json(force=True) or {}
    session.setdefault('overrides', {})

    # Question-level price override
    if 'question_id' in data and 'value' in data:
        session['overrides'][f"q_{data['question_id']}"] = float(data['value'])

    # Output-group (revenue pool) level override
    if 'output_group' in data and 'override_total' in data:
        session['overrides'][f"og_{data['output_group']}"] = float(
            data['override_total'])

    # Payment schedule percentage overrides
    if 'deposit_pct' in data:
        session['overrides']['deposit_pct'] = float(data['deposit_pct'])
    if 'completion_pct' in data:
        session['overrides']['completion_pct'] = float(data['completion_pct'])

    session.modified = True
    return jsonify({'success': True})


# ── Quote Calculator: admin payment-schedule defaults ────────────────────
@app.route('/admin/payment-schedule', methods=['GET', 'POST'])
@require_role('admin')
def admin_payment_schedule():
    """Save default deposit/completion percentages and the allow-override flag."""
    import template_store as ts
    settings = ts.get_payment_schedule_block('builder_beta')

    if request.method == 'POST':
        data = request.get_json(force=True) or {}
        deposit_pct = float(data.get('deposit_pct', settings.get('deposit_pct', 0.10)))
        completion_pct = float(data.get('completion_pct', settings.get('completion_pct', 0.10)))
        allow_override = bool(data.get('allow_user_override', settings.get('allow_user_override', False)))
        initial_payment_pct = float(data.get('initial_payment_pct', settings.get('initial_payment_pct', 0.05)))
        initial_payment_floor = float(data.get('initial_payment_floor', settings.get('initial_payment_floor', 3000.0)))
        initial_payment_ceiling_threshold = float(data.get('initial_payment_ceiling_threshold', settings.get('initial_payment_ceiling_threshold', 70000.0)))
        initial_payment_floor_above_ceiling = float(data.get('initial_payment_floor_above_ceiling', settings.get('initial_payment_floor_above_ceiling', 4000.0)))
        completion_meeting_plus_3rd_pct = float(data.get('completion_meeting_plus_3rd_pct', settings.get('completion_meeting_plus_3rd_pct', 0.35)))
        weekly_payment_count = int(data.get('weekly_payment_count', settings.get('weekly_payment_count', 4)))
        temp_kitchen_line_code = str(data.get('temp_kitchen_line_code', settings.get('temp_kitchen_line_code', 'pl6')))
        temp_kitchen_cost = float(data.get('temp_kitchen_cost', settings.get('temp_kitchen_cost', 250.0)))
        glazing_cost = float(data.get('glazing_cost', settings.get('glazing_cost', 500.0)))

        ts.upsert_payment_schedule_block(
            template_key='builder_beta',
            deposit_pct=deposit_pct,
            completion_pct=completion_pct,
            allow_user_override=allow_override,
            initial_payment_pct=initial_payment_pct,
            initial_payment_floor=initial_payment_floor,
            initial_payment_ceiling_threshold=initial_payment_ceiling_threshold,
            initial_payment_floor_above_ceiling=initial_payment_floor_above_ceiling,
            completion_meeting_plus_3rd_pct=completion_meeting_plus_3rd_pct,
            weekly_payment_count=weekly_payment_count,
            temp_kitchen_line_code=temp_kitchen_line_code,
            temp_kitchen_cost=temp_kitchen_cost,
            glazing_cost=glazing_cost,
        )
        return jsonify({'success': True})

    return render_template(
        'admin_payment_schedule.html',
        deposit_pct=settings.get('deposit_pct', 0.10),
        completion_pct=settings.get('completion_pct', 0.10),
        allow_user_override=settings.get('allow_user_override', False),
        initial_payment_pct=settings.get('initial_payment_pct', 0.05),
        initial_payment_floor=settings.get('initial_payment_floor', 3000.0),
        initial_payment_ceiling_threshold=settings.get('initial_payment_ceiling_threshold', 70000.0),
        initial_payment_floor_above_ceiling=settings.get('initial_payment_floor_above_ceiling', 4000.0),
        completion_meeting_plus_3rd_pct=settings.get('completion_meeting_plus_3rd_pct', 0.35),
        weekly_payment_count=settings.get('weekly_payment_count', 4),
        temp_kitchen_line_code=settings.get('temp_kitchen_line_code', 'pl6'),
        temp_kitchen_cost=settings.get('temp_kitchen_cost', 250.0),
        glazing_cost=settings.get('glazing_cost', 500.0),
    )


@app.route('/builder_beta/page_details_save/<page_key>', methods=['POST'])
@require_role('admin')
def builder_page_details_save(page_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    title = data.get('title', '')
    desc = data.get('description', '')
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE page_templates SET title = ?, description = ? WHERE page_key = ?", [
            title, desc, page_key])
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/builder_beta/category_details_json')
@require_role('admin')
def builder_category_details_json():
    page_key = request.args.get('page_key')
    name = request.args.get('name')
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute('''

        SELECT c.name, c.description, c.output_group
        FROM category_templates c
        JOIN page_templates p ON c.page_template_id = p.id
        WHERE p.page_key = ? AND c.name = ?
    ''', [page_key, name]).fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({})


@app.route('/builder_beta/category_details_save', methods=['POST'])
@require_role('admin')
def builder_category_details_save():
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    desc = data.get('description', '')  # ← FIXED: define desc
    output_group = data.get('output_group', 'General')

    conn = sqlite3.connect(db)
    try:
        # Get page id
        page_id = conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ?",
            [page_key]).fetchone()[0]
        conn.execute(
            "UPDATE category_templates SET name = ?, description = ?, output_group = ? WHERE page_template_id = ? AND name = ?",
            [new_name, desc, output_group, page_id, old_name]
        )

        # Cascading update: line_items category linking to match if changed
        if old_name != new_name:
            conn.execute(
                "UPDATE line_items SET category = ? WHERE form_page = ? AND category = ?",
                [new_name, page_key, old_name]
            )

        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/category/add', methods=['POST'])
@require_role('admin')
def builder_beta_category_add():
    import template_store as _ts
    data = request.get_json(force=True) or {}
    if not data or 'page_key' not in data or 'category_name' not in data:
        return jsonify(
            {'success': False, 'error': 'Missing page_key or category_name'}), 400
    output_group = data.get('output_group', 'General')
    res = _ts.add_category(
        data['page_key'],
        data['category_name'],
        template_key=TEMPLATE_STORE_KEY,
        output_group=output_group)
    if res.get('success'):
        return jsonify({'success': True})
    return jsonify(res), 500


@app.route('/builder_beta/line_item_add', methods=['POST'])
@require_role('admin')
def builder_line_item_add():
    import sqlite3
    import time
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    category = data.get('category')

    if not page_key or not category:
        return jsonify({'success': False, 'error': 'page_key and category are required'}), 400

    conn = None
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row

        # Verify the category exists before attempting insert
        cat_exists = conn.execute(
            "SELECT 1 FROM category_templates ct "
            "JOIN page_templates p ON ct.page_template_id = p.id "
            "WHERE p.page_key = ? AND ct.name = ?",
            [page_key, category]
        ).fetchone()

        if not cat_exists:
            return jsonify({
                'success': False,
                'error': f'Category "{category}" not found on page "{page_key}". Please add the category first.'
            }), 404

        # get max sort
        max_sort = conn.execute(
            "SELECT MAX(sort_order) FROM line_items WHERE form_page = ? AND category = ?",
            [page_key, category]).fetchone()[0]
        next_sort = 0 if max_sort is None else max_sort + 1
        new_code = f"new_{int(time.time())}"

        cur = conn.cursor()
        # Get default output_group from category_templates
        default_group = conn.execute(
            "SELECT output_group FROM category_templates ct "
            "JOIN page_templates p ON ct.page_template_id = p.id "
            "WHERE p.page_key = ? AND ct.name = ?",
            [page_key, category]
        ).fetchone()
        output_group_val = default_group[0] if default_group else 'General'

        cur.execute('''
            INSERT INTO line_items (form_page, category, line_code, internal_description, item_role, form_visible, sort_order, output_group)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        ''', [page_key, category, new_code, "New Question", "parent", next_sort, output_group_val])
        conn.commit()

        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM line_items WHERE id = ?",
            [new_id]).fetchone()

        return jsonify({'success': True, 'item': dict(row)})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()


@app.route('/builder_beta/category/delete', methods=['POST'])
@require_role('admin')
def builder_category_delete():
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    category_name = data.get('category_name')

    conn = sqlite3.connect(db)
    try:
        page_id = conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ?",
            [page_key]).fetchone()[0]
        # Delete category mapping
        conn.execute(
            "DELETE FROM category_templates WHERE page_template_id = ? AND name = ?", [
                page_id, category_name])
        # Additionally delete all child line_items
        conn.execute(
            "DELETE FROM line_items WHERE form_page = ? AND category = ?", [
                page_key, category_name])
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/page_details_delete/<page_key>', methods=['POST'])
@require_role('admin')
def builder_page_delete(page_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ?",
            [page_key]).fetchone()
        if not row:
            return jsonify({'error': 'Page not found'}), 404
        page_id = row[0]
        # Delete dependencies
        conn.execute(
            "DELETE FROM category_templates WHERE page_template_id = ?",
            [page_id])
        conn.execute("DELETE FROM line_items WHERE form_page = ?", [page_key])
        conn.execute("DELETE FROM page_templates WHERE id = ?", [page_id])
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/save_as_template', methods=['POST'])
@require_role('admin')
def builder_save_as_template():
    return jsonify({'ok': True, 'msg': 'Template saved successfully'})


@app.route('/builder_beta/line_item_delete', methods=['POST'])
@require_role('admin')
def builder_line_item_delete():
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    line_code = data.get('line_code')

    if not line_code:
        return jsonify({'error': 'No line code provided'}), 400

    conn = sqlite3.connect(db)
    try:
        conn.execute("DELETE FROM line_items WHERE line_code = ?", [line_code])
        conn.commit()
        return jsonify({'success': True, 'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/line_item_save/<int:item_id>', methods=['POST'])
@require_role('admin')
def builder_line_item_save(item_id):
    """Save/update a line item's editable fields."""
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    conn = sqlite3.connect(db)
    try:
        # Build SET clause from allowed fields
        allowed = [
            'internal_description', 'output_title', 'output_notes', 'output_guidance',
            'unit_cost', 'units', 'pricing_visibility',
            'form_visible', 'category',
            'is_follow_up', 'follow_up_type', 'follow_up_config',
            'output_group', 'allow_user_override',
        ]
        sets = []
        params = []
        for key in allowed:
            if key in data:
                sets.append(f'{key} = ?')
                params.append(data[key])
        if not sets:
            return jsonify({'ok': False, 'error': 'No fields to update'}), 400
        params.append(item_id)
        conn.execute(
            f"UPDATE line_items SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params
        )
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    finally:
        conn.close()


# ── NEW: Save editable question title (internal_description) ─────────────
@app.route('/save-title', methods=['POST'])
@require_role('admin')
def save_title():
    """Persist an edited question title (internal_description) for a line item.

    Expected JSON payload:
      {
        "code": "bw4^",          # line‑item line_code
        "title": "Create a courtyard/lightwell"
      }
    """
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()
    new_title = data.get('title', '').strip()

    if not code:
        return jsonify({'success': False, 'error': 'Missing code'}), 400
    if not new_title:
        return jsonify({'success': False, 'error': 'Title cannot be empty'}), 400
    if len(new_title) > 120:
        return jsonify({'success': False, 'error': 'Title too long (max 120 chars)'}), 400

    conn = None
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row

        # Find the line item by line_code
        row = conn.execute(
            "SELECT id FROM line_items WHERE line_code = ?",
            [code]
        ).fetchone()

        if not row:
            return jsonify({'success': False, 'error': f'Line item with code "{code}" not found'}), 404

        conn.execute(
            "UPDATE line_items SET internal_description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            [new_title, row['id']]
        )
        conn.commit()
        return jsonify({'success': True, 'code': code, 'title': new_title})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()


@app.route('/builder_beta/line_items_json')
@require_role('admin')
def builder_line_items_json():
    """Return line items grouped by category for a given page."""
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    page = request.args.get('page', '')
    category = request.args.get('category', '')
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM line_items WHERE form_page = ? AND category = ? ORDER BY sort_order",
                [page, category]
            ).fetchall()
            categories = [{'name': category, 'items': [dict(r) for r in rows]}]
        else:
            cat_rows = conn.execute(
                "SELECT DISTINCT category FROM line_items WHERE form_page = ? ORDER BY category",
                [page]
            ).fetchall()
            categories = []
            for cr in cat_rows:
                rows = conn.execute(
                    "SELECT * FROM line_items WHERE form_page = ? AND category = ? ORDER BY sort_order",
                    [page, cr['category']]
                ).fetchall()
                categories.append(
                    {'name': cr['category'], 'items': [dict(r) for r in rows]})
        return jsonify({'categories': categories})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/swap_order', methods=['POST'])
@require_role('admin')
def builder_swap_order():
    """Swap sort_order of two adjacent line items or categories."""
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    scope = data.get('scope', 'question')
    identifier = data.get('identifier')
    direction = data.get('direction', 'up')
    page_key = data.get('page_key', '')
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        if scope == 'question':
            # Get current item's sort_order and category
            cur = conn.execute(
                "SELECT sort_order, category FROM line_items WHERE id = ?",
                [identifier]
            ).fetchone()
            if not cur:
                return jsonify({'error': 'Item not found'}), 404
            cur_sort, category = cur
            # Find adjacent item
            op = '<' if direction == 'up' else '>'
            order = 'DESC' if direction == 'up' else 'ASC'
            adj = conn.execute(
                f"SELECT id, sort_order FROM line_items WHERE form_page = ? AND category = ? AND sort_order {op} ? ORDER BY sort_order {order} LIMIT 1",
                [page_key, category, cur_sort]
            ).fetchone()
            if not adj:
                return jsonify({'error': 'No adjacent item'}), 400
            # Swap sort orders
            conn.execute(
                "UPDATE line_items SET sort_order = ? WHERE id = ?", [
                    adj['sort_order'], identifier])
            conn.execute(
                "UPDATE line_items SET sort_order = ? WHERE id = ?", [
                    cur_sort, adj['id']])
            conn.commit()
            return jsonify({'success': True})
        elif scope == 'category':
            # Swap display_order in category_templates
            cur = conn.execute(
                "SELECT display_order FROM category_templates WHERE id = ?",
                [identifier]
            ).fetchone()
            if not cur:
                return jsonify({'error': 'Category not found'}), 404
            cur_order = cur['display_order']
            op = '<' if direction == 'up' else '>'
            order = 'DESC' if direction == 'up' else 'ASC'
            adj = conn.execute(
                f"SELECT id, display_order FROM category_templates WHERE page_template_id = (SELECT page_template_id FROM category_templates WHERE id = ?) AND display_order {op} ? ORDER BY display_order {order} LIMIT 1",
                [identifier, cur_order]
            ).fetchone()
            if not adj:
                return jsonify({'error': 'No adjacent category'}), 400
            conn.execute(
                "UPDATE category_templates SET display_order = ? WHERE id = ?", [
                    adj['display_order'], identifier])
            conn.execute(
                "UPDATE category_templates SET display_order = ? WHERE id = ?", [
                    cur_order, adj['id']])
            conn.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Unknown scope: {scope}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


##########################################################################

        # Image Processing

##########################################################################


def analyze_site_images(upload_path):
    image_meta = []
    for filename in sorted(os.listdir(upload_path)):
        if filename.startswith("img_site_") and allowed_file(filename):
            file_path = os.path.join(upload_path, filename)
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    orientation = 'landscape' if width > height else 'portrait'
                    image_meta.append({
                        'filename': filename,
                        'path': file_path,
                        'orientation': orientation,
                        'width': width,
                        'height': height
                    })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    return image_meta


def select_templates(image_meta):
    def chunk_images(meta, max_group_size=10):
        return [meta[i:i + max_group_size]
                for i in range(0, len(meta), max_group_size)]

    templates = []
    chunks = chunk_images(image_meta)

    for chunk in chunks:
        portrait_count = sum(
            1 for img in chunk if img['orientation'] == 'portrait')
        landscape_count = sum(
            1 for img in chunk if img['orientation'] == 'landscape')
        total_count = len(chunk)

        matching_templates = [
            key for key in TEMPLATE_COORDINATES
            if key.startswith(f'template_{total_count}-{landscape_count}L{portrait_count}P')
        ]

        if matching_templates:
            templates.append({
                'templates': matching_templates,  # Return ALL matching templates
                'images': [img['filename'] for img in chunk]
            })
        else:
            print(
                f"[WARNING] No matching template found for {total_count} images ({landscape_count}L, {portrait_count}P).")

    return templates


def compose_template(image_plan, upload_folder,
                     output_basename='final_output'):
    from PIL import Image, ImageOps

    canvas_width = 2480  # A4 @ 300dpi
    canvas_height = 3508
    margin = 10  # px

    for idx, block in enumerate(image_plan, start=1):
        template_key = block.get('template')
        image_list = block.get('images', [])
        coordinates = get_layout_definition(template_key)

        canvas = Image.new(
            'RGB', (canvas_width, canvas_height), (255, 255, 255))

        for i, (x, y, w, h) in enumerate(coordinates):
            if i >= len(image_list):
                break
            image_filename = image_list[i]
            image_path = os.path.join(upload_folder, image_filename)

            try:
                with Image.open(image_path) as img:
                    img = img.convert("RGB")
                    target_size = (w - 2 * margin, h - 2 * margin)
                    fitted_img = ImageOps.fit(
                        img, target_size, method=Image.LANCZOS)
                    canvas.paste(fitted_img, (x + margin, y + margin))
            except Exception as e:
                print(f"[ERROR] Could not process {image_filename}: {e}")

        # Save individual page
        filename = f"{output_basename}_{idx}.jpg"
        output_path = os.path.join(upload_folder, filename)
        canvas.save(output_path)
        print(f"[INFO] Saved layout page: {output_path}")


##########################################################################
# SVG TEMPLATE PREVIEW ROUTE
##########################################################################

@app.route('/template_preview/<template_key>')
def template_preview(template_key):
    """Return an SVG preview image for the given template key.

    Uses the coordinate data from TEMPLATE_COORDINATES to generate
    an on-the-fly SVG showing each block as a coloured rectangle.
    No image files need to be stored.
    """
    coordinates = get_layout_definition(template_key)
    if not coordinates:
        # Return a simple "not found" SVG
        return Response(
            '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="340">'
            '<rect width="220" height="340" fill="#f8f8f8" stroke="#ddd"/>'
            '<text x="110" y="170" text-anchor="middle" font-size="14" '
            'font-family="Arial" fill="#999">Not found</text></svg>',
            mimetype='image/svg+xml',
            status=404
        )

    svg_content = generate_template_svg(
        coordinates, canvas_width=220, canvas_height=340)
    return Response(svg_content, mimetype='image/svg+xml')


##########################################################################

    # PAGE - Project Details

##########################################################################

def _get_runtime_quote_context():
    """Return the runtime quote context variables needed by the template."""
    data = session.get("data", {})
    return {
        "client_address": data.get("client_address", ""),
        "proposal_date": data.get("Date", ""),
        "quote_ref": data.get("quote_ref", ""),
        "client_name": data.get("client_name", ""),
    }

@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    """Simple login page using the admin password from environment."""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['role'] = 'admin'
            session['username'] = 'admin'
            flash('Logged in as admin.', 'success')
            next_url = session.pop('_login_next', None) or url_for('index')
            return redirect(next_url)
        else:
            flash('Invalid password.', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@csrf.exempt
def logout():
    """Clear the session and redirect to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
    

# ── Dynamic builder-beta page route ──────────────────────────────────
@app.route('/<page_id>', methods=['GET', 'POST'])
def dynamic_page(page_id):
    """Serve any form page defined in the builder beta state."""
    state = get_builder_beta_state()
    all_pages = state.get('pages', {})
    if page_id not in all_pages:
        abort(404)

    session['last_visited'] = page_id
    page = all_pages[page_id]
    page_schema = compile_builder_beta_page_to_runtime_schema(page_id)
    if page_schema is None:
        abort(500)

    checkbox_data = session.setdefault('checkbox_data', {})

    if request.method == 'POST':
        for block in page.get('blocks', []):
            field_name = block.get('standard', {}).get('name') or block.get('id')
            if not field_name:
                continue
            if block['block_type'] in ('checkbox_group', 'line_items_by_category'):
                selected = request.form.getlist(field_name)
                checkbox_data[field_name] = {'preselected': selected}
            else:
                value = (request.form.get(field_name) or '')
                if value:
                    checkbox_data[field_name] = value
        session['checkbox_data'] = checkbox_data
        session.modified = True

        try:
            form_data = session.get('data', {})
            existing_pending = session.get('quote_editor_pending_blocks', [])
            existing_ids = {b.get('id') for b in existing_pending}
            pending = list(existing_pending)
            seen_pages = set()
            seen_categories = set()
            for block in page.get('blocks', []):
                field_name = block.get('standard', {}).get('name') or block.get('id')
                if not field_name:
                    continue
                raw_value = checkbox_data.get(field_name) or form_data.get(field_name) or ''
                if isinstance(raw_value, dict):
                    raw_value = raw_value.get('preselected', [])
                if not raw_value:
                    continue

                if block['block_type'] == 'line_items_by_category' and isinstance(raw_value, list):
                    selected_codes = [v for v in raw_value if isinstance(v, str) and v.strip()]
                    if not selected_codes:
                        continue
                    items = get_line_items_by_codes(selected_codes)
                    if not items:
                        continue

                    page_title = page.get('title') or page_id.replace('_', ' ').title()
                    if page_title not in seen_pages:
                        seen_pages.add(page_title)
                        page_title_id = f"form__{page_id}__page_title"
                        if page_title_id not in existing_ids:
                            pending.append({
                                'id': page_title_id,
                                'type': 'page_title',
                                'source_page': page_id,
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
                                category_id = f"form__{page_id}__category__{category}"
                                if category_id not in existing_ids:
                                    pending.append({
                                        'id': category_id,
                                        'type': 'category_title',
                                        'source_page': page_id,
                                        'source_block_id': '__category_title__',
                                        'snapshot': {'title': category},
                                        'editor_overrides': {},
                                        'flags': { 'source_dirty': False, 'editor_dirty': False },
                                        'settings': { 'margin_top': 5, 'margin_bottom': 5, 'padding': 12, 'alignment': 'left' },
                                    })

                        output_title = item.get('output_title', '') or item.get('internal_description', '') or item.get('line_code', '')
                        output_notes = item.get('output_guidance', '') or item.get('output_notes', '')
                        parts = [output_title]
                        if output_notes:
                            parts.append(output_notes)
                        value_text = ' '.join(parts)

                        question_id = f"form__{page_id}__{field_name}__{item.get('line_code', '')}"
                        if question_id not in existing_ids:
                            pending.append({
                                'id': question_id,
                                'type': 'form_question',
                                'source_page': page_id,
                                'source_block_id': str(field_name),
                                'snapshot': {
                                    'label': output_title,
                                    'value': value_text,
                                    'line_code': item.get('line_code', ''),
                                    'category': category,
                                },
                                'editor_overrides': {},
                                'flags': { 'source_dirty': False, 'editor_dirty': False },
                                'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left' },
                            })
                    continue

                if block['block_type'] in ('checkbox_group', 'text_input', 'number_currency_input', 'dropdown_select'):
                    page_title = page.get('title') or page_id.replace('_', ' ').title()
                    if page_title not in seen_pages:
                        seen_pages.add(page_title)
                        page_title_id = f"form__{page_id}__page_title"
                        if page_title_id not in existing_ids:
                            pending.append({
                                'id': page_title_id,
                                'type': 'page_title',
                                'source_page': page_id,
                                'source_block_id': '__page_title__',
                                'snapshot': {'title': page_title},
                                'editor_overrides': {},
                                'flags': { 'source_dirty': False, 'editor_dirty': False },
                                'settings': { 'margin_top': 10, 'margin_bottom': 10, 'padding': 12, 'alignment': 'left' },
                            })

                        question_id = f"form__{page_id}__{field_name}"
                        if question_id not in existing_ids:
                            pending.append({
                                'id': question_id,
                                'type': 'form_question',
                                'source_page': page_id,
                                'source_block_id': str(field_name),
                                'snapshot': {
                                    'label': block.get('standard', {}).get('label', field_name),
                                    'value': raw_value if isinstance(raw_value, str) else ', '.join(raw_value),
                                },
                                'editor_overrides': {},
                                'flags': { 'source_dirty': False, 'editor_dirty': False },
                                'settings': { 'margin_top': 2, 'margin_bottom': 2, 'padding': 12, 'alignment': 'left' },
                            })
            session['quote_editor_pending_blocks'] = pending
            session.modified = True
        except Exception:
            pass

        nav = resolve_builder_beta_navigation_targets(page_id, page_schema)
        next_page = nav.get('next_page_id')
        if next_page and next_page in all_pages:
            return redirect(url_for('dynamic_page', page_id=next_page))
        return redirect(url_for('review'))

    _li_cats = _get_li_categories_from_schema(page_id) or []
    edit_requested = request.args.get('edit', '').lower() in {'1', 'true', 'yes'}
    edit_mode = session.get('role') == 'admin' and edit_requested

    if edit_mode:
        builder_state = get_builder_beta_state()
        current_page = {
            'id': page_id,
            'title': page_schema.get('title', page_id.replace('_', ' ').title()),
            'blocks': page.get('blocks', [])
        }
        selected_block_id = request.args.get(
            'selected_block_id',
            current_page['blocks'][0]['id'] if current_page['blocks'] else ''
        )

        page_config = page_schema
        
        return render_template(
            'form.html',
            page_schema=page_schema,
            page_config=page_config,
            schema_render_mode='full',
            title=page_schema.get('title', page_id.replace('_', ' ').title()),
            builder_state=builder_state,
            current_page=current_page,
            current_page_id=page_id,
            selected_block_id=selected_block_id,
            selected_block=next(
                (b for b in current_page['blocks'] if b['id'] == selected_block_id), None
            ),
            pricing_modes=sorted(ALLOWED_BLOCK_PRICING_MODES),
            li_categories=_li_cats,
            **_get_runtime_quote_context()
        )
    else:
        page_config = page_schema

        # Compute line-items group data for line_items_by_category blocks
        li_groups_data = None
        for field in page_schema.get('fields', []):
            if field.get('type') == 'line_items_by_category':
                _li_raw = _get_line_items_for_page(page_id)
                if isinstance(_li_raw, dict):
                    li_groups_data = [
                        {'category': c, 'items': [
                            {'value': r.get('line_code', ''),
                             'label': r.get('internal_description') or r.get('line_code', ''),
                             'include_default': r.get('include_default') or 'N',
                             'is_follow_up': r.get('is_follow_up') or 0,
                             'follow_up_type': r.get('follow_up_type') or '',
                             'follow_up_config': r.get('follow_up_config') or '{}'}
                            for r in v
                        ]}
                        for c, v in _li_raw.items()
                    ]
                break

        return render_template(
            'form.html',
            page_schema=page_schema,
            page_config=page_config,
            schema_render_mode='full',
            title=page_schema.get('title', page_id.replace('_', ' ').title()),
            li_categories=_li_cats,
            li_groups=li_groups_data,
            current_page_id=page_id,
            **_get_runtime_quote_context()
        )

@app.route('/', methods=['POST', 'GET'])
def index():
    session['last_visited'] = 'index'

    # Get the first DYNAMIC page from builder beta state (skip redundant index page)
    state = get_builder_beta_state()
    pages = state.get('pages', {})
    # Exclude 'index' (project details) from dynamic pages - start with next page
    dynamic_page_ids = [pid for pid in sorted(pages.keys()) if pid != 'index']
    first_dynamic_page = dynamic_page_ids[0] if dynamic_page_ids else None

    if request.method == 'POST':
        data = session.setdefault('data', {})
        pd1 = request.form.get('client_address', '').strip()
        pd2 = request.form.get('Date', '').strip()
        if pd2:
            try:
                parsed_date = datetime.strptime(pd2, '%Y-%m-%d')
                formatted_date = parsed_date.strftime('%d/%m/%Y')
                data['Date'] = formatted_date
            except ValueError:
                data['Date'] = pd2
        if pd1:
            data['client_address'] = pd1
        session['data'] = data
        session.modified = True

        # Redirect to first dynamic page instead of redundant index page
        if first_dynamic_page:
            return redirect(url_for('dynamic_page', page_id=first_dynamic_page))
        return redirect(url_for('review'))

    # GET: preload form if data exists
    data = session.get('data', {})
    client_address = data.get('client_address', '')
    raw_date = data.get('Date', '')
    try:
        form_date = datetime.strptime(raw_date, '%d/%m/%Y').strftime('%Y-%m-%d')
    except ValueError:
        form_date = ''

    return render_template(
        'form.html',
        first_page=True,
        title="Project Details",
        current_page=None,
        selected_block_id=None,
        edit_mode=False,
        next_page=first_dynamic_page,  # dynamic next page
        form_date=form_date,
        **_get_runtime_quote_context()
    )

@app.route('/admin/template_store_status', methods=['GET'])
@require_role('admin')
def template_store_status():
    return jsonify(get_template_store_status(template_key=TEMPLATE_STORE_KEY))


@app.route('/admin/template_store_templates', methods=['GET'])
@require_role('admin')
def template_store_templates():
    overview = get_template_store_overview()
    overview['active_template_key'] = TEMPLATE_STORE_KEY
    return jsonify(overview)


@app.route('/admin/template_clone', methods=['GET'])
@require_role('admin')
def template_clone():
    new_template_key = request.args.get('new_template_key', '').strip()
    scenario_key = request.args.get(
        'scenario_key',
        'full_extension').strip() or 'full_extension'
    disabled_pages_raw = request.args.get('disabled_pages', '').strip()
    disabled_pages = [item.strip() for item in disabled_pages_raw.split(
        ',') if item.strip()] if disabled_pages_raw else []

    if not new_template_key:
        return jsonify({'error': 'new_template_key is required'}), 400

    try:
        result = clone_template(
            TEMPLATE_STORE_KEY,
            new_template_key,
            scenario_key=scenario_key,
            disabled_pages=disabled_pages,
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify(result)

# depends on save_field_override() which uses page_schemas.json – will
# refactor when template_store.patch_page_field() is available


@app.route('/admin/field_override', methods=['POST'])
@csrf.exempt
@require_role('admin')
def admin_field_override():
    """Save hide/label/option overrides for a schema-driven field.

    POST /admin/field_override
    JSON body:
      {
        "page_id": "example_page",
        "field_id": "example_field",
        "hidden": false,
        "label_override": "Custom label",
        "format_options": {
          "block_type": "list_item",
          "line_break_mode": "single"
        },
        "option_overrides": {
          "opt1": {
            "hidden": true,
            "label_override": "Custom option A",
            "format_options": {"bullet": true}
          }
        }
      }
    """

    body = request.get_json(silent=True) or {}
    page_id = str(body.get('page_id', '')).strip()
    field_id = str(body.get('field_id', '')).strip()

    if not page_id or not field_id:
        return jsonify({'error': 'page_id and field_id are required.'}), 400

    hidden = body.get('hidden')         # may be None (not provided)
    label_override = body.get('label_override')
    format_options = body.get('format_options')
    option_overrides = body.get('option_overrides')

    if hidden is not None:
        hidden = bool(hidden)
    if label_override is not None:
        label_override = str(label_override)
    if format_options is not None and not isinstance(format_options, dict):
        return jsonify({'error': 'format_options must be an object.'}), 400
    if option_overrides is not None and not isinstance(option_overrides, dict):
        return jsonify({'error': 'option_overrides must be an object.'}), 400

    saved = save_field_override(
        page_id=page_id,
        field_id=field_id,
        hidden=hidden,
        label_override=label_override,
        option_overrides=option_overrides,
        format_options=format_options,
    )
    if not saved:
        return jsonify(
            {'error': f'Field "{field_id}" not found on page "{page_id}".'}), 404

    return jsonify({'ok': True, 'page_id': page_id, 'field_id': field_id})

# depends on save_field_inspector() which uses page_schemas.json – will
# refactor when template_store.patch_page_field() is available


@app.route('/admin/field_inspector', methods=['POST'])
@csrf.exempt
@require_role('admin')
def admin_field_inspector():
    """Save pricing_options and output_options for a schema-driven field.

    POST /admin/field_inspector
    JSON body:
      {
        "page_id": "example_page",
        "field_id": "example_field",
        "pricing_options": {"mode": "fixed", "fixed_amount": 250.00},
        "output_options": {"include_in_output": true, "output_label": "Custom output"}
      }
    """
    
    body = request.get_json(silent=True) or {}
    page_id = str(body.get('page_id', '')).strip()
    field_id = str(body.get('field_id', '')).strip()

    if not page_id or not field_id:
        return jsonify({'error': 'page_id and field_id are required.'}), 400

    pricing_options = body.get('pricing_options')
    output_options = body.get('output_options')

    if pricing_options is not None and not isinstance(pricing_options, dict):
        return jsonify({'error': 'pricing_options must be an object.'}), 400
    if output_options is not None and not isinstance(output_options, dict):
        return jsonify({'error': 'output_options must be an object.'}), 400

    saved = save_field_inspector(
        page_id=page_id,
        field_id=field_id,
        pricing_options=pricing_options,
        output_options=output_options,
    )
    if not saved:
        return jsonify(
            {'error': f'Field "{field_id}" not found on page "{page_id}".'}), 404

    return jsonify({'ok': True, 'page_id': page_id, 'field_id': field_id})


# depends on publish_current_draft() which writes
# page_schemas_published.json – will refactor when publish/rollback uses
# template store
@csrf.exempt
@app.route('/admin/publish_draft', methods=['POST'])
@require_role('admin')
def admin_publish_draft():
    """Snapshot the current draft as the published version."""
    try:
        meta = publish_current_draft()
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
    return jsonify({'ok': True, **meta})

# calls rollback_to_published() which relies on
# page_schemas_published.json – will refactor when publish/rollback uses
# template store


@csrf.exempt
@app.route('/admin/rollback', methods=['POST'])
@require_role('admin')
def admin_rollback():
    """Roll back page_schemas to the last published snapshot."""
    try:
        result = rollback_to_published()
    except FileNotFoundError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
    return jsonify({'ok': True, **result})

# depends on get_builder_beta_state() and save_page_schemas() – will
# refactor when builder state migrated to template store


@app.route('/builder_beta/page/<page_id>', methods=['GET', 'POST'])
@require_role('admin')
def builder_beta_page_editor(page_id):
    state = get_builder_beta_state()
    all_pages = state.get('pages', {})
    page = all_pages.get(page_id)
    if not page:
        flash('Builder beta page not found.', 'danger')
        return redirect(url_for('form_editor'))

    selected_block_id = request.args.get('selected_block_id', '').strip()

    if request.method == 'POST':
        action = request.form.get('action', '').strip()

        if action == 'add_block':
            block_type = request.form.get('block_type', '').strip()
            if block_type in state.get('question_types', {}):
                new_block = _new_block_template(
                    block_type, page_id, len(page.get('blocks', [])))
                page.setdefault('blocks', []).append(new_block)
                selected_block_id = new_block['id']
                save_page_schemas()
                flash(f'Added {block_type} block.', 'success')

        elif action == 'delete_block':
            delete_id = request.form.get('block_id', '').strip()
            delete_index, _ = _find_block(page, delete_id)
            if delete_index is not None:
                del page['blocks'][delete_index]
                # Fix: properly handle empty list and first item deletion
                if page['blocks']:
                    # Clamp index to valid range after deletion
                    if delete_index >= len(page['blocks']):
                        delete_index = len(page['blocks']) - 1
                    selected_block_id = page['blocks'][delete_index]['id']
                else:
                    selected_block_id = ''
                save_page_schemas()
                flash('Block deleted.', 'success')

        elif action == 'save_block':
            warnings, new_selected_id = update_builder_beta_page_from_form(page_id, request.form)
            if new_selected_id:
                selected_block_id = new_selected_id
            for warning in warnings:
                flash(warning, 'warning')

        elif action in ['move_block_up', 'move_block_down']:
            warnings, new_selected_id = update_builder_beta_page_from_form(page_id, request.form)
            if new_selected_id:
                selected_block_id = new_selected_id
            for warning in warnings:
                flash(warning, 'warning')

    # GET or after POST - render the template
    return render_template(
        'builder_beta/page_editor.html',
        page=page,
        page_id=page_id,
        selected_block_id=selected_block_id,
        state=state,
        question_types=state.get('question_types', {}),
        pricing_modes=sorted(ALLOWED_BLOCK_PRICING_MODES)
    )

##########################################################################
# PAGE - IMAGE UPLOAD
##########################################################################
# Builder-beta page route — renders from builder beta state
@app.route('/image_upload_page', methods=['GET', 'POST'])
@csrf.exempt
def image_upload_page():
    session['last_visited'] = 'image_upload_page'
    checkbox_data = session.setdefault('checkbox_data', {})

    # ── IMAGE UPLOAD HANDLING ──
    project_title = session.get('data', {}).get('client_address', 'Unnamed_Project')
    safe_title = secure_filename(project_title)
    project_folder = os.path.join(app.config['UPLOAD_FOLDER'], safe_title)
    os.makedirs(project_folder, exist_ok=True)

    uploaded_images = session.get('uploaded_images', {})

    # Handle individual image uploads (cover, CGI, floorplan)
    for image_type in ['cover_image', 'cgi_image', 'floorplan_image']:
        if image_type in request.files:
            file = request.files[image_type]
            if file and file.filename and allowed_file(file.filename):
                filename = f"{image_type}.jpg"
                save_path = os.path.join(project_folder, filename)
                file.save(save_path)
                with Image.open(save_path) as img:
                    img.convert("RGB").save(save_path, format='JPEG', optimize=True, quality=85)
                uploaded_images[filename] = url_for('static', filename=f'uploads/{safe_title}/{filename}')
                session['uploaded_images'] = uploaded_images
                session.modified = True
                flash(f"{image_type.replace('_', ' ').title()} uploaded successfully.", "success")

    # Handle site images upload
    files = request.files.getlist('site_images')
    action = request.form.get('action')
    selected_images = request.form.getlist('selected_images')
    open_accordion = request.form.get('open_accordion')

    index_offset = len([f for f in os.listdir(project_folder) if f.startswith('img_site_')])

    # Reset session and file state if requested
    if request.method == 'POST' and request.form.get('reset_session'):
        for f in os.listdir(project_folder):
            path = os.path.join(project_folder, f)
            if os.path.isfile(path):
                os.remove(path)
        session.pop('uploaded_images', None)
        session.modified = True
        flash("Session and project folder fully reset.", "info")
        return redirect(url_for('image_upload_page'))

    # Delete selected images
    if action == 'delete' and selected_images:
        for filename in selected_images:
            path = os.path.join(project_folder, filename)
            if os.path.exists(path):
                os.remove(path)
                uploaded_images.pop(filename, None)
        session['uploaded_images'] = uploaded_images
        session.modified = True

    # Upload new files
    if files and any(file.filename for file in files):
        for i, file in enumerate(files, start=1):
            if file and allowed_file(file.filename):
                filename = f"img_site_{index_offset + i}.jpg"
                save_path = os.path.join(project_folder, filename)
                file.save(save_path)
                with Image.open(save_path) as img:
                    img.convert("RGB").save(save_path, format='JPEG', optimize=True, quality=85)
                uploaded_images[filename] = url_for('static', filename=f'uploads/{safe_title}/{filename}')

        uploaded_count = len(files)
        if uploaded_count > 0:
            flash(f"{uploaded_count} image{'s' if uploaded_count != 1 else ''} uploaded successfully.", "success")

        # Clear layout
        if request.form.get('clear_layout'):
            for f in os.listdir(project_folder):
                if f.startswith('final_output_') and f.endswith('.jpg'):
                    os.remove(os.path.join(project_folder, f))
                    uploaded_images.pop(f, None)
            session['uploaded_images'] = uploaded_images
            session.modified = True
            return redirect(url_for('image_upload_page'))

        session['uploaded_images'] = uploaded_images
        session.modified = True

    # Always recompute dynamic layout after any upload/delete/clear so the user
    # gets a fresh layout automatically without needing a manual button press.
    site_images = sorted([f for f in uploaded_images if f.startswith('img_site_')])
    cover_cgi_floorplan = [f for f in uploaded_images if f in ['cover_image.jpg', 'cgi_image.jpg', 'floorplan_image.jpg']]
    ordered_images = cover_cgi_floorplan + site_images
    if ordered_images:
        try:
            layout = compute_dynamic_layout(ordered_images, project_folder)
            session['dynamic_layout'] = layout
            compose_dynamic_layout(layout, project_folder)
        except Exception as exc:
            print(f"[layout] compute_dynamic_layout failed: {exc}")
        finally:
            session.modified = True
    else:
        session.pop('dynamic_layout', None)
        session.modified = True

    # ── FORM BUILDER BETA INTEGRATION ──
    if request.method == 'POST' and not files and not action:
        state = get_builder_beta_state()
        page = state.get('pages', {}).get('image_upload_page')
        if page:
            for block in page.get('blocks', []):
                field_name = block.get('standard', {}).get('name')
                if field_name:
                    if block['block_type'] == 'checkbox_group':
                        selected = request.form.getlist(field_name)
                        checkbox_data[field_name] = {'preselected': selected}
                    else:
                        value = (request.form.get(field_name) or '')
                        if value:
                            checkbox_data[field_name] = value

        session['checkbox_data'] = checkbox_data
        session.modified = True
        return redirect(url_for('review'))

    # GET: build runtime schema from builder beta state
    page_schema = compile_builder_beta_page_to_runtime_schema(
        'image_upload_page')

    edit_requested = request.args.get('edit', '').lower() in {
        '1', 'true', 'yes'}
    edit_mode = session.get('role') == 'admin' and edit_requested
    _li_cats = _get_li_categories_from_schema('image_upload_page') or []

    if edit_mode:
        builder_state = get_builder_beta_state()
        current_page_id = 'image_upload_page'
        current_page_blocks = builder_state.get(
            'pages',
            {}).get(
            current_page_id,
            {}).get(
            'blocks',
            [])
        selected_block_id = request.args.get(
            'selected_block_id',
            current_page_blocks[0]['id'] if current_page_blocks else '')
        selected_block = next(
            (b for b in current_page_blocks if b['id'] == selected_block_id), None)

        return render_template(
            'form.html',
            page_schema=page_schema,
            schema_render_mode='full',
            previous_page=page_schema.get(
                'navigation',
                {}).get(
                'previous_endpoint',
                'optional_extras_page') if page_schema else 'optional_extras_page',
            next_page=page_schema.get(
                'navigation',
                {}).get(
                'next_endpoint',
                'review') if page_schema else 'review',
            title=page_schema.get(
                'title', 'Image Upload') if page_schema else 'Image Upload',
            builder_state=builder_state,
            current_page={
                'id': current_page_id,
                'title': page_schema.get(
                    'title',
                    'Image Upload') if page_schema else 'Image Upload',
                'blocks': current_page_blocks},
            current_page_id=current_page_id,
            selected_block_id=selected_block_id,
            selected_block=selected_block,
            pricing_modes=sorted(ALLOWED_BLOCK_PRICING_MODES),
            li_categories=_li_cats,
            **_get_runtime_quote_context()
        )
    else:
        from templates import TEMPLATE_COORDINATES
        project_title = session.get('data', {}).get('client_address', 'Unnamed_Project')
        safe_title = secure_filename(project_title)
        preview_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_title, 'final_output_1.jpg')
        preview_url = url_for('static', filename=f'uploads/{safe_title}/final_output_1.jpg') if session.get('dynamic_layout') and os.path.exists(preview_path) else None
        return render_template(
            'image_upload.html',
            image_upload_page=True,
            previous_page='optional_extras_page',
            next_page='review',
            open_accordion=open_accordion,
            title="Upload Quote-Specific Images",
            uploaded_images=uploaded_images,
            saved_layout=session.get('dynamic_layout', []),
            preview_url=preview_url,
        )


##########################################################################
# DYNAMIC LAYOUT ENDPOINTS
##########################################################################

@app.route('/save_layout', methods=['POST'])
@csrf.exempt
def save_layout():
    """Save the dynamic layout data from Gridstack and return enforced layout."""
    try:
        data = request.get_json()
        layout = data.get('layout', [])
        session['dynamic_layout'] = layout
        session['saved_custom_layout'] = True
        session.modified = True
        return jsonify({'success': True, 'layout': layout})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/generate_preview', methods=['POST'])
@csrf.exempt
def generate_preview():
    """Generate a preview image based on the dynamic layout."""
    try:
        data = request.get_json()
        layout = data.get('layout', [])

        session['dynamic_layout'] = layout
        session['saved_custom_layout'] = True
        session.modified = True

        project_title = session.get('data', {}).get('client_address', 'Unnamed_Project')
        safe_title = secure_filename(project_title)
        project_folder = os.path.join(app.config['UPLOAD_FOLDER'], safe_title)

        compose_dynamic_layout(layout, project_folder)

        from time import time
        preview_url = url_for('static', filename=f'uploads/{safe_title}/final_output_1.jpg') + f'?v={int(time())}'

        return jsonify({'success': True, 'preview_url': preview_url, 'layout': layout})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/clear_dynamic_layout', methods=['POST'])
@csrf.exempt
def clear_dynamic_layout():
    """Remove the pre-configured template layout from the session so the
    drag-and-drop editor starts with a clean slate."""
    session.pop('dynamic_layout', None)
    session.pop('saved_custom_layout', None)
    session.modified = True
    return jsonify({'success': True})


@app.route('/recompute_layout', methods=['POST'])
@csrf.exempt
def recompute_layout():
    """Recompute the auto-layout from uploaded images and store in session."""
    try:
        project_title = session.get('data', {}).get('client_address', 'Unnamed_Project')
        safe_title = secure_filename(project_title)
        project_folder = os.path.join(app.config['UPLOAD_FOLDER'], safe_title)

        uploaded_images = session.get('uploaded_images', {})
        site_images = sorted([f for f in uploaded_images if f.startswith('img_site_')])
        cover_cgi_floorplan = [f for f in uploaded_images if f in ['cover_image.jpg', 'cgi_image.jpg', 'floorplan_image.jpg']]
        ordered_images = cover_cgi_floorplan + site_images

        if ordered_images:
            layout = compute_dynamic_layout(ordered_images, project_folder)
            session['dynamic_layout'] = layout
            session.pop('saved_custom_layout', None)
            session.modified = True
            return jsonify({'success': True, 'layout': layout})

        session.pop('dynamic_layout', None)
        session.pop('saved_custom_layout', None)
        session.modified = True
        return jsonify({'success': True, 'layout': []})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def compute_dynamic_layout(image_filenames, upload_folder):
    """Compute a 6-unit row-bin-packed layout for the given images.
    
    Returns a list of grid items with {id, x, y, w, h}.
    """
    CANVAS_WIDTH_UNITS = 6
    items = []
    for filename in image_filenames:
        image_path = os.path.join(upload_folder, filename)
        if not os.path.exists(image_path):
            continue
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                aspect_ratio = width / height if height else 1
                if aspect_ratio < 0.8:
                    orientation = 'portrait'
                    unit_w = 2
                    unit_h = 3
                elif aspect_ratio > 1.2:
                    orientation = 'landscape'
                    unit_w = 3
                    unit_h = 2
                else:
                    orientation = 'landscape'
                    unit_w = 3
                    unit_h = 2
                items.append({
                    'id': filename,
                    'unit_w': unit_w,
                    'unit_h': unit_h,
                    'orientation': orientation,
                    'aspect_ratio': aspect_ratio,
                })
        except Exception:
            continue

    layout = []
    y = 0
    i = 0
    while i < len(items):
        row_items = []
        row_width = 0
        while i < len(items) and row_width + items[i]['unit_w'] <= CANVAS_WIDTH_UNITS:
            row_items.append(items[i])
            row_width += items[i]['unit_w']
            i += 1

        if not row_items:
            row_items.append(items[i])
            row_width = items[i]['unit_w']
            i += 1

        # Normalize row height to tallest unit_h in row
        row_unit_height = max(item['unit_h'] for item in row_items)
        x = 0
        for item in row_items:
            layout.append({
                'id': item['id'],
                'x': x,
                'y': y,
                'w': item['unit_w'],
                'h': row_unit_height,
            })
            x += item['unit_w']
        y += row_unit_height

    return layout


def compose_dynamic_layout(layout, upload_folder, output_basename='final_output'):
    """Compose images based on dynamic layout data from Gridstack.

    Normalizes heights per row while preserving aspect ratios.
    """
    from PIL import Image, ImageOps

    CANVAS_WIDTH = 2480  # A4 @ 300dpi
    CANVAS_HEIGHT = 3508
    UNIT_SIZE = CANVAS_WIDTH / 6  # 413.333px per unit
    MARGIN = 10  # 10px margin inside each block

    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))

    rows = {}
    print(f"[DEBUG compose_dynamic_layout] Input layout: {layout}")
    sorted_layout = sorted(layout, key=lambda item: (item.get('y', 0), item.get('x', 0)))
    for item in sorted_layout:
        filename = item.get('id')
        grid_x = item.get('x', 0)
        grid_y = item.get('y', 0)
        grid_w = item.get('w', 1)
        grid_h = item.get('h', 1)

        rows.setdefault(grid_y, []).append({
            'filename': filename,
            'x': grid_x,
            'w': grid_w,
            'h': grid_h,
            'pixel_x': int(grid_x * UNIT_SIZE),
            'pixel_y': int(grid_y * UNIT_SIZE),
            'pixel_w': int(grid_w * UNIT_SIZE),
            'pixel_h': int(grid_h * UNIT_SIZE),
        })

    for row_y, items in rows.items():
        row_y_px = int(row_y * UNIT_SIZE)
        for item in items:
            filename = item['filename']
            image_path = os.path.join(upload_folder, filename)
            if not os.path.exists(image_path):
                print(f"[WARNING] Image not found: {image_path}")
                continue

            try:
                with Image.open(image_path) as img:
                    img = img.convert("RGB")

                    target_w = item['pixel_w'] - 2 * MARGIN
                    target_h = item['pixel_h'] - 2 * MARGIN

                    fitted_img = ImageOps.contain(
                        img, (target_w, target_h), method=Image.LANCZOS)

                    paste_x = item['pixel_x'] + MARGIN
                    paste_y = item['pixel_y'] + MARGIN
                    canvas.paste(fitted_img, (paste_x, paste_y))
            except Exception as e:
                print(f"[ERROR] Could not process {filename}: {e}")

    filename = f"{output_basename}_1.jpg"
    output_path = os.path.join(upload_folder, filename)
    canvas.save(output_path)
    print(f"[INFO] Saved dynamic layout: {output_path}")


##########################################################################
# PAGE - REVIEW (form answers summary; pricing lives in Calculator Mode)
##########################################################################

@app.route('/review', methods=['GET', 'POST'])
def review():
    session['last_visited'] = 'review'
    checkbox_data = session.get('checkbox_data', {})

    if request.method == 'POST':
        # Persist any final checkbox changes from the review page and refresh
        checkbox_data = session.setdefault('checkbox_data', {})
        for key, value in request.form.items():
            checkbox_data[key] = value
        session['checkbox_data'] = checkbox_data
        session.modified = True
        return redirect(url_for('review'))

    # ── Build review_data: the user's form answers grouped by page (section) ──
    # Review mode only shows what the user has selected/entered on each page.
    # Pricing math (calculator, line items, cost matrix) lives in Calculator
    # Mode — a separate page — so it is intentionally NOT computed here.
    session_data = session.get('data', {})
    # Keep form_data available for the export routes (export_routes.py reads it).
    session['form_data'] = session_data

    # Pages that are not "answer" pages worth reviewing. image_upload_page is
    # the upload step that, in the new flow, runs AFTER the calculator.
    SKIP_PAGES = {'image_upload_page'}

    state_pages = get_builder_beta_state().get('pages', {})

    # Pass 1: collect selected line codes so we can look up descriptions + categories
    selected_codes = set()
    raw_sections = {}
    for page_id, page_info in state_pages.items():
        if page_id in SKIP_PAGES:
            continue
        compiled_page = compile_builder_beta_page_to_runtime_schema(page_id)
        if not compiled_page:
            continue

        section_fields = {}
        for field in compiled_page.get('fields', []):
            field_name = field.get('name')
            if not field_name:
                continue

            value = session_data.get(field_name)
            if not value:
                cb_val = checkbox_data.get(field_name)
                if isinstance(cb_val, dict):
                    value = cb_val.get('preselected', [])
                elif cb_val:
                    value = cb_val
                else:
                    value = []

            if value:
                if isinstance(value, (list, tuple)):
                    for v in value:
                        if isinstance(v, str) and v.strip():
                            selected_codes.add(v.strip())
                else:
                    if isinstance(value, str) and value.strip():
                        selected_codes.add(value.strip())
                section_fields[field_name] = value

        if section_fields:
            title = page_info.get('title') or page_id.replace('_', ' ').title()
            raw_sections[title] = section_fields

    # Resolve line codes → human-readable labels AND categories
    line_code_labels = {}
    line_code_categories = {}
    if selected_codes:
        try:
            conn = sqlite3.connect(str(Path(__file__).parent / 'template_store.sqlite3'))
            conn.row_factory = sqlite3.Row
            placeholders = ','.join('?' for _ in selected_codes)
            rows = conn.execute(
                f'SELECT line_code, output_title, internal_description FROM line_items WHERE line_code IN ({placeholders})',
                list(selected_codes),
            ).fetchall()
            for row in rows:
                label = row['internal_description'] or row['output_title'] or row['line_code']
                line_code_labels[row['line_code']] = label
                category = row['output_title'].rstrip(':').strip()
                line_code_categories[row['line_code']] = category
            conn.close()
        except Exception:
            pass

    # Pass 2: build review_data, grouping line_items_by_category by category
    review_data = {}
    TITLE_MAPPING = {}
    for page_id, page_info in state_pages.items():
        if page_id in SKIP_PAGES:
            continue
        compiled_page = compile_builder_beta_page_to_runtime_schema(page_id)
        if not compiled_page:
            continue

        section = {}
        for field in compiled_page.get('fields', []):
            field_name = field.get('name')
            if not field_name:
                continue

            raw_value = raw_sections.get(page_info.get('title', ''), {}).get(field_name)
            if not raw_value:
                continue

            meta = field.get('builder_beta_meta', {})
            block_type = meta.get('block_type', field.get('type', 'unknown'))

            label = field.get('label', field_name)
            clean_label = re.sub(r'^\[beta:[^\]]*\]\s*', '', label) if label else field_name
            if not clean_label or clean_label == field_name:
                fallback = field_name
                for suffix in ('__line_items', '_line_items'):
                    if fallback.endswith(suffix):
                        fallback = fallback[: -len(suffix)]
                if fallback.startswith('li_'):
                    fallback = fallback[len('li_'):]
                fallback = fallback.replace('_page', '').replace('_', ' ').strip()
                clean_label = fallback.title() if fallback else field_name.replace('_', ' ').title()
            if field_name and clean_label != field_name:
                TITLE_MAPPING[field_name] = clean_label

            if block_type == 'line_items_by_category' and isinstance(raw_value, list):
                categories = {}
                for code in raw_value:
                    category = line_code_categories.get(code, 'Other')
                    categories.setdefault(category, []).append(code)
                section[field_name] = {
                    '_type': 'line_items_by_category',
                    'categories': categories,
                }
            else:
                section[field_name] = raw_value if isinstance(raw_value, (list, tuple)) else [raw_value]

        if section:
            title = page_info.get('title') or page_id.replace('_', ' ').title()
            review_data[title] = section

    ctx = _get_runtime_quote_context()

    return render_template(
        'review.html',
        review_data=review_data,
        TITLE_MAPPING=TITLE_MAPPING,
        line_code_labels=line_code_labels,
        **ctx
    )


@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    session['last_visited'] = 'calculator'
    context = {}
    template_key = session.get('template_key', 'standard_build')
    form_data = session.get('data', {})
    session_overrides = session.get('session_overrides', {})
    try:
        from calculator import calculate_quote
        context['result'] = calculate_quote(template_key, form_data, session_overrides)
    except Exception as exc:
        context['error'] = str(exc)
    return render_template('calculator.html', **context)


@app.route('/api/line-item/override', methods=['POST'])
@csrf.exempt
def api_line_item_override():
    data = request.get_json(force=True) or {}
    line_code = data.get('line_code', '').strip()
    unit_cost = data.get('unit_cost')
    scope = data.get('scope', 'project')

    if not line_code or unit_cost is None:
        return jsonify({'success': False, 'error': 'line_code and unit_cost are required'}), 400

    try:
        unit_cost = float(unit_cost)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'unit_cost must be a number'}), 400

    db_path = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    row = conn.execute(
        "SELECT id FROM line_items WHERE line_code = ? LIMIT 1",
        (line_code,),
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'success': False, 'error': f'Line item {line_code} not found'}), 404

    item_id = row['id']

    if scope == 'db':
        if session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Admin role required to update DB defaults'}), 403
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE line_items SET unit_cost = ? WHERE id = ?",
            (unit_cost, item_id),
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'scope': 'db', 'line_code': line_code, 'unit_cost': unit_cost})

    session_overrides = session.setdefault('session_overrides', {})
    overrides = session_overrides.setdefault('overrides', {})
    overrides[str(item_id)] = unit_cost
    session.modified = True
    return jsonify({'success': True, 'scope': 'project', 'line_code': line_code, 'unit_cost': unit_cost})


@app.route('/quote_editor', methods=['GET', 'POST'])
def quote_editor():
    session['last_visited'] = 'quote_editor'
    form_key = session.get('template_key', 'builder_beta')
    layouts = []
    try:
        from template_store import list_quote_editor_layouts
        layouts = list_quote_editor_layouts(form_key)
    except Exception:
        pass
    pending_blocks = session.pop('quote_editor_pending_blocks', [])
    pending_block = session.pop('quote_editor_pending_block', None)
    return render_template(
        'user_output_editor.html',
        form_key=form_key,
        layouts=layouts,
        pending_blocks=pending_blocks,
        pending_block=pending_block,
    )


@app.route('/save-load', methods=['GET', 'POST'])
def save_load():
    session['last_visited'] = 'save_load'
    db_path = str(Path(__file__).parent / 'template_store.sqlite3')
    saved = False
    loaded = False
    error = None
    saved_sessions = []
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS saved_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            session_data TEXT NOT NULL,
            user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'save':
            save_name = request.form.get('save_name', '').strip()
            if not save_name:
                error = 'Session name is required.'
            else:
                data_to_save = {
                    'data': session.get('data', {}),
                    'checkbox_data': session.get('checkbox_data', {}),
                    'session_overrides': session.get('session_overrides', {}),
                    'template_key': session.get('template_key'),
                }
                try:
                    conn.execute(
                        'INSERT INTO saved_sessions (name, session_data, user_id) VALUES (?, ?, ?)',
                        (save_name, json.dumps(data_to_save), session.get('user_id'))
                    )
                    conn.commit()
                    saved = True
                except Exception as exc:
                    error = str(exc)
        elif action == 'load':
            session_id = request.form.get('session_id')
            if session_id:
                row = conn.execute(
                    'SELECT id, session_data FROM saved_sessions WHERE id = ?', (session_id,)
                ).fetchone()
                if row:
                    try:
                        loaded_data = json.loads(row['session_data'])
                        session['data'] = loaded_data.get('data', {})
                        session['checkbox_data'] = loaded_data.get('checkbox_data', {})
                        session['session_overrides'] = loaded_data.get('session_overrides', {})
                        if loaded_data.get('template_key'):
                            session['template_key'] = loaded_data['template_key']
                        session.modified = True
                        loaded = True
                    except Exception as exc:
                        error = str(exc)
    conn.close()

    conn = sqlite3.connect(db_path)
    rows = conn.execute('SELECT id, name, created_at FROM saved_sessions ORDER BY created_at DESC').fetchall()
    conn.close()
    for row in rows:
        saved_sessions.append({'id': row[0], 'name': row[1], 'created_at': row[2]})

    return render_template(
        'save_load.html',
        saved=saved,
        loaded=loaded,
        error=error,
        saved_sessions=saved_sessions,
    )


from quote_editor_routes import quote_editor_bp
from quote_editor_export import quote_editor_export_bp
from export_routes import export_bp

app.register_blueprint(quote_editor_bp)
app.register_blueprint(quote_editor_export_bp)
app.register_blueprint(export_bp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)