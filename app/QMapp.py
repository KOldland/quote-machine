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
    get_question_images_for_line_item,
)


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


def _get_latest_version_id(conn, template_key):
    row = conn.execute(
        """
        SELECT ftv.id
        FROM form_template_versions ftv
        JOIN form_templates ft ON ft.id = ftv.form_template_id
        WHERE ft.key = ?
        ORDER BY ftv.version DESC
        LIMIT 1
        """,
        (template_key,),
    ).fetchone()
    return int(row[0]) if row else None


def _remove_category_from_payload(conn, version_id, page_key, category_name):
    row = conn.execute(
        "SELECT payload_json FROM form_template_versions WHERE id = ?",
        (version_id,),
    ).fetchone()
    if not row:
        return
    try:
        payload = json.loads(row[0])
    except Exception:
        return
    pages = payload.get("builder_beta", {}).get("pages", payload.get("pages", {}))
    page = pages.get(page_key)
    if not isinstance(page, dict):
        return
    cats = page.get("categories", [])
    if not isinstance(cats, list):
        return
    new_cats = [c for c in cats if not (isinstance(c, dict) and c.get("name") == category_name)]
    if len(new_cats) != len(cats):
        page["categories"] = new_cats
        conn.execute(
            "UPDATE form_template_versions SET payload_json = ? WHERE id = ?",
            (json.dumps(payload, sort_keys=True), version_id),
        )


def _move_category_in_payload(conn, version_id, source_page_key, target_page_key, category_name):
    row = conn.execute(
        "SELECT payload_json FROM form_template_versions WHERE id = ?",
        (version_id,),
    ).fetchone()
    if not row:
        return
    try:
        payload = json.loads(row[0])
    except Exception:
        return
    pages = payload.get("builder_beta", {}).get("pages", payload.get("pages", {}))
    source_page = pages.get(source_page_key)
    target_page = pages.get(target_page_key)
    if not isinstance(source_page, dict) or not isinstance(target_page, dict):
        return
    source_cats = source_page.get("categories", [])
    target_cats = target_page.get("categories", [])
    if not isinstance(source_cats, list) or not isinstance(target_cats, list):
        return
    moved = None
    new_source = []
    for c in source_cats:
        if isinstance(c, dict) and c.get("name") == category_name:
            moved = dict(c)
        else:
            new_source.append(c)
    if moved is None:
        return
    source_page["categories"] = new_source
    target_cats.append(moved)
    target_page["categories"] = target_cats
    conn.execute(
        "UPDATE form_template_versions SET payload_json = ? WHERE id = ?",
        (json.dumps(payload, sort_keys=True), version_id),
    )


def _rebuild_payload_from_db(conn, template_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    if conn is None:
        conn = _get_conn()
    
    latest_version_id = _get_latest_version_id(conn, template_key)
    if not latest_version_id:
        return None
    pages_rows = conn.execute(
        "SELECT id, page_key, title, display_order FROM page_templates WHERE form_template_version_id = ? ORDER BY display_order ASC",
        (latest_version_id,),
    ).fetchall()
    pages = {}
    for page_row in pages_rows:
        page_id = page_row["id"]
        page_key = page_row["page_key"]
        cats = conn.execute(
            "SELECT name, display_order, output_group FROM category_templates WHERE page_template_id = ? ORDER BY display_order ASC",
            (page_id,),
        ).fetchall()
        questions = conn.execute(
            "SELECT question_key, question_type, label, storage_key, display_order, metadata_json FROM question_templates WHERE page_template_id = ? ORDER BY display_order ASC",
            (page_id,),
        ).fetchall()
        blocks = []
        for q in questions:
            try:
                meta = json.loads(q["metadata_json"])
            except Exception:
                meta = {"id": q["question_key"], "block_type": q["question_type"], "label": q["label"] or "", "storage": {"key": q["storage_key"] or q["question_key"]}}
            blocks.append(meta)
        pages[page_key] = {
            "title": page_row["title"],
            "categories": [
                {"name": c["name"], "sort_order": c["display_order"], "output_group": c["output_group"]}
                for c in cats
            ],
            "blocks": blocks,
        }
    return {"builder_beta": {"pages": pages}}
from config import (
    TEMPLATE_STORE_READ_ENABLED,
    TEMPLATE_STORE_KEY,
    TEMPLATE_STORE_DB_PATH,
    FLASK_SECRET_KEY,
)

app = Flask(__name__)
csrf = CSRFProtect(app)

# ── Database connection helper (SQLite local / PostgreSQL on Render) ──
# CRITICAL: Always use ? placeholders in SQL strings.
# The _CompatConnection adapter converts ? to %s for PostgreSQL.
# Never use $1, $2, etc. - breaks SQLite compatibility.
def _get_conn(db_path=None):
    """Return a DB connection via template_store._connect().
    On Render (DATABASE_URL set) this uses PostgreSQL; locally it uses SQLite."""
    import template_store as _ts_conn
    return _ts_conn._connect(db_path)

@app.template_filter('from_json')
def from_json_filter(s):
    import json
    try:
        return json.loads(s)
    except Exception:
        return {}

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


@app.before_request
def require_login():
    # List of endpoints that do not require login
    public_endpoints = ['login', 'logout', 'static']
    # Ignore favicon requests - they shouldn't trigger login redirect or
    # overwrite the _login_next session variable
    if request.path == '/favicon.ico':
        return
    if request.endpoint not in public_endpoints and not session.get('role'):
        session['_login_next'] = request.url
        flash('Please log in to access that page.', 'warning')
        return redirect(url_for('login'))


@app.before_request
def set_quote_editor_active():
    """Set session flag indicating if we are in quote editor mode."""
    if request.endpoint and request.endpoint.startswith('quote_editor'):
        session['quote_editor_active'] = True
    else:
        session['quote_editor_active'] = False


# Define upload folder path
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB total (if batch)
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the filesystem
app.config['SESSION_FILE_DIR'] = str(Path(__file__).parent / 'flask_session')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Ensure cookies are sent with same-origin AJAX
app.config['SECRET_KEY'] = os.getenv(
    'QM_SECRET_KEY', 'dev-insecure-key-change-me')
app.config['WTF_CSRF_TIME_LIMIT'] = 86400

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

    # "Where was I?" — carry the last visited form page across mode switches
    # so Build ⇄ Form navigation returns the user to the same page.
    _page_keys = {p['page_key'] for p in db_pages}
    _lv = session.get('last_visited')
    last_visited = _lv if _lv in _page_keys and _lv != 'index' else None

    return dict(
        current_user_role=role,
        current_username=session.get('username'),
        is_admin=is_admin,
        edit_mode=edit_mode,
        db_pages=db_pages,
        last_visited=last_visited,
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
    """Return list of category objects for a page from the template store.
    Each object has name, display_order, output_group, is_cost_group, etc.
    Falls back to keys from get_line_items_for_page()."""
    try:
        items = get_line_items_for_page(page_id)
        cat_names = list(items.keys()) if items else []
    except Exception:
        cat_names = []
    # Query category_templates directly for is_cost_group data
    try:
        from template_store import _default_db_path, _connect
        db = _default_db_path()
        conn = _connect(db)
        rows = conn.execute(
            """SELECT ct.name, ct.display_order, ct.output_group, ct.is_cost_group,
                      ct.cost_group_override_allowed, ct.image_url, ct.description,
                      ct.is_module, ct.module_type
               FROM category_templates ct
               JOIN page_templates pt ON pt.id = ct.page_template_id
               JOIN form_template_versions ftv ON ftv.id = ct.form_template_version_id
               WHERE pt.page_key = ?
               ORDER BY ct.display_order ASC""",
            (page_id,)
        ).fetchall()
        conn.close()
        cat_dict = {r['name']: dict(r) for r in rows}
        result = []
        for name in cat_names:
            if name in cat_dict:
                result.append(cat_dict[name])
            else:
                result.append({'name': name, 'is_cost_group': 0, 'output_group': 'General', 'display_order': 0})
        result.sort(key=lambda x: x.get('display_order', 0))
        # Strip any stale rows whose name matches a known module type
        _MODULE_TYPE_NAMES = {'page_total', 'payment_schedule', 'image_upload'}
        result = [r for r in result if r.get('name') not in _MODULE_TYPE_NAMES]
        # Also remove cost group sections — they are now blocks in
        # page_schemas.json and rendered via the module injection JS.
        result = [r for r in result if not r.get('is_cost_group')]
        return result
    except Exception:
        pass
    # Fallback: return just names
    return [{'name': n, 'is_cost_group': 0, 'output_group': 'General', 'display_order': 0} for n in cat_names]


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
            conn = _get_conn(db_path)
            
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
            conn = _get_conn(db_path)
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
    # Also update the stored payload_json so load_template_payload() returns
    # the current state (including module blocks that live only in the JSON).
    # initialize_template_store skips seeding when a version already exists,
    # so we patch the JSON payload in the existing version directly.
    try:
        import sqlite3
        from pathlib import Path
        _db = str(Path(__file__).parent / 'template_store.sqlite3')
        _conn = _get_conn()
        _row = _conn.execute(
            "SELECT ftv.id FROM form_template_versions ftv "
            "JOIN form_templates ft ON ft.id = ftv.form_template_id "
            "WHERE ft.key = ? ORDER BY ftv.version DESC LIMIT 1",
            (TEMPLATE_STORE_KEY,)
        ).fetchone()
        if _row:
            _conn.execute(
                "UPDATE form_template_versions SET payload_json = ? WHERE id = ?",
                (json.dumps(page_schemas), _row[0])
            )
            _conn.commit()
        _conn.close()
    except Exception as exc:
        print(f"Payload JSON sync skipped: {exc}")


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
        conn = _get_conn(db_path)
        
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
        conn = _get_conn(db_path)
        
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
    'textarea_input': {
        'label': 'Larger Text Box',
        'default_label': 'New larger text box',
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
    'calculator': {
        'label': 'Calculator',
        'default_label': 'New calculator',
        'supports': {'logic': True, 'pricing': True, 'output': True},
        'icon': '#',
        'description': 'Cost group breakdown with editable quantities — ideal for pricing pages',
    },
    'payment_schedule': {
        'label': 'Payment Schedule',
        'default_label': 'Payment Schedule',
        'supports': {'logic': False, 'pricing': False, 'output': True},
        'icon': '$',
        'description': 'Payment schedule breakdown based on quote totals — shows deposit, stage payments, and completion amounts',
    },
    'page_total': {
        'label': 'Page Total',
        'default_label': 'Page Total',
        'supports': {'logic': False, 'pricing': False, 'output': True},
        'icon': 'Σ',
        'description': 'Totals one or more cost groups on this page',
    },
}

ALLOWED_BLOCK_PRICING_MODES = {
    'none',
    'fixed',
    'entered',
    'quantity_rate',
    'percent_subtotal',
    'matrix',
    'calculator'
}

# Default cost groups with metadata (similar to question types)
DEFAULT_BUILDER_BETA_COST_GROUPS = {
    'general': {
        'label': 'General',
        'default_label': 'General',
        'description': 'Default cost group for unclassified items',
        'sort_order': 0
    }
}


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
        question_types = state['question_types']
    for k, v in DEFAULT_BUILDER_BETA_QUESTION_TYPES.items():
        question_types.setdefault(k, deepcopy(v))

    # 4️⃣① Load/initialise cost group definitions
    cost_groups = state.get('cost_groups')
    if not isinstance(cost_groups, dict):
        state['cost_groups'] = deepcopy(DEFAULT_BUILDER_BETA_COST_GROUPS)
        cost_groups = state['cost_groups']
    for k, v in DEFAULT_BUILDER_BETA_COST_GROUPS.items():
        cost_groups.setdefault(k, deepcopy(v))

    # 5️⃣  Load the *pages* from the schema – this is the crucial part.
    #     If the schema contains a 'pages' mapping we honour it; otherwise we
    #     fall back to an empty dict (so the UI still works but is empty).
    schema_pages = page_schemas.get('pages', {})
    if isinstance(schema_pages, dict):
        pages = deepcopy(schema_pages)
    else:
        pages = {}

    # 6️⃣  Ensure the 'pages' key exists in the state and that each page
    #     has the required keys (id, title, navigation, blocks).
    #     Only use state.get('pages') if it has actual content; otherwise
    #     keep the pages from schema_pages above.
    state_pages = state.get('pages', {})
    if isinstance(state_pages, dict) and state_pages:
        # deepcopy: `state` is a shallow copy of the module-level
        # page_schemas, so without this the DB-merge below would mutate the
        # shared seed object in place and compound on every call.
        pages = deepcopy(state_pages)
    # else: keep pages from schema_pages (already set above)

    # Populate any missing defaults for each page.
    for pid, pg in pages.items():
        pg.setdefault('id', pid)
        pg.setdefault('title', pid.replace('_', ' ').title())
        pg.setdefault('navigation', {})
        if not isinstance(pg.get('blocks'), list):
            pg['blocks'] = []   # make sure a list exists

    # Make SQLite authoritative for page *content* (title, categories, blocks).
    #
    # The builder used to read pages straight from page_schemas.json, a legacy
    # seed file that is also re-seeded from the versioned payload_json at import.
    # That made it a second source of truth: a category renamed or page merged in
    # SQLite left the old entry behind, because the sync below only ever appended.
    # _rebuild_payload_from_db() derives the same structure from page_templates /
    # category_templates / question_templates, so prefer it.
    #
    # Navigation is the exception: previous/next endpoints are only populated in
    # the JSON seed (the page_templates columns are empty for the live version),
    # so carry it across rather than dropping the Save & Continue chain.
    try:
        _db_state = _rebuild_payload_from_db(conn=None, template_key=TEMPLATE_STORE_KEY)
        _db_pages = (_db_state or {}).get('builder_beta', {}).get('pages') or {}
        for _pid, _pg in _db_pages.items():
            if not isinstance(_pg, dict):
                continue
            _pg.setdefault('id', _pid)
            _pg.setdefault('navigation', (pages.get(_pid) or {}).get('navigation') or {})
            # Preserve any blocks from the JSON page that do not exist in the
            # DB-derived page.  Module blocks (page_total, payment_schedule,
            # image_upload, …) live only in page_schemas.json, not in the
            # SQLite question_templates, and would otherwise be lost.
            _json_blocks = (pages.get(_pid) or {}).get('blocks') or []
            _db_blocks = _pg.get('blocks') or []
            # Preserve the JSON payload block ORDER — the same list that the
            # builder swap/reorder admin actions mutate — while preferring DB
            # block content where a matching id exists. Previously the merge
            # emitted DB blocks first then appended JSON blocks, which reversed
            # module blocks (payment_schedule / page_total / cost_group_section)
            # relative to the payload so swaps appeared not to move in the UI.
            _db_by_id = {}
            for _dbb in _db_blocks:
                if _dbb.get('id'):
                    _db_by_id[_dbb['id']] = _dbb
            _merged_blocks = []
            _used_db = set()
            for _jb in _json_blocks:
                _jid = _jb.get('id')
                if _jid and _jid in _db_by_id:
                    _merged_blocks.append(deepcopy(_db_by_id[_jid]))
                    _used_db.add(_jid)
                else:
                    _merged_blocks.append(deepcopy(_jb))
            # Append any DB-only blocks (e.g. questions added straight to DB)
            for _dbb in _db_blocks:
                if _dbb.get('id') and _dbb['id'] not in _used_db:
                    _merged_blocks.append(deepcopy(_dbb))
            if _merged_blocks:
                _pg['blocks'] = _merged_blocks
            if not isinstance(_pg.get('blocks'), list):
                _pg['blocks'] = []
            pages[_pid] = _pg
    except Exception:
        pass

    # Inject display_order from SQLite so navigation can use it as single source of truth.
    # Also ensure any pages that exist in the DB but not in the JSON schema are included
    # (e.g. pages added via the Add Page modal).
    try:
        ordered_pages = get_all_pages(template_key=TEMPLATE_STORE_KEY)
        for pg in ordered_pages:
            pid = pg['page_key']
            if pid in pages:
                pages[pid]['display_order'] = pg['display_order']
            else:
                pages[pid] = {
                    'title': pg.get('title', pid.replace('_', ' ').title()),
                    'blocks': [],
                    'categories': [],
                    'display_order': pg.get('display_order', 999),
                }
        pages = dict(sorted(pages.items(), key=lambda x: x[1].get('display_order', 999)))
        state['pages'] = pages
    except Exception:
        pass

    # Ensure any categories that exist in the DB but not in the JSON schema
    # are visible in BUILD MODE (e.g. categories added via add_category).
    try:
        import sqlite3 as _sqlite3  # kept for Row type
        from pathlib import Path as _Path
        _db_path = _Path(__file__).parent / 'template_store.sqlite3'
        if _db_path.exists():
            _conn = _get_conn(_db_path)
            _rows = _conn.execute(
                "SELECT pt.page_key, ct.name, ct.display_order, ct.description, ct.output_group "
                "FROM category_templates ct "
                "JOIN page_templates pt ON pt.id = ct.page_template_id "
                "WHERE pt.form_template_version_id = ("
                "  SELECT MAX(ftv.id) FROM form_template_versions ftv "
                "  JOIN form_templates ft ON ft.id = ftv.form_template_id "
                "  WHERE ft.key = ?"
                ") "
                "ORDER BY pt.display_order ASC, ct.display_order ASC",
                (TEMPLATE_STORE_KEY,)
            ).fetchall()
            _conn.close()
            # DB is authoritative for categories. Previously this only *appended*
            # DB rows that were missing from the JSON seed, which meant a category
            # renamed in SQLite left a phantom behind (e.g. stale "Standard Item"
            # from the versioned payload_json alongside the real "Standard Items").
            # Replace the list wherever the DB actually has rows, and keep the JSON
            # seed only for pages the DB knows nothing about.
            _by_page: dict[str, list[dict]] = {}
            for _r in _rows:
                _by_page.setdefault(_r['page_key'], []).append({
                    'name': _r['name'],
                    'sort_order': _r['display_order'],
                    'description': _r['description'] or '',
                    'output_group': _r['output_group'] or 'General',
                })
            for _pid, _cats in _by_page.items():
                if _pid not in pages:
                    continue
                pages[_pid]['categories'] = _cats
    except Exception:
        pass

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
            'selection_limit': None,
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
            standard['static_content'] = (form_data.get('standard_static_content') or standard.get('standard_content', '')).strip()

            # Cost group total block fields
            standard['cost_group_id'] = form_data.get('cost_group_id', '') or ''
            raw_override = form_data.get('cost_group_override', '')
            if raw_override and str(raw_override).strip():
                try:
                    standard['cost_group_override'] = float(raw_override)
                except (TypeError, ValueError):
                    standard['cost_group_override'] = ''
            else:
                standard['cost_group_override'] = ''

            raw_choices = form_data.get('standard_dropdown_choices', '')
            if isinstance(raw_choices, str):
                standard['dropdown_choices'] = [
                    c.strip() for c in raw_choices.splitlines() if c.strip()]
            # Calculator: support both checkbox multi-select and legacy textarea
            calc_checkbox_values = form_data.getlist('calculator_groups')
            if calc_checkbox_values:
                standard['calculator_groups'] = list(dict.fromkeys(calc_checkbox_values))
            else:
                raw_calculator_groups = form_data.get('standard_calculator_groups', '')
                if isinstance(raw_calculator_groups, str):
                    standard['calculator_groups'] = [
                        g.strip() for g in raw_calculator_groups.splitlines() if g.strip()]

            raw_selection_limit = form_data.get('standard_selection_limit')
            if raw_selection_limit is not None and str(raw_selection_limit).strip() != '':
                try:
                    standard['selection_limit'] = int(raw_selection_limit)
                except (TypeError, ValueError):
                    standard['selection_limit'] = None
            else:
                standard['selection_limit'] = None

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
            pricing_options['addon_amount'] = _parse_builder_float(
                form_data.get('pricing_addon_amount'), pricing_options.get('addon_amount', 0.0), 0, 1000000)
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

            if pricing_mode == 'matrix':
                matrix_types = form_data.get('pricing_matrix_types', '')
                matrix_sizes = form_data.get('pricing_matrix_sizes', '')
                matrix_prices_raw = form_data.get('pricing_matrix_prices', '')
                types_list = [t.strip() for t in (matrix_types or '').splitlines() if t.strip()]
                sizes_list = [s.strip() for s in (matrix_sizes or '').splitlines() if s.strip()]
                prices_list = []
                if matrix_prices_raw:
                    try:
                        parsed = json.loads(matrix_prices_raw)
                        if isinstance(parsed, list):
                            prices_list = parsed
                    except Exception:
                        prices_list = []
                pricing_options['matrix_types'] = types_list
                pricing_options['matrix_sizes'] = sizes_list
                pricing_options['matrix_prices'] = prices_list
                if types_list and sizes_list and prices_list and len(prices_list) == len(types_list):
                    pricing_options['price_matrix'] = {
                        'types': types_list,
                        'sizes': sizes_list,
                        'prices': prices_list
                    }
                else:
                    pricing_options['price_matrix'] = {'types': types_list, 'sizes': sizes_list, 'prices': prices_list}
            else:
                pricing_options.pop('price_matrix', None)
                pricing_options.pop('matrix_types', None)
                pricing_options.pop('matrix_sizes', None)
                pricing_options.pop('matrix_prices', None)

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
                'selection_limit': standard.get('selection_limit'),
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
        elif block_type in ('page_total', 'payment_schedule', 'image_upload', 'cost_group_section'):
            # Module blocks and cost-group section blocks — include at
            # their natural position in the blocks list
            field_entry = {
                **common_payload,
                'type': block_type,
                'label': field_label,
                'config': deepcopy(block.get('config', {})),
            }
            # For cost_group_section, inject metadata the template expects
            if block_type == 'cost_group_section':
                _cfg = block.get('config', {})
                field_entry.setdefault('builder_beta_meta', {})['cost_group_id'] = _cfg.get('cost_group_id', '')
                field_entry.setdefault('builder_beta_meta', {})['override_allowed'] = bool(_cfg.get('override_allowed', False))
            compiled_fields.append(field_entry)
        else:
            # Renders by block_type in the form templates, so pass the real
            # label through. A "[beta:<type>]" marker was used here to flag
            # unhandled block types while migrating off the legacy schema,
            # but it leaked into customer-facing output.
            compiled_fields.append({
                **common_payload,
                'type': block_type,
                'label': field_label,
            })

    # Fallback: a page with no blocks still needs to render its line items in
    # the form. Some pages (created before blocks existed, or edited purely
    # through the builder UI) have line_items in SQLite but no blocks and no
    # category_templates rows at all — keying this off `categories` alone
    # missed those. Detect from the line items themselves, which is the same
    # source the form view uses to render them.
    if not compiled_fields:
        try:
            _li_rows = _get_line_items_for_page(page_id) or {}
            _li_total = sum(len(v) for v in _li_rows.values())
        except Exception:
            _li_total = 0
        if _li_total:
            compiled_fields.append({
                'id': page_id + '_auto_li',
                'name': page_id + '_line_items',
                'label': page.get('title', page_id.replace('_', ' ').title()),
                'note': '',
                'hidden': False,
                'type': 'line_items_by_category',
                'builder_beta_meta': {
                    'block_type': 'line_items_by_category',
                    'placeholder': '',
                    'dropdown_choices': [],
                    'selection_limit': None,
                    'static_content': '',
                    'static_variant': 'body',
                    'logic_options': {},
                    'pricing_options': {},
                    'output_options': {},
                },
                'config': {'page_key': page_id},
            })


    return {
        'id': page_id,
        'title': page.get('title', page_id.replace('_', ' ').title()),
        'navigation': deepcopy(page.get('navigation', {})),
        'fields': compiled_fields,
    }

def _apply_conditional_visibility(page_schema, form_data, checkbox_data):
    field_hidden = {}
    for field in page_schema.get('fields', []):
        meta = field.get('builder_beta_meta', {})
        logic = meta.get('logic_options', {})
        if logic.get('visibility') != 'conditional':
            continue
        depends_on = logic.get('depends_on_field', '')
        required_value = logic.get('depends_on_value', '')
        if not depends_on:
            field['hidden'] = True
            field_hidden[field.get('id')] = True
            continue
        if field_hidden.get(depends_on, False):
            field['hidden'] = True
            field_hidden[field.get('id')] = True
            continue
        current_value = ''
        cb_val = checkbox_data.get(depends_on)
        if isinstance(cb_val, dict):
            current_value = cb_val.get('preselected', [])
        elif cb_val is not None:
            current_value = str(cb_val)
        else:
            current_value = str(form_data.get(depends_on, ''))
        if isinstance(current_value, list):
            field['hidden'] = str(required_value).strip() not in [str(v).strip() for v in current_value]
        else:
            field['hidden'] = str(current_value).strip() != str(required_value).strip()
        field_hidden[field.get('id')] = field['hidden']


def resolve_builder_beta_navigation_targets(page_id, runtime_page):
    state = get_builder_beta_state()
    pages = state.get('pages', {})

    # Build ordered page list from display_order (single source of truth)
    page_order = []
    for pid, pg in pages.items():
        order = pg.get('display_order')
        if order is not None:
            page_order.append((order, pid))
    page_order.sort()

    page_ids = [pid for _, pid in page_order]

    if page_id in page_ids:
        idx = page_ids.index(page_id)
        previous_page_id = page_ids[idx - 1] if idx > 0 else None
        next_page_id = page_ids[idx + 1] if idx < len(page_ids) - 1 else None
    else:
        previous_page_id = None
        next_page_id = None

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
        import sqlite3 as _sqlite3  # kept for Row type
        db_path = os.path.join(
            os.path.dirname(__file__),
            'template_store.sqlite3')
        conn = _get_conn(db_path)
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
    conn = _get_conn()
    
    # Get latest version id
    latest_version_row = conn.execute(
        """
        SELECT ftv.id
        FROM form_template_versions ftv
        JOIN form_templates ft ON ft.id = ftv.form_template_id
        WHERE ft.key = ?
        ORDER BY ftv.version DESC
        LIMIT 1
        """,
        (TEMPLATE_STORE_KEY,)
    ).fetchone()
    latest_version_id = int(latest_version_row[0]) if latest_version_row else None
    if latest_version_id is None:
        conn.close()
        return jsonify({})
    row = conn.execute(
        "SELECT title, description, metadata_json FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
        [page_key, latest_version_id]).fetchone()
    conn.close()
    if row:
        result = dict(row)
        # Extract visibility flags from metadata_json
        meta = {}
        try:
            import json as _j
            meta = _j.loads(result.pop('metadata_json', '{}'))
        except Exception:
            meta = {}
        result['form_visible'] = meta.get('form_visible', True)
        result['quote_visible'] = meta.get('quote_visible', True)
        result['title'] = meta.get('title', result['title'])
        result['modules'] = meta.get('modules', [])
        result['page_total'] = meta.get('page_total', {})
        result['image_upload'] = meta.get('image_upload', {})
        return jsonify(result)
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


@app.route('/builder_beta/load_form', methods=['POST'])
@require_role('admin')
def load_form_route():
    import template_store as ts
    data = request.json
    form_key = data.get('form_key')

    if not form_key:
        return jsonify({'success': False, 'error': 'Form key is required'}), 400

    try:
        # Try loading from template store first
        payload = ts.load_template_payload(form_key)
        if payload:
            pages = payload.get('builder_beta', {}).get('pages', payload.get('pages', {}))
            if pages:
                page_schemas['builder_beta'] = copy.deepcopy(pages)
                save_page_schemas()
                return jsonify({'success': True})
        
        # Fallback to in-memory page_schemas
        if form_key in page_schemas:
            page_schemas['builder_beta'] = copy.deepcopy(page_schemas[form_key])
            save_page_schemas()
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/builder_beta/templates')
@require_role('admin')
def builder_templates():
    if request.args.get('edit', '0') != '1':
        return redirect(url_for('form_editor', edit=1))
    return render_template('builder_templates.html')


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
@app.route('/admin/payment-schedule', methods=['POST'])
@require_role('admin')
def admin_payment_schedule():
    """Save payment schedule settings from builder module config."""
    import template_store as ts
    settings = ts.get_payment_schedule_block('builder_beta')

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
    deposit_enabled = bool(data.get('deposit_enabled', settings.get('deposit_enabled', True)))
    completion_enabled = bool(data.get('completion_enabled', settings.get('completion_enabled', True)))
    initial_payment_enabled = bool(data.get('initial_payment_enabled', settings.get('initial_payment_enabled', True)))
    initial_payment_rounding = str(data.get('initial_payment_rounding', settings.get('initial_payment_rounding', 'none')))
    initial_payment_floors = data.get('initial_payment_floors', settings.get('initial_payment_floors'))
    weekly_payment_auto = bool(data.get('weekly_payment_auto', settings.get('weekly_payment_auto', True)))
    show_temp_kitchen = bool(data.get('show_temp_kitchen', settings.get('show_temp_kitchen', True)))
    show_glazing = bool(data.get('show_glazing', settings.get('show_glazing', True)))
    groups = data.get('groups', settings.get('groups', []))

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
        deposit_enabled=deposit_enabled,
        completion_enabled=completion_enabled,
        initial_payment_enabled=initial_payment_enabled,
        initial_payment_rounding=initial_payment_rounding,
        initial_payment_floors=initial_payment_floors,
        weekly_payment_auto=weekly_payment_auto,
        show_temp_kitchen=show_temp_kitchen,
        show_glazing=show_glazing,
        groups=groups,
    )
    return jsonify({'success': True})


@app.route('/admin/payment-schedule-data')
@require_role('admin')
def admin_payment_schedule_data():
    import template_store as ts
    settings = ts.get_payment_schedule_block('builder_beta')
    return jsonify({'success': True, 'settings': settings})

@app.route('/builder_beta/payment_schedule_preview', methods=['POST'])
@csrf.exempt
def builder_payment_schedule_preview():
    """Compute payment schedule preview for FORM MODE."""
    import template_store as ts
    import calculator as calc
    import re
    import sqlite3
    from pathlib import Path
    data = request.get_json(force=True) or {}
    basic_build = float(data.get('basic_build', 0))
    # If no basic_build provided, compute it from the given page_key + groups
    if basic_build <= 0:
        page_key = data.get('page_key', '')
        groups = data.get('groups', [])
        if page_key and groups:
            db = str(Path(__file__).parent / 'template_store.sqlite3')
            conn = _get_conn()
            
            try:
                totals = _compute_cost_group_totals(groups, conn, session)
                basic_build = round(sum(totals.get(g, 0) for g in groups), 2)
            finally:
                conn.close()
    weekly_count = int(data.get('weekly_count', 4))
    has_temp_kitchen = bool(data.get('has_temp_kitchen', True))
    has_glazing = bool(data.get('has_glazing', False))
    sow_levels = data.get('sow_levels')
    ps = ts.get_payment_schedule_block('builder_beta')
    
    # If sow_levels not provided by frontend, extract from session checkbox_data
    if not sow_levels:
        try:
            cb_data = (session.get('checkbox_data', {}) or {})
            _all_checked = set()
            for _key, _val in cb_data.items():
                if _key.endswith('__line_items') and isinstance(_val, dict):
                    _ps = _val.get('preselected')
                    if isinstance(_ps, list):
                        _all_checked.update(_ps)
            # Parse SOW week levels from checked line codes (pattern: sww<level><task>^)
            _sow_nums = []
            for _code in _all_checked:
                _m = re.match(r'sww(\d+)', _code)
                if _m:
                    _sow_nums.append(int(_m.group(1)))
            if _sow_nums:
                sow_levels = _sow_nums
        except Exception:
            pass
    
    # If sow_levels provided and auto is on, override weekly_count
    weekly_auto = bool(ps.get('weekly_payment_auto', True))
    if weekly_auto and sow_levels and isinstance(sow_levels, list) and len(sow_levels) > 0:
        nums = [int(s) for s in sow_levels if s is not None]
        if nums:
            weekly_count = max(nums)
    weekly_count = max(weekly_count, 1)
    
    # Compute initial payment with multi-floor support
    initial_pct = float(ps.get('initial_payment_pct', 0.05))
    raw_initial = round(basic_build * initial_pct, 2)
    floors = ps.get('initial_payment_floors', [])
    initial_payment = raw_initial
    if floors and isinstance(floors, list):
        for floor in floors:
            ceiling = float(floor.get('ceiling', 0))
            payment = float(floor.get('payment', 0))
            if basic_build <= ceiling:
                initial_payment = max(raw_initial, payment)
                break
        else:
            # Above all ceilings — use last floor's payment
            if floors:
                initial_payment = max(raw_initial, float(floors[-1].get('payment', 0)))
    # Rounding
    rounding = ps.get('initial_payment_rounding', 'none')
    if rounding == '100':
        initial_payment = round(initial_payment / 100) * 100
    elif rounding == '1000':
        initial_payment = round(initial_payment / 1000) * 1000

    # Total weekly slots = weekly_count (the 3rd Payment occupies one slot)
    # The 65% pool is split across (weekly_count - 1) of those slots
    remaining_weeks = max(weekly_count, 1)

    completion_pool_pct = float(ps.get('completion_meeting_plus_3rd_pct', 0.35))
    completion_pool = round(basic_build * completion_pool_pct, 2)  # 35% of total = IP + CM + 3rd
    pool_after_stages = round(basic_build - completion_pool, 2)  # remaining 65%

    temp_kitchen_cost = float(ps.get('temp_kitchen_cost', 250.0))
    glazing_cost = float(ps.get('glazing_cost', 500.0))

    # ── Rounding setting (from builder/admin config) ────────────
    ps_rounding = ps.get('initial_payment_rounding', 'none')

    def _round_amount(amt, rnd):
        if rnd == '100':
            return round(amt / 100) * 100
        elif rnd == '1000':
            return round(amt / 1000) * 1000
        return round(amt, 2)

    # ── 35% split: IP + CM + 3rd ──────────────────────────────────
    # CM and 3rd each get half of what remains after IP
    # 3rd Payment is listed as "3rd Payment" at its chronological position
    cm_each = round((completion_pool - initial_payment) / 2, 2) if completion_pool > initial_payment else 0
    third_payment = round(completion_pool - initial_payment - cm_each, 2) if completion_pool > initial_payment else 0

    # ── 65% pool: adjustments stay WITHIN the total ──────────────
    # If TK removal is needed, the £250 comes out of the weekly pool
    # and goes to the final settlement.  If glazing is needed, same.
    adjustments = 0.0
    if has_temp_kitchen:
        adjustments += temp_kitchen_cost
    if has_glazing:
        adjustments += glazing_cost
    weekly_pool = round(pool_after_stages - adjustments, 2)  # adjustments reduce the pool
    # Regular weekly amount, rounded per the builder setting
    raw_per_week = weekly_pool / remaining_weeks if remaining_weeks > 0 else 0
    regular_slots = remaining_weeks - 1  # slots that get the 65% pool (all except 3rd Payment)
    regular_weekly = _round_amount(weekly_pool / regular_slots, ps_rounding) if regular_slots > 0 else 0

    # ── Build schedule: IP, CM, then interleaved weeks + 3rd Payment ──
    # weeks BEFORE 3rd Payment: Week 1, Week 2
    # Week occupied by 3rd Payment
    # weeks AFTER 3rd Payment: Week 4 ... Week N  (last = final settlement)
    schedule = [
        {"stage": "Initial Payment", "amount": initial_payment, "note": ""},
        {"stage": "Commencement Meeting", "amount": cm_each, "note": ""},
    ]
    for i in range(1, remaining_weeks + 1):
        if i == remaining_weeks:
            # Last week = final settlement — absorbs ALL remainder
            last_amount = round(basic_build - sum(s['amount'] for s in schedule), 2)
            schedule.append({"stage": f"Week {i}", "amount": last_amount, "note": ""})
        elif i == 3:
            # 3rd Payment at its chronological position (week 3)
            schedule.append({"stage": "3rd Payment", "amount": third_payment, "note": ""})
        else:
            schedule.append({"stage": f"Week {i}", "amount": regular_weekly, "note": ""})
    
    return jsonify({
        'success': True,
        'basic_build': basic_build,
        'initial_payment': initial_payment,
        'completion_pool': completion_pool,
        'pool_after_stages': pool_after_stages,
        'schedule': schedule,
        'total': round(sum(s['amount'] for s in schedule), 2),
        'has_temp_kitchen': has_temp_kitchen,
        'has_glazing': has_glazing,
    })

@app.route('/session/clear', methods=['POST'])
@require_role('admin')
def session_clear():
    """Clear form/quote editing state from the session but stay logged in."""
    role = session.get('role')
    username = session.get('username')
    session.clear()
    session['role'] = role
    session['username'] = username
    session.modified = True
    return jsonify({'success': True})
@app.route('/builder_beta/line_item_move', methods=['POST'])
@require_role('admin')
def builder_line_item_move():
    """Move a question (line_item) to a different category, optionally on another page.

    Mirrors builder_category_move so both levels of the hierarchy behave the same.
    """
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    line_item_id = data.get('line_item_id')
    target_category = (data.get('target_category') or '').strip()
    source_page = data.get('page_key')
    target_page = (data.get('target_page_key') or source_page or '').strip()

    if not line_item_id or not target_category or not source_page or not target_page:
        return jsonify({'success': False,
                        'error': 'line_item_id, page_key and target_category are required'}), 400

    conn = _get_conn()
    
    try:
        item = conn.execute(
            "SELECT id, form_page, category, sort_order FROM line_items WHERE id = ?",
            [line_item_id]
        ).fetchone()
        if not item:
            return jsonify({'success': False, 'error': 'Question not found'}), 404

        latest_row = conn.execute(
            """
            SELECT ftv.id FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ? ORDER BY ftv.version DESC LIMIT 1
            """,
            (TEMPLATE_STORE_KEY,)
        ).fetchone()
        latest_version_id = int(latest_row[0]) if latest_row else None
        if latest_version_id is None:
            return jsonify({'success': False, 'error': 'Template version not found'}), 404

        target_page_row = conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
            [target_page, latest_version_id]
        ).fetchone()
        if not target_page_row:
            return jsonify({'success': False, 'error': 'Target page not found'}), 404

        target_cat_row = conn.execute(
            """SELECT ct.id FROM category_templates ct
               JOIN page_templates pt ON pt.id = ct.page_template_id
               WHERE pt.page_key = ? AND pt.form_template_version_id = ? AND ct.name = ?""",
            [target_page, latest_version_id, target_category]
        ).fetchone()
        if not target_cat_row:
            return jsonify({'success': False,
                            'error': f"Category '{target_category}' not found on the target page"}), 404

        # Land at the end of the target category so ordering stays predictable.
        max_order = conn.execute(
            "SELECT MAX(sort_order) AS m FROM line_items WHERE form_page = ? AND category = ?",
            [target_page, target_category]
        ).fetchone()['m']
        next_sort = (int(max_order) + 1) if max_order is not None else 0

        conn.execute(
            "UPDATE line_items SET form_page = ?, category = ?, sort_order = ? WHERE id = ?",
            [target_page, target_category, next_sort, line_item_id]
        )
        conn.commit()
        return jsonify({'success': True, 'category': target_category,
                        'form_page': target_page, 'sort_order': next_sort})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/page_details_save/<page_key>', methods=['POST'])
@require_role('admin')
def builder_page_details_save(page_key):
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    title = data.get('title', '')
    desc = data.get('description', '')
    form_visible = data.get('form_visible', True)
    quote_visible = data.get('quote_visible', True)
    conn = _get_conn()
    # Get latest version id
    latest_version_row = conn.execute(
        """
        SELECT ftv.id
        FROM form_template_versions ftv
        JOIN form_templates ft ON ft.id = ftv.form_template_id
        WHERE ft.key = ?
        ORDER BY ftv.version DESC
        LIMIT 1
        """,
        (TEMPLATE_STORE_KEY,)
    ).fetchone()
    latest_version_id = int(latest_version_row[0]) if latest_version_row else None
    if latest_version_id is None:
        conn.close()
        return jsonify({'ok': False, 'error': 'Template version not found'}), 404
    # Read existing metadata_json
    existing_row = conn.execute(
        "SELECT metadata_json FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
        [page_key, latest_version_id]).fetchone()
    meta = {}
    if existing_row and existing_row[0]:
        try:
            meta = json.loads(existing_row[0]) if isinstance(existing_row[0], str) else existing_row[0]
        except Exception:
            pass
@app.route('/builder_beta/page_modules_save/<page_key>', methods=['POST'])
@require_role('admin')
def builder_page_modules_save(page_key):
    """Save the list of enabled modules for a page."""
    import sqlite3
    from pathlib import Path
    import json as _j
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    modules = data.get('modules', [])
    if not isinstance(modules, list):
        return jsonify({'ok': False, 'error': 'modules must be a list'}), 400
    conn = _get_conn()
    lv = conn.execute("SELECT MAX(id) FROM form_template_versions WHERE form_template_id = (SELECT id FROM form_templates WHERE key = ?)", (TEMPLATE_STORE_KEY,)).fetchone()
    lid = int(lv[0]) if lv and lv[0] else None
    if not lid:
        conn.close()
        return jsonify({'ok': False, 'error': 'No version'}), 404
    existing = conn.execute("SELECT metadata_json FROM page_templates WHERE page_key = ? AND form_template_version_id = ?", [page_key, lid]).fetchone()
    meta = {}
    if existing and existing[0]:
        try: meta = _j.loads(existing[0]) if isinstance(existing[0], str) else existing[0]
        except: meta = {}
    if not isinstance(meta, dict): meta = {}
    meta['modules'] = modules
    conn.execute("UPDATE page_templates SET metadata_json = ? WHERE page_key = ? AND form_template_version_id = ?", [_j.dumps(meta), page_key, lid])
    conn.commit()
    conn.close()
    return jsonify({'ok': True})
    if not isinstance(meta, dict):
        meta = {}
    meta['form_visible'] = form_visible
    meta['quote_visible'] = quote_visible
    meta['title'] = title
    conn.execute(
        "UPDATE page_templates SET title = ?, description = ?, metadata_json = ? WHERE page_key = ? AND form_template_version_id = ?", [
            title, desc, json.dumps(meta), page_key, latest_version_id])
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/builder_beta/image_upload_save/<page_key>', methods=['POST'])
@require_role('admin')
def builder_image_upload_save(page_key):
    """Save image upload module config (which slot to display)."""
    import sqlite3
    from pathlib import Path
    import json as _j
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    slot = data.get('slot', 'cover_image')
    label = data.get('label', 'Uploaded Image')
    conn = _get_conn()
    lv = conn.execute("SELECT MAX(id) FROM form_template_versions WHERE form_template_id = (SELECT id FROM form_templates WHERE key = ?)", (TEMPLATE_STORE_KEY,)).fetchone()
    lid = int(lv[0]) if lv and lv[0] else None
    if not lid:
        conn.close()
        return jsonify({'ok': False, 'error': 'No version'}), 404
    existing = conn.execute("SELECT metadata_json FROM page_templates WHERE page_key = ? AND form_template_version_id = ?", [page_key, lid]).fetchone()
    meta = {}
    if existing and existing[0]:
        try: meta = _j.loads(existing[0]) if isinstance(existing[0], str) else existing[0]
        except: meta = {}
    if not isinstance(meta, dict): meta = {}
    meta['image_upload'] = {'slot': slot, 'label': label}
    conn.execute("UPDATE page_templates SET metadata_json = ? WHERE page_key = ? AND form_template_version_id = ?", [_j.dumps(meta), page_key, lid])
    conn.commit()
    conn.close()
    return jsonify({'ok': True})
@app.route('/builder_beta/page_total_calc', methods=['POST'])
@csrf.exempt
def builder_page_total_calc():
    """Calculate the total for selected cost groups on a page.
    Sums the per-group totals from the helper so it always matches the
    cost group accordion display (checked items only, with macro overrides).
    This endpoint is called from the form preview (customer-facing),
    so it must not require admin role."""
    import sqlite3
    from pathlib import Path
    import json as _j
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key', '')
    groups = data.get('groups', [])
    if not page_key or not groups:
        return jsonify({'success': False, 'error': 'page_key and groups required'}), 400
    conn = _get_conn()
    
    try:
        totals = _compute_cost_group_totals(groups, conn, session)
        selected_total = round(sum(totals.get(g, 0) for g in groups), 2)
        return jsonify({'success': True, 'total': selected_total, 'groups': groups, 'subtotals': dict(totals)})
    finally:
        conn.close()


@app.route('/builder_beta/cg_override_save', methods=['POST'])
@csrf.exempt
def builder_cg_override_save():
    """Save a cost group override to the session."""
    data = request.get_json(force=True) or {}
    cg_id = data.get('cg_id', '')
    value = data.get('value')
    if not cg_id or value is None:
        return jsonify({'ok': False, 'error': 'cg_id and value required'}), 400
    try:
        val = float(value)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Invalid value'}), 400
    session_overrides = session.setdefault('session_overrides', {})
    cg_overrides = session_overrides.setdefault('cg_overrides', {})
    cg_overrides[cg_id] = val
    session.modified = True
    return jsonify({'ok': True})

@app.route('/builder_beta/cg_override_revert', methods=['POST'])
@csrf.exempt
def builder_cg_override_revert():
    """Remove a cost group override from the session."""
    data = request.get_json(force=True) or {}
    cg_id = data.get('cg_id', '')
    if not cg_id:
        return jsonify({'ok': False, 'error': 'cg_id required'}), 400
    session_overrides = session.setdefault('session_overrides', {})
    cg_overrides = session_overrides.setdefault('cg_overrides', {})
    cg_overrides.pop(cg_id, None)
    session.modified = True
    return jsonify({'ok': True})


@app.route('/builder_beta/li_override_save', methods=['POST'])
@csrf.exempt
def builder_li_override_save():
    """Save a line item override to the session."""
    data = request.get_json(force=True) or {}
    item_id = data.get('item_id', '')
    value = data.get('value')
    if not item_id or value is None:
        return jsonify({'ok': False, 'error': 'item_id and value required'}), 400
    try:
        val = float(value)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Invalid value'}), 400
    session_overrides = session.setdefault('session_overrides', {})
    overrides = session_overrides.setdefault('overrides', {})
    overrides[item_id] = val
    session.modified = True
    return jsonify({'ok': True})


@app.route('/builder_beta/li_units_save', methods=['POST'])
@csrf.exempt
def builder_li_units_save():
    """Save a line item units override to the session."""
    data = request.get_json(force=True) or {}
    item_id = data.get('item_id', '')
    value = data.get('value')
    if not item_id or value is None:
        return jsonify({'ok': False, 'error': 'item_id and value required'}), 400
    try:
        val = int(value)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Invalid value'}), 400
    session_overrides = session.setdefault('session_overrides', {})
    units_overrides = session_overrides.setdefault('units_overrides', {})
    units_overrides[item_id] = val
    session.modified = True
    return jsonify({'ok': True})


@app.route('/builder_beta/page_total_save/<page_key>', methods=['POST'])
@require_role('admin')
def builder_page_total_save(page_key):
    """Save page total module config (label, included cost groups).
    Config lives in the page_total block's config field — not in metadata_json."""
    data = request.get_json(force=True) or {}
    label = data.get('label', 'Page Total')
    groups = data.get('groups', [])
    form_visible = data.get('form_visible', True)
    quote_visible = data.get('quote_visible', True)
    # Write directly to the page_total block in page_schemas.json
    bb_pages = page_schemas.setdefault('builder_beta', {}).setdefault('pages', {})
    page = bb_pages.get(page_key)
    if not page:
        return jsonify({'ok': False, 'error': 'Page not found'}), 404
    for block in page.setdefault('blocks', []):
        if block.get('block_type') == 'page_total':
            block.setdefault('config', {})
            block['config']['groups'] = groups
            block['config']['form_visible'] = form_visible
            block['config']['quote_visible'] = quote_visible
            if label:
                block.setdefault('standard', {})['label'] = label
            break
    save_page_schemas()
    return jsonify({'ok': True})

@app.route('/builder_beta/module_block_add/<page_id>', methods=['POST'])
@require_role('admin')
def builder_module_block_add(page_id):
    """Add a module as a proper block in the page schema (not category_templates)."""
    data = request.get_json(force=True) or {}
    mod_type = data.get('module_type', '')
    label = data.get('label', '')
    if not mod_type or not page_id:
        return jsonify({'ok': False, 'error': 'module_type and page_id required'}), 400
    # Modify page_schemas directly
    bb_pages = page_schemas.setdefault('builder_beta', {}).setdefault('pages', {})
    page = bb_pages.get(page_id)
    if not page:
        return jsonify({'ok': False, 'error': 'Page not found'}), 404
    blocks = page.setdefault('blocks', [])
    new_block = _new_block_template(mod_type, page_id, len(blocks))
    if label:
        new_block['standard']['label'] = label
    blocks.append(new_block)
    save_page_schemas()
    return jsonify({'ok': True})

@app.route('/builder_beta/module_block_delete/<page_id>', methods=['POST'])
@require_role('admin')
def builder_module_block_delete(page_id):
    """Remove a module block from the page schema."""
    data = request.get_json(force=True) or {}
    mod_type = data.get('module_type', '')
    if not mod_type or not page_id:
        return jsonify({'ok': False, 'error': 'module_type and page_id required'}), 400
    bb_pages = page_schemas.setdefault('builder_beta', {}).setdefault('pages', {})
    page = bb_pages.get(page_id)
    if not page:
        return jsonify({'ok': False, 'error': 'Page not found'}), 404
    blocks = page.get('blocks', [])
    new_blocks = [b for b in blocks if b.get('block_type') != mod_type]
    if len(new_blocks) == len(blocks):
        return jsonify({'ok': False, 'error': 'No block found with that type'}), 404
    page['blocks'] = new_blocks
    save_page_schemas()
    return jsonify({'ok': True})

@app.route('/builder_beta/category_details_json')
@app.route('/builder_beta/category_details_json')
@require_role('admin')
def builder_category_details_json():
    page_key = request.args.get('page_key')
    name = request.args.get('name')
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    conn = _get_conn()
    
    # Get latest version id
    latest_version_row = conn.execute(
        """
        SELECT ftv.id
        FROM form_template_versions ftv
        JOIN form_templates ft ON ft.id = ftv.form_template_id
        WHERE ft.key = ?
        ORDER BY ftv.version DESC
        LIMIT 1
        """,
        (TEMPLATE_STORE_KEY,)
    ).fetchone()
    latest_version_id = int(latest_version_row[0]) if latest_version_row else None
    if latest_version_id is None:
        conn.close()
        return jsonify({})
    row = conn.execute('''
        SELECT c.id, c.name, c.description, c.output_group, c.image_url, c.is_cost_group, c.cost_group_override_allowed
        FROM category_templates c
        JOIN page_templates p ON c.page_template_id = p.id
        WHERE p.page_key = ? AND p.form_template_version_id = ? AND c.name = ?
    ''', [page_key, latest_version_id, name]).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result['category_image'] = result.get('image_url', '') or ''
        # Also load multiple images from category_images table
        try:
            import sqlite3 as _sql
            conn2 = _get_conn()
            img_rows = conn2.execute(
                '''
                SELECT ci.image_url
                FROM category_images ci
                JOIN page_templates pt ON pt.id = ci.page_template_id
                WHERE pt.page_key = ? AND ci.category_name = ?
                ORDER BY ci.sort_order, ci.id
                ''',
                (page_key, name),
            ).fetchall()
            conn2.close()
            result['category_images'] = [r['image_url'] for r in img_rows if r['image_url']]
        except Exception:
            result['category_images'] = []
        return jsonify(result)
    return jsonify({})


@csrf.exempt
@app.route('/builder_beta/category_details_save', methods=['POST'])
@require_role('admin')
def builder_category_details_save():
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    from urllib.parse import unquote
    page_key = data.get('page_key')
    old_name = data.get('old_name')
    if old_name:
        old_name = unquote(old_name)
    new_name = data.get('new_name')
    if new_name:
        new_name = unquote(new_name)
    desc = data.get('description', '')
    output_group = data.get('output_group', 'General')
    is_cost_group = data.get('is_cost_group', False)
    category_image = (data.get('category_image') or '').strip()
    category_images = data.get('category_images') or []
    if not isinstance(category_images, list):
        category_images = [category_images] if category_images else []
    category_images = [str(u).strip() for u in category_images if str(u).strip()]
    # dedupe preserving order
    seen = set()
    deduped = []
    for u in category_images:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    category_images = deduped
    print(f"[CAT_SAVE] page_key={page_key!r} old_name={old_name!r} new_name={new_name!r} category_image={category_image!r} category_images={category_images!r}", flush=True)

    conn = _get_conn()
    try:
        latest_version_row = conn.execute(
            """
            SELECT ftv.id
            FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            ORDER BY ftv.version DESC
            LIMIT 1
            """,
            (TEMPLATE_STORE_KEY,)
        ).fetchone()
        latest_version_id = int(latest_version_row[0]) if latest_version_row else None
        if latest_version_id is None:
            return jsonify({'success': False, 'error': 'Template version not found'}), 404

        page_ids = [r[0] for r in conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ?",
            [page_key]).fetchall()]
        print(f"[CAT_SAVE] page_ids={page_ids}", flush=True)

        for pid in page_ids:
            conn.execute(
                "UPDATE category_templates SET name = ?, description = ?, output_group = ?, image_url = ?, is_cost_group = ?, cost_group_override_allowed = ? WHERE page_template_id = ? AND name = ?",
                [new_name, desc, output_group, category_image or (category_images[0] if category_images else ''), 1 if is_cost_group else 0, 1 if data.get('cost_group_override_allowed') else 0, pid, old_name]
            )
            print(f"[CAT_SAVE] Updated pid={pid} old_name={old_name!r} -> image_url={category_image!r}", flush=True)

        conn.commit()

        # Sync category_images table
        for pid in page_ids:
            conn.execute(
                "DELETE FROM category_images WHERE page_template_id = ? AND category_name = ?",
                [pid, old_name]
            )
            for idx, url in enumerate(category_images):
                conn.execute(
                    "INSERT INTO category_images (page_template_id, category_name, image_url, sort_order) VALUES (?, ?, ?, ?)",
                    [pid, new_name, url, idx]
                )
        conn.commit()
        print(f"[CAT_SAVE] Synced {len(category_images)} images to category_images table", flush=True)

        # Sync changes to the corresponding block in page_schemas.json
        if is_cost_group:
            try:
                bb = page_schemas.setdefault('builder_beta', {}).setdefault('pages', {})
                pg = bb.get(page_key)
                if pg:
                    for blk in pg.setdefault('blocks', []):
                        if blk.get('block_type') == 'cost_group_section' and blk.get('standard', {}).get('label') == old_name:
                            blk.setdefault('config', {})['cost_group_id'] = output_group or ''
                            blk.setdefault('config', {})['override_allowed'] = bool(data.get('cost_group_override_allowed'))
                            if new_name != old_name:
                                blk.setdefault('standard', {})['label'] = new_name
                            break
                save_page_schemas()
            except Exception as e:
                print(f"[CAT_SAVE] Block sync failed: {e}", flush=True)

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


def _get_page_visibility(page_key: str) -> dict:
    """Return {form_visible, quote_visible} for a page, defaulting both to True."""
    try:
        import sqlite3
        from pathlib import Path
        db = str(Path(__file__).parent / 'template_store.sqlite3')
        conn = _get_conn()
        row = conn.execute(
            "SELECT metadata_json FROM page_templates WHERE page_key = ? "
            "AND form_template_version_id IN (SELECT id FROM form_template_versions "
            "WHERE form_template_id = (SELECT id FROM form_templates WHERE key = ?) "
            "ORDER BY version DESC LIMIT 1)",
            (page_key, TEMPLATE_STORE_KEY)
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


@app.route('/builder_beta/category/add', methods=['POST'])
@require_role('admin')
def builder_beta_category_add():
    import template_store as _ts
    import sys
    try:
        data = request.get_json(force=True) or {}
        if not data or 'page_key' not in data or 'category_name' not in data:
            return jsonify(
                {'success': False, 'error': 'Missing page_key or category_name'}), 400
        output_group = data.get('output_group', 'General')
        is_cost_group = data.get('is_cost_group', 0)
        print(f"[CAT_ADD_DEBUG] page_key={data['page_key']!r} category_name={data['category_name']!r} output_group={output_group!r} is_cost_group={is_cost_group!r}", file=sys.stderr)
        res = _ts.add_category(
            data['page_key'],
            data['category_name'],
            template_key=TEMPLATE_STORE_KEY,
            output_group=output_group)
        # If this is a module entry, set is_module and module_type on the newly created category
        is_module = data.get('is_module', 0)
        module_type = data.get('module_type', '')
        if res.get('success') and (is_module or module_type):
            try:
                import sqlite3
                from pathlib import Path
                db = str(Path(__file__).parent / 'template_store.sqlite3')
                conn2 = _get_conn()
                conn2.execute(
                    "UPDATE category_templates SET is_module = ?, module_type = ? WHERE name = ? AND page_template_id IN (SELECT id FROM page_templates WHERE page_key = ?)",
                    (1 if is_module else 0, module_type, data['category_name'], data['page_key'])
                )
                conn2.commit()
                conn2.close()
            except Exception:
                pass
        # If this is a cost group section and the name already exists, update the existing entry
        if is_cost_group and not res.get('success') and res.get('duplicate'):
            import sqlite3
            from pathlib import Path
            db = str(Path(__file__).parent / 'template_store.sqlite3')
            conn2 = _get_conn()
            conn2.execute(
                "UPDATE category_templates SET is_cost_group = 1 WHERE name = ? AND page_template_id IN (SELECT id FROM page_templates WHERE page_key = ?)",
                (data['category_name'], data['page_key'])
            )
            conn2.commit()
            conn2.close()
            return jsonify({'success': True})
        if res.get('success') and is_cost_group:
            # Update the newly created category to mark it as a cost group section
            try:
                import sqlite3
                from pathlib import Path
                db = str(Path(__file__).parent / 'template_store.sqlite3')
                conn2 = _get_conn()
                conn2.execute(
                    "UPDATE category_templates SET is_cost_group = 1 WHERE name = ? AND page_template_id IN (SELECT id FROM page_templates WHERE page_key = ?)",
                    (data['category_name'], data['page_key'])
                )
                conn2.commit()
                conn2.close()
            except Exception:
                pass
            # Also create a block in page_schemas.json for the cost group section
            try:
                import time
                bb = page_schemas.setdefault('builder_beta', {}).setdefault('pages', {})
                pg = bb.get(data['page_key'])
                if pg:
                    block_id = f"{data['page_key']}__cg_{data['category_name'].lower().replace(' ', '_')}_{int(time.time() * 1000)}"
                    new_block = {
                        'id': block_id,
                        'block_type': 'cost_group_section',
                        'standard': {
                            'label': data['category_name'],
                            'name': block_id,
                            'required': False,
                            'help_text': '',
                            'source_prefix': '',
                            'placeholder': '',
                            'dropdown_choices': [],
                            'selection_limit': None,
                            'static_content': '',
                            'static_variant': 'body',
                        },
                        'config': {
                            'cost_group_id': output_group or '',
                            'override_allowed': False,
                        },
                        'display_order': len(pg.get('blocks', [])),
                    }
                    pg.setdefault('blocks', []).append(new_block)
                    save_page_schemas()
            except Exception as e:
                print(f"[CAT_ADD] Block creation failed: {e}", flush=True)
        print(f"[CAT_ADD_DEBUG] res={res!r}", file=sys.stderr)
        if res.get('success'):
            return jsonify({'success': True})
        return jsonify(res), 500
    except Exception as e:
        import traceback
        print(f"[CAT_ADD_DEBUG] exception: {e!r}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return jsonify({'success': False, 'error': str(e)}), 500


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
        conn = _get_conn()
        

        # Verify the category exists before attempting insert
        # Get latest version id
        latest_version_row = conn.execute(
            """
            SELECT ftv.id
            FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            ORDER BY ftv.version DESC
            LIMIT 1
            """,
            (TEMPLATE_STORE_KEY,)
        ).fetchone()
        latest_version_id = int(latest_version_row[0]) if latest_version_row else None
        if latest_version_id is None:
            conn.close()
            return jsonify({'success': False, 'error': 'Template version not found'}), 404
        cat_exists = conn.execute(
            "SELECT 1 FROM category_templates ct "
            "JOIN page_templates p ON ct.page_template_id = p.id "
            "WHERE p.page_key = ? AND p.form_template_version_id = ? AND ct.name = ?",
            [page_key, latest_version_id, category]
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
            "WHERE p.page_key = ? AND p.form_template_version_id = ? AND ct.name = ?",
            [page_key, latest_version_id, category]
        ).fetchone()
        output_group_val = default_group[0] if default_group else 'General'

        cur.execute('''
            INSERT INTO line_items (form_page, category, line_code, internal_description, item_role, form_visible, sort_order, output_group, metadata_json)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
        ''', [page_key, category, new_code, "New Question", "parent", next_sort, output_group_val, json.dumps(data.get('metadata', {}) or {})])
        conn.commit()

        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM line_items WHERE id = ?",
            [new_id]).fetchone()

        return jsonify({'success': True, 'item': dict(row)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
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

    conn = _get_conn()
    
    try:
        # Get latest version id
        latest_version_row = conn.execute(
            """
            SELECT ftv.id
            FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            ORDER BY ftv.version DESC
            LIMIT 1
            """,
            (TEMPLATE_STORE_KEY,)
        ).fetchone()
        latest_version_id = int(latest_version_row[0]) if latest_version_row else None
        if latest_version_id is None:
            return jsonify({'success': False, 'error': 'Template version not found'}), 404

        page_id_row = conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
            [page_key, latest_version_id]).fetchone()
        if not page_id_row:
            return jsonify({'success': False, 'error': 'Page not found'}), 404
        page_id = page_id_row[0]

        # Delete category mapping across ALL versions (not just latest),
        # so categories that exist in older versions but not the latest
        # (e.g. "Work Summary" renamed to "Summary" in v647) can still be removed.
        conn.execute(
            "DELETE FROM category_templates WHERE page_template_id IN (SELECT id FROM page_templates WHERE page_key = ?) AND name = ?", [
                page_key, category_name])
        # Additionally delete all child line_items
        conn.execute(
            "DELETE FROM line_items WHERE form_page = ? AND category = ?", [
                page_key, category_name])
        # Sync payload snapshot
        _remove_category_from_payload(conn, latest_version_id, page_key, category_name)
        
        # Renumber display_order to close gaps left by deleted categories
        remaining = conn.execute(
            """SELECT c.name
               FROM category_templates c
               JOIN page_templates pt ON pt.id = c.page_template_id
               WHERE pt.page_key = ?
               ORDER BY c.display_order ASC, c.id ASC""",
            [page_key]
        ).fetchall()
        seen = set()
        for new_order, row in enumerate(remaining):
            if row['name'] not in seen:
                seen.add(row['name'])
                conn.execute(
                    "UPDATE category_templates SET display_order = ? WHERE name = ? AND page_template_id IN (SELECT id FROM page_templates WHERE page_key = ?)",
                    [new_order, row['name'], page_key]
                )
        
        conn.commit()
        # Remove the corresponding block from page_schemas.json
        try:
            bb = page_schemas.setdefault('builder_beta', {}).setdefault('pages', {})
            pg = bb.get(page_key)
            if pg:
                blocks = pg.get('blocks', [])
                pg['blocks'] = [b for b in blocks if not (b.get('block_type') == 'cost_group_section' and b.get('standard', {}).get('label') == category_name)]
                save_page_schemas()
        except Exception as e:
            print(f"[CAT_DELETE] Block removal failed: {e}", flush=True)
        return jsonify({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/category/move', methods=['POST'])
@require_role('admin')
def builder_category_move():
    """Move a category (and its line items) from one page to another."""
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    category_name = data.get('category_name')
    target_page_key = data.get('target_page_key')

    if not page_key or not category_name or not target_page_key:
        return jsonify({'success': False, 'error': 'page_key, category_name, and target_page_key are required'}), 400

    if page_key == target_page_key:
        return jsonify({'success': False, 'error': 'Source and target pages are the same'}), 400

    conn = _get_conn()
    try:
        # Get latest version id
        latest_version_row = conn.execute(
            """
            SELECT ftv.id
            FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            ORDER BY ftv.version DESC
            LIMIT 1
            """,
            (TEMPLATE_STORE_KEY,)
        ).fetchone()
        latest_version_id = int(latest_version_row[0]) if latest_version_row else None
        if latest_version_id is None:
            return jsonify({'success': False, 'error': 'Template version not found'}), 404

        source_page = conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
            [page_key, latest_version_id]
        ).fetchone()
        target_page = conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
            [target_page_key, latest_version_id]
        ).fetchone()

        if not source_page or not target_page:
            return jsonify({'success': False, 'error': 'Source or target page not found'}), 404

        source_page_id = source_page[0]
        target_page_id = target_page[0]

        # Update category_templates to point to target page
        conn.execute(
            "UPDATE category_templates SET page_template_id = ? WHERE page_template_id = ? AND name = ?",
            [target_page_id, source_page_id, category_name]
        )

        # Update line_items to point to target page
        conn.execute(
            "UPDATE line_items SET form_page = ? WHERE form_page = ? AND category = ?",
            [target_page_key, page_key, category_name]
        )

        # Sync payload snapshot
        _move_category_in_payload(conn, latest_version_id, page_key, target_page_key, category_name)
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
    conn = _get_conn()
    try:
        # Get latest version id
        latest_version_row = conn.execute(
            """
            SELECT ftv.id
            FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            ORDER BY ftv.version DESC
            LIMIT 1
            """,
            (TEMPLATE_STORE_KEY,)
        ).fetchone()
        latest_version_id = int(latest_version_row[0]) if latest_version_row else None
        if latest_version_id is None:
            return jsonify({'error': 'Template version not found'}), 404

        row = conn.execute(
            "SELECT id FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
            [page_key, latest_version_id]).fetchone()
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
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/page/add', methods=['POST'])
@require_role('admin')
def builder_page_add():
    import template_store as _ts
    data = request.get_json(force=True) or {}
    title = data.get('title', '')
    page_key = data.get('page_key', '')
    if not title or not page_key:
        return jsonify({'success': False, 'error': 'title and page_key are required'}), 400
    res = _ts.add_page(page_key, title, template_key=TEMPLATE_STORE_KEY)
    if res.get('success'):
        return jsonify({'success': True, 'page_key': page_key})
    return jsonify(res), 500


@app.route('/builder_beta/page/duplicate', methods=['POST'])
@require_role('admin')
def builder_page_duplicate():
    import template_store as _ts
    data = request.get_json(force=True) or {}
    source_page_key = data.get('source_page_key', '')
    new_page_key = data.get('new_page_key', '')
    new_title = data.get('new_title', '')
    if not source_page_key or not new_page_key or not new_title:
        return jsonify({'success': False, 'error': 'source_page_key, new_page_key, and new_title are required'}), 400
    res = _ts.duplicate_page(source_page_key, new_page_key, new_title, template_key=TEMPLATE_STORE_KEY)
    if res.get('success'):
        return jsonify({'success': True, 'page_key': new_page_key})
    return jsonify(res), 500


@app.route('/builder_beta/save_as_template', methods=['POST'])
@require_role('admin')
def builder_save_as_template():
    return jsonify({'ok': True, 'msg': 'Template saved successfully'})


@app.route('/builder_beta/template/quick_save', methods=['POST'])
@require_role('admin')
def builder_quick_save():
    """Save the current template in-place, creating a new version."""
    import template_store as _ts
    template_key = session.get('template_key') or TEMPLATE_STORE_KEY
    try:
        payload = _rebuild_payload_from_db(conn=None, template_key=template_key)
        if not payload:
            payload = _ts.load_template_payload(template_key) or {}
        result = _ts.save_template(template_key, payload)
        return jsonify({'success': True, **result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/builder_beta/template/save_as', methods=['POST'])
@require_role('admin')
def builder_save_as_new():
    """Save current template under a new name (clone with versioning)."""
    import template_store as _ts
    data = request.json or {}
    new_name = data.get('name', '').strip()
    new_description = data.get('description', '').strip()
    new_key = data.get('key', '').strip()
    overwrite_key = data.get('overwrite_key', '').strip()
    if overwrite_key:
        new_key = overwrite_key
        new_name = new_name or overwrite_key
    if not new_name or not new_key:
        return jsonify({'success': False, 'error': 'Name and key are required'}), 400
    try:
        payload = _rebuild_payload_from_db(conn=None, template_key=TEMPLATE_STORE_KEY)
        if not payload:
            payload = _ts.load_template_payload(TEMPLATE_STORE_KEY) or {}
    except Exception:
        payload = {}
    try:
        result = _ts.save_template(new_key, payload, name=new_name, description=new_description)
        return jsonify({'success': True, **result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/builder_beta/template/list')
@require_role('admin')
def builder_template_list():
    """Return all templates for the save-as / load picker."""
    import template_store as _ts
    overview = _ts.get_template_store_overview()
    templates = overview.get('templates', [])
    return jsonify({'success': True, 'templates': templates})


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

    conn = _get_conn()
    try:
        conn.execute("DELETE FROM line_items WHERE line_code = ?", [line_code])
        conn.commit()
        return jsonify({'success': True, 'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/line_item_duplicate', methods=['POST'])
@require_role('admin')
def builder_line_item_duplicate():
    import sqlite3
    import time
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    line_code = data.get('line_code')
    page_key = data.get('page_key')
    category = data.get('category')

    if not line_code:
        return jsonify({'error': 'No line code provided'}), 400

    conn = _get_conn()
    
    try:
        print(f"[DUPLICATE] line_code={line_code!r} page_key={page_key!r} category={category!r}", flush=True)
        row = conn.execute(
            "SELECT * FROM line_items WHERE line_code = ?",
            [line_code]
        ).fetchone()
        print(f"[DUPLICATE] row found: {row is not None}", flush=True)
        if not row:
            return jsonify({'error': 'Line item not found'}), 404

        max_sort = conn.execute(
            "SELECT MAX(sort_order) FROM line_items WHERE form_page = ? AND category = ?",
            [row['form_page'], row['category']]
        ).fetchone()[0]
        next_sort = 0 if max_sort is None else max_sort + 1
        new_code = f"{row['line_code']}_copy_{int(time.time())}"

        cur = conn.cursor()
        cur.execute('''
            INSERT INTO line_items (
                line_code, form_page, category, internal_description,
                include_default, unit_cost, units, pricing_visibility,
                output_title, output_notes, output_guidance,
                parent_code, item_role, input_type, trigger_parent_code,
                form_visible, sort_order,
                is_follow_up, follow_up_type, follow_up_config,
                allow_user_override, output_group, quantity_source, pricing_mode,
                addon_amount, price_matrix
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            new_code,
            row['form_page'],
            row['category'],
            row['internal_description'] + ' (copy)',
            row['include_default'],
            row['unit_cost'],
            row['units'],
            row['pricing_visibility'],
            row['output_title'],
            row['output_notes'],
            row['output_guidance'],
            row['parent_code'] or '',
            row['item_role'],
            row['input_type'] or '',
            row['trigger_parent_code'] or '',
            row['form_visible'],
            next_sort,
            row['is_follow_up'],
            row['follow_up_type'] or '',
            row['follow_up_config'] or '',
            row['allow_user_override'] if 'allow_user_override' in row.keys() else 0,
            row['output_group'] or 'General',
            row['quantity_source'] or '',
            row['pricing_mode'] if 'pricing_mode' in row.keys() else 'per_unit',
            row['addon_amount'] if 'addon_amount' in row.keys() else 0.0,
            row['price_matrix'] if 'price_matrix' in row.keys() else None,
        ])
        conn.commit()
        new_id = cur.lastrowid
        new_row = conn.execute(
            "SELECT * FROM line_items WHERE id = ?",
            [new_id]
        ).fetchone()
        return jsonify({"success": True, "item": dict(new_row)})
    except Exception as e:
        import traceback
        print(f"[DUPLICATE ERROR] {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


# ── Helper: compute per-group totals from checked items ────────────────
def _compute_cost_group_totals(groups, conn, session_data):
    """Return {group_id: total} by summing only checked items in each cost
    group.  Uses the same category-routing / checkbox_data logic as the
    cost group accordion, so the totals always match."""
    from template_store import _default_db_path, _connect
    cat_rows = conn.execute(
        f"""SELECT ct.name, ct.output_group
            FROM category_templates ct
            WHERE ct.output_group IN ({','.join('?' for _ in groups)})
            AND ct.form_template_version_id = (
                SELECT MAX(ftv.id) FROM form_template_versions ftv
                JOIN form_templates ft ON ft.id = ftv.form_template_id
                WHERE ft.key = ?
            )""",
        groups + ['builder_beta']
    ).fetchall()
    cg_to_cats = {}
    for r in cat_rows:
        og = r['output_group']
        cg_to_cats.setdefault(og, []).append(r['name'])

    # Collect checked line_codes from every page
    try:
        cb_data = (session_data.get('checkbox_data', {}) or {})
        checked_set = set()
        for _key, _val in cb_data.items():
            if _key.endswith('__line_items') and isinstance(_val, dict):
                _ps = _val.get('preselected')
                if isinstance(_ps, list):
                    checked_set.update(_ps)
    except Exception:
        checked_set = set()
    # Build a lookup: category_name -> output_group (from cat templates)
    cat_to_group = {}
    for _r in cat_rows:
        cat_to_group[_r['name']] = _r['output_group']

    # Sum only checked items per group, respecting per-line-item overrides
    try:
        units_ovr = (session_data.get('session_overrides', {}) or {}).get('units_overrides', {}) or {}
    except Exception:
        units_ovr = {}
    totals = {}
    for gid in groups:
        cat_names = cg_to_cats.get(gid, [])
        if not cat_names:
            totals[gid] = 0.0
            continue
        cat_ph = ','.join('?' for _ in cat_names)
        # Also fetch output_group and override flag so we can route correctly
        rows = conn.execute(
            f"SELECT id, line_code, unit_cost, units, output_group, override_output_group, category FROM line_items WHERE category IN ({cat_ph})",
            cat_names
        ).fetchall()
        gt = 0.0
        for r in rows:
            if r['line_code'] not in checked_set:
                continue
            # Check if this line item overrides its category routing
            if r['override_output_group'] and r['output_group'] and r['output_group'] != cat_to_group.get(r.get('category', ''), ''):
                # This line item is routed to a DIFFERENT group — skip it here;
                # it will be picked up when we process that group.
                continue
            u = units_ovr.get(str(r['id']), float(r['units'] or 0))
            gt += round(float(r['unit_cost'] or 0) * float(u), 2)
        totals[gid] = gt
    # Second pass: pick up override-routed line items and add to their target groups
    all_cat_names = []
    for _cn in cg_to_cats.values():
        all_cat_names.extend(_cn)
    if all_cat_names:
        all_ph = ','.join('?' for _ in all_cat_names)
        override_rows = conn.execute(
            f"SELECT id, line_code, unit_cost, units, output_group, category FROM line_items WHERE category IN ({all_ph}) AND override_output_group = 1",
            all_cat_names
        ).fetchall()
        for r in override_rows:
            if r['line_code'] not in checked_set:
                continue
            target_group = r['output_group'] or ''
            if target_group in groups:
                u = units_ovr.get(str(r['id']), float(r['units'] or 0))
                totals.setdefault(target_group, 0.0)
                totals[target_group] += round(float(r['unit_cost'] or 0) * float(u), 2)
    # Apply cost-group-level overrides (macro overrides)
    try:
        cg_ovr = (session_data.get('session_overrides', {}) or {}).get('cg_overrides', {}) or {}
        for gid in groups:
            if gid in cg_ovr:
                totals[gid] = float(cg_ovr[gid])
    except Exception:
        pass
    return totals
# ── Calculator Preview Route ─────────────────────────────────────────
@app.route('/builder_beta/calculator_preview', methods=['GET'])
@csrf.exempt
def builder_calculator_preview():
    """Return line items for selected cost groups using category-level routing.
    A category is routed to a cost group when category_templates.output_group
    matches the cost group id. All line items in that category are included,
    regardless of which form_page they belong to.

    Called from the customer-facing form preview (cost group accordions),
    so it must not require admin role."""
    page_key = request.args.get('page_key', '')
    group_ids_param = request.args.get('groups', '')
    if not group_ids_param:
        return jsonify({'items': {}, 'error': None})
    group_ids = [g.strip() for g in group_ids_param.split(',') if g.strip()]
    from template_store import _default_db_path, _connect
    db_path = _default_db_path()
    conn = _connect(db_path)
    try:
        # Step 1: find all category names routed to the requested cost groups
        # A category is routed to cost group X when ct.output_group = X
        placeholders = ','.join(['?' for _ in group_ids])
        cat_rows = conn.execute(
            f"""SELECT ct.name, ct.output_group
                FROM category_templates ct
                WHERE ct.output_group IN ({placeholders})
                AND ct.form_template_version_id = (
                    SELECT MAX(ftv.id) FROM form_template_versions ftv
                    JOIN form_templates ft ON ft.id = ftv.form_template_id
                    WHERE ft.key = ?
                )""",
            group_ids + ['builder_beta']
        ).fetchall()
        
        # Build mapping: output_group -> list of category names
        cg_to_cats = {}
        for r in cat_rows:
            og = r['output_group']
            if og not in cg_to_cats:
                cg_to_cats[og] = []
            cg_to_cats[og].append(r['name'])
        
        # Step 2: fetch line items from ALL pages whose category matches
        items_by_group = {}
        for gid in group_ids:
            cat_names = cg_to_cats.get(gid, [])
            if not cat_names:
                items_by_group[gid] = []
                continue
            # Build placeholders for category names
            cat_placeholders = ','.join(['?' for _ in cat_names])
            rows = conn.execute(
                f"""SELECT li.id, li.line_code, li.internal_description, li.output_title, li.unit_cost,
                          li.units, li.sort_order, li.category,
                          li.output_group, li.pricing_mode, li.pricing_visibility,
                          li.form_page
                   FROM line_items li
                   WHERE li.category IN ({cat_placeholders})
                   ORDER BY li.category ASC, li.sort_order ASC, li.line_code ASC""",
                cat_names
            ).fetchall()
            items_by_group[gid] = [dict(r) for r in rows]
        
        # Mark items as checked/unchecked and apply price overrides from session
        # The user checks items on INPUT pages (e.g. additional_costs_page).
        # Those checked values are stored in checkbox_data as {page_key}__line_items.
        # On the REVIEW page (pricing_categories), we need to find them regardless
        # of which input page they came from.
        try:
            cb_data = (session.get('checkbox_data', {}) or {})
            li_overrides = (session.get('session_overrides', {}) or {}).get('overrides', {}) or {}
            # Collect all checked line_code values from every page's line items field
            checked_set = set()
            for _key, _val in cb_data.items():
                if _key.endswith('__line_items') and isinstance(_val, dict):
                    _ps = _val.get('preselected')
                    if isinstance(_ps, list):
                        checked_set.update(_ps)
            for gid in list(items_by_group.keys()):
                for it in items_by_group[gid]:
                    is_checked = it.get('line_code') in checked_set
                    it['checked'] = is_checked
                    item_id = str(it.get('id', ''))
                    # Apply price override from session (only for checked items)
                    if is_checked and item_id in li_overrides:
                        it['unit_cost'] = float(li_overrides[item_id])
                    # Unchecked items: zero the values so they display as £0.00 / 0 / £0.00
                    if not is_checked:
                        it['unit_cost'] = 0.0
                        it['units'] = 0
        except Exception:
            pass
        
        return jsonify({'items': items_by_group, 'error': None})
    except Exception as e:
        return jsonify({'items': {}, 'error': str(e)})
    finally:
        conn.close()


# ── Cost Group Management Routes ─────────────────────────────────────
@app.route('/builder_beta/cost_groups')
@require_role('admin')
def builder_cost_groups():
    """Return all cost groups for management."""
    state = get_builder_beta_state()
    cost_groups = state.get('cost_groups', {})
    # Convert to list for easier consumption by frontend
    groups_list = []
    for group_id, group_data in cost_groups.items():
        groups_list.append({
            'id': group_id,
            'label': group_data.get('label', group_id),
            'description': group_data.get('description', ''),
            'sort_order': group_data.get('sort_order', 0)
        })
    # Sort by sort_order
    groups_list.sort(key=lambda x: x['sort_order'])
    return jsonify({'success': True, 'cost_groups': groups_list})


@app.route('/builder_beta/cost_group/save', methods=['POST'])
@require_role('admin')
def builder_cost_group_save():
    """Save (create or update) a cost group."""
    import template_store as ts
    data = request.get_json(force=True) or {}
    
    group_id = data.get('id', '').strip()
    label = data.get('label', '').strip()
    description = data.get('description', '').strip()
    sort_order = data.get('sort_order', 0)
    
    if not group_id:
        return jsonify({'success': False, 'error': 'Cost group ID is required'}), 400
    if not label:
        return jsonify({'success': False, 'error': 'Cost group label is required'}), 400
    
    # Validate sort_order is an integer
    try:
        sort_order = int(sort_order)
    except (ValueError, TypeError):
        sort_order = 0
    
    state = get_builder_beta_state()
    if 'cost_groups' not in state:
        state['cost_groups'] = {}
    
    # Check if this is a new group or existing one
    is_new = group_id not in state['cost_groups']
    
    # Update or create the cost group
    state['cost_groups'][group_id] = {
        'label': label,
        'description': description,
        'sort_order': sort_order
    }
    
    # If renaming an existing group, cascade the update to all references
    if not is_new and 'old_id' in data and data['old_id'] != group_id:
        old_id = data['old_id']
        # Update all line_items that reference the old group
        conn = ts.get_connection()
        try:
            conn.execute(
                "UPDATE line_items SET output_group = ? WHERE output_group = ?",
                [group_id, old_id]
            )
            conn.commit()
        finally:
            conn.close()
        
        # Update all category_templates that reference the old group
        conn = ts.get_connection()
        try:
            conn.execute(
                "UPDATE category_templates SET output_group = ? WHERE output_group = ?",
                [group_id, old_id]
            )
            conn.commit()
        finally:
            conn.close()
    
    # Save the updated state back to the database
    ts.update_builder_beta_state(TEMPLATE_STORE_KEY, state)
    
    # Refresh the in-memory cache so the UI sees new cost groups immediately
    try:
        from template_store import load_template_payload
        db_payload = load_template_payload(TEMPLATE_STORE_KEY)
        if db_payload:
            globals()['page_schemas'] = db_payload
    except Exception:
        pass
    
    return jsonify({
        'success': True, 
        'cost_group': {
            'id': group_id,
            'label': label,
            'description': description,
            'sort_order': sort_order
        },
        'is_new': is_new
    })


@app.route('/builder_beta/cost_group/delete', methods=['POST'])
@require_role('admin')
def builder_cost_group_delete():
    """Delete a cost group and remap its references."""
    import template_store as ts
    data = request.get_json(force=True) or {}
    
    group_id = data.get('id', '').strip()
    if not group_id:
        return jsonify({'success': False, 'error': 'Cost group ID is required'}), 400
    
    # Prevent deletion of the default 'general' group
    if group_id == 'general':
        return jsonify({'success': False, 'error': 'Cannot delete the default General cost group'}), 400
    
    state = get_builder_beta_state()
    if 'cost_groups' not in state or group_id not in state['cost_groups']:
        return jsonify({'success': False, 'error': 'Cost group not found'}), 404
    
    # Get the remap target (if specified)
    remap_to = data.get('remap_to', '').strip()
    if not remap_to:
        remap_to = 'general'  # Default to general group
    
    # Ensure remap_to exists
    if remap_to not in state['cost_groups']:
        remap_to = 'general'
    
    import sqlite3
    from pathlib import Path
    _db = str(Path(__file__).parent / 'template_store.sqlite3')
    
    # Remap all line_items that reference this group
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE line_items SET output_group = ? WHERE output_group = ?",
            [remap_to, group_id]
        )
        conn.commit()
    finally:
        conn.close()
    
    # Remap all category_templates that reference this group
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE category_templates SET output_group = ? WHERE output_group = ?",
            [remap_to, group_id]
        )
        conn.commit()
    finally:
        conn.close()
    
    # Remove the cost group
    del state['cost_groups'][group_id]
    
    # Save the updated state back to the database
    ts.update_builder_beta_state(TEMPLATE_STORE_KEY, state)
    
    return jsonify({
        'success': True, 
        'remapped_to': remap_to,
        'deleted_id': group_id
    })


@app.route('/builder_beta/line_item_save/<int:item_id>', methods=['POST'])
@require_role('admin')
def builder_line_item_save(item_id):
    """Save/update a line item's editable fields."""
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    # Normalise the Preselected checkbox (posted as 1/0) to the DB's 'Y'/'N'
    if 'include_default' in data:
        data['include_default'] = 'Y' if str(data['include_default']).lower() in ('1', 'y', 'true', 'yes', 'on') else 'N'
    # Prevent PostgreSQL "invalid input syntax for type real" when the JS
    # submits empty '' for numeric fields (number inputs start blank).
    for key in ('unit_cost', 'units', 'addon_amount'):
        if key in data and (data[key] == '' or data[key] is None):
            data[key] = None
    conn = _get_conn()
    try:
        # Build SET clause from allowed fields
        allowed = [
            'internal_description', 'output_title', 'output_notes', 'output_guidance',
            'unit_cost', 'units', 'pricing_visibility', 'quantity_source', 'pricing_mode',
            'form_visible', 'category', 'include_default',
            'is_follow_up', 'follow_up_type', 'follow_up_config',
            'output_group', 'override_output_group',
        ]
        sets = []
        params = []
        for key in allowed:
            if key in data:
                sets.append(f'{key} = ?')
                params.append(data[key])
        # Cost group total fields & sow_level: store in metadata_json
        if 'cost_group_id' in data or 'cost_group_override' in data or 'sow_level' in data:
            existing_row = conn.execute("SELECT metadata_json FROM line_items WHERE id = ?", (item_id,)).fetchone()
            existing_meta = {}
            if existing_row and existing_row[0]:
                try:
                    existing_meta = json.loads(existing_row[0]) if isinstance(existing_row[0], str) else existing_row[0]
                except Exception:
                    existing_meta = {}
            if not isinstance(existing_meta, dict):
                existing_meta = {}
            if 'cost_group_id' in data:
                existing_meta['cost_group_id'] = data['cost_group_id']
            if 'cost_group_override' in data:
                try:
                    existing_meta['cost_group_override'] = float(data['cost_group_override']) if data['cost_group_override'] else ''
                except (TypeError, ValueError):
                    existing_meta['cost_group_override'] = ''
            if 'sow_level' in data:
                try:
                    existing_meta['sow_level'] = int(data['sow_level']) if data['sow_level'] != '' else ''
                except (TypeError, ValueError):
                    existing_meta['sow_level'] = ''
            sets.append('metadata_json = ?')
            params.append(json.dumps(existing_meta))
        if 'pricing_matrix_types' in data or 'pricing_matrix_sizes' in data or 'pricing_matrix_prices' in data:
            types_list = [t.strip() for t in (data.get('pricing_matrix_types') or '').splitlines() if t.strip()]
            sizes_list = [s.strip() for s in (data.get('pricing_matrix_sizes') or '').splitlines() if s.strip()]
            prices_list = []
            prices_raw = data.get('pricing_matrix_prices')
            if prices_raw:
                try:
                    parsed = json.loads(prices_raw)
                    if isinstance(parsed, list):
                        prices_list = parsed
                except Exception:
                    prices_list = []
            price_matrix = {'types': types_list, 'sizes': sizes_list, 'prices': prices_list}
            sets.append('price_matrix = ?')
            params.append(json.dumps(price_matrix))
        elif data.get('pricing_mode') and data.get('pricing_mode') != 'matrix':
            sets.append('price_matrix = ?')
            params.append(None)
        if not sets:
            return jsonify({'ok': False, 'error': 'No fields to update'}), 400
        params.append(item_id)
        conn.execute(
            f"UPDATE line_items SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params
        )
        conn.commit()

        question_images = data.get('question_images') or []
        if not isinstance(question_images, list):
            question_images = [question_images] if question_images else []
        question_images = [str(u).strip() for u in question_images if str(u).strip()]
        seen = set()
        deduped = []
        for u in question_images:
            if u not in seen:
                seen.add(u)
                deduped.append(u)
        question_images = deduped

        # Sync question_images — detect the active schema. PostgreSQL uses
        # the newer question_template_id/image_path/image_order; legacy SQLite
        # databases use line_item_id/image_url/sort_order.
        legacy_qi = False
        try:
            conn.execute("DELETE FROM question_images WHERE question_template_id = ?", (item_id,))
        except Exception:
            conn.rollback()
            conn.execute("DELETE FROM question_images WHERE line_item_id = ?", (item_id,))
            legacy_qi = True
        for idx, url in enumerate(question_images):
            if legacy_qi:
                conn.execute(
                    "INSERT INTO question_images (line_item_id, image_url, sort_order) VALUES (?, ?, ?)",
                    (item_id, url, idx)
                )
            else:
                conn.execute(
                    "INSERT INTO question_images (question_template_id, image_path, image_order) VALUES (?, ?, ?)",
                    (item_id, url, idx)
                )
        conn.commit()

        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/question_images', methods=['POST'])
@require_role('admin')
def builder_question_images():
    """Save/update images for a question (line item)."""
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    line_item_id = data.get('line_item_id')
    images = data.get('images') or []
    if not isinstance(images, list):
        images = [images] if images else []
    images = [str(u).strip() for u in images if str(u).strip()]
    seen = set()
    deduped = []
    for u in images:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    images = deduped

    if line_item_id is None:
        return jsonify({'success': False, 'error': 'line_item_id is required'}), 400

    conn = _get_conn()
    try:
        # Detect the active question_images schema (new PG vs legacy SQLite)
        legacy_qi = False
        try:
            conn.execute("DELETE FROM question_images WHERE question_template_id = ?", (line_item_id,))
        except Exception:
            conn.rollback()
            conn.execute("DELETE FROM question_images WHERE line_item_id = ?", (line_item_id,))
            legacy_qi = True
        for idx, url in enumerate(images):
            if legacy_qi:
                conn.execute(
                    "INSERT INTO question_images (line_item_id, image_url, sort_order) VALUES (?, ?, ?)",
                    (line_item_id, url, idx)
                )
            else:
                conn.execute(
                    "INSERT INTO question_images (question_template_id, image_path, image_order) VALUES (?, ?, ?)",
                    (line_item_id, url, idx)
                )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
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
        conn = _get_conn()
        

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

    except Exception as e:
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()


def _row_to_item(row: dict) -> dict:
    item = dict(row)
    price_matrix_raw = item.get('price_matrix')
    if price_matrix_raw:
        try:
            price_matrix = json.loads(price_matrix_raw) if isinstance(price_matrix_raw, str) else price_matrix_raw
            if isinstance(price_matrix, dict):
                item.setdefault('pricing_options', {})
                item['pricing_options']['matrix_types'] = price_matrix.get('types', [])
                item['pricing_options']['matrix_sizes'] = price_matrix.get('sizes', [])
                item['pricing_options']['matrix_prices'] = price_matrix.get('prices', [])
        except Exception:
            pass
    meta_raw = item.get('metadata_json')
    if meta_raw:
        try:
            parsed = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
            if isinstance(parsed, dict):
                item['metadata'] = parsed
        except Exception:
            pass
    item['question_images'] = get_question_images_for_line_item(item.get('id'))
    return item


@app.route('/builder_beta/line_items_json')
@require_role('admin')
def builder_line_items_json():
    """Return line items grouped by category for a given page."""
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    page = request.args.get('page', '')
    category = request.args.get('category', '')
    conn = _get_conn()
    
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM line_items WHERE form_page = ? AND category = ? ORDER BY sort_order",
                [page, category]
            ).fetchall()
            categories = [{'name': category, 'items': [_row_to_item(dict(r)) for r in rows]}]
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
                    {'name': cr['category'], 'items': [_row_to_item(dict(r)) for r in rows]})
        return jsonify({'categories': categories})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/categories_for_page')
@require_role('admin')
def builder_categories_for_page():
    """Return distinct category names for a given page_key."""
    page_key = request.args.get('page_key', '').strip()
    if not page_key:
        return jsonify({'categories': []})
    conn = _get_conn()
    try:
        cat_rows = conn.execute(
            "SELECT DISTINCT ct.name FROM category_templates ct "
            "JOIN page_templates pt ON pt.id = ct.page_template_id "
            "JOIN form_template_versions ftv ON ftv.id = pt.form_template_version_id "
            "JOIN form_templates ft ON ft.id = ftv.form_template_id "
            "WHERE pt.page_key = ? AND ft.key = ? "
            "ORDER BY ct.name",
            [page_key, TEMPLATE_STORE_KEY],
        ).fetchall()
        categories = [{'name': r['name']} for r in cat_rows]
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
    conn = _get_conn()
    
    try:
        # Get latest version id
        latest_version_row = conn.execute(
            """
            SELECT ftv.id
            FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            ORDER BY ftv.version DESC
            LIMIT 1
            """,
            (TEMPLATE_STORE_KEY,)
        ).fetchone()
        latest_version_id = int(latest_version_row[0]) if latest_version_row else None
        if latest_version_id is None:
            return jsonify({'error': 'Template version not found'}), 404

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
        elif scope == 'module_block':
            # Reorder a module block relative to its neighbours in the
            # blocks list (which may be other blocks or modules).
            if not page_key:
                return jsonify({'error': 'page_key is required for module_block scope'}), 400
            if not identifier:
                return jsonify({'error': 'identifier (block_type) is required'}), 400
            bb_pages = page_schemas.setdefault('builder_beta', {}).setdefault('pages', {})
            pg = bb_pages.get(page_key)
            if not pg:
                return jsonify({'error': 'Page not found'}), 404
            blocks = pg.get('blocks', [])
            # Find current block — prefer exact block id (injected module
            # buttons now send it), fall back to block_type for legacy buttons
            # (multiple cost_group_section blocks share the same block_type).
            cur_idx = None
            for i, b in enumerate(blocks):
                if b.get('id') == identifier:
                    cur_idx = i
                    break
            if cur_idx is None:
                for i, b in enumerate(blocks):
                    if b.get('block_type') == identifier:
                        cur_idx = i
                        break
            if cur_idx is None:
                return jsonify({'error': f'No block with type "{identifier}" found'}), 404
            swap_idx = cur_idx - 1 if direction == 'up' else cur_idx + 1
            if swap_idx < 0 or swap_idx >= len(blocks):
                return jsonify({'error': 'Already at edge — cannot move further'}), 400
            # Swap the two blocks
            blocks[cur_idx], blocks[swap_idx] = blocks[swap_idx], blocks[cur_idx]
            save_page_schemas()
            return jsonify({'success': True})
        elif scope == 'category':
            # Swap category order using the deduplicated category list
            # (same as the UI). This handles categories that exist in
            # multiple template versions with inconsistent display_orders.
            if not page_key:
                return jsonify({'error': 'page_key is required for category scope'}), 400

            import sys
            print(f"[SWAP_DEBUG] request payload: scope={scope!r} identifier={identifier!r} direction={direction!r} page_key={page_key!r}", file=sys.stderr)

            # Get all category rows across all versions, deduplicated by name
            cat_rows = conn.execute(
                """SELECT c.name, c.display_order, c.id
                   FROM category_templates c
                   JOIN page_templates pt ON pt.id = c.page_template_id
                   WHERE pt.page_key = ?
                   ORDER BY c.display_order ASC, c.id ASC""",
                [page_key]
            ).fetchall()

            seen = set()
            cat_list = []
            for row in cat_rows:
                if row['name'] not in seen:
                    seen.add(row['name'])
                    cat_list.append(row)

            identifier = (identifier or '').strip()
            if not identifier:
                return jsonify({'error': 'identifier is required for category scope'}), 400
            
            # Find current category index (match by exact name, stripped name, or id)
            cur_idx = None
            for i, cat in enumerate(cat_list):
                if (cat['name'] == identifier or 
                    cat['name'].strip().lower() == identifier.strip().lower() or
                    str(cat['id']) == str(identifier)):
                    cur_idx = i
                    break

            if cur_idx is None:
                cat_name = identifier.strip()
                page_row = conn.execute(
                    "SELECT id FROM page_templates WHERE form_template_version_id = ? AND page_key = ?",
                    (latest_version_id, page_key)
                ).fetchone()
                if page_row:
                    existing = conn.execute(
                        "SELECT id FROM category_templates WHERE page_template_id = ? AND name = ?",
                        (page_row["id"], cat_name)
                    ).fetchone()
                    if not existing:
                        max_order_row = conn.execute(
                            "SELECT MAX(display_order) as max_order FROM category_templates WHERE page_template_id = ?",
                            (page_row["id"],)
                        ).fetchone()
                        next_order = 0
                        if max_order_row and max_order_row["max_order"] is not None:
                            next_order = int(max_order_row["max_order"]) + 1
                        conn.execute(
                            "INSERT INTO category_templates (form_template_version_id, page_template_id, name, display_order, output_group) VALUES (?, ?, ?, ?, ?)",
                            (latest_version_id, page_row["id"], cat_name, next_order, "General")
                        )
                        conn.commit()
                        cat_rows = conn.execute(
                            """SELECT c.name, c.display_order, c.id
                               FROM category_templates c
                               JOIN page_templates pt ON pt.id = c.page_template_id
                               WHERE pt.page_key = ?
                               ORDER BY c.display_order ASC, c.id ASC""",
                            [page_key]
                        ).fetchall()
                        seen = set()
                        cat_list = []
                        for row in cat_rows:
                            if row['name'] not in seen:
                                seen.add(row['name'])
                                cat_list.append(row)
                        for i, cat in enumerate(cat_list):
                            if cat['name'] == identifier or cat['name'].strip().lower() == identifier.strip().lower():
                                cur_idx = i
                                break
                if cur_idx is None:
                    return jsonify({'error': 'Category not found'}), 404

            # Find adjacent category
            if direction == 'up':
                adj_idx = cur_idx - 1
            else:
                adj_idx = cur_idx + 1

            if adj_idx < 0 or adj_idx >= len(cat_list):
                import sys
                print(f"[SWAP_DEBUG] page_key={page_key!r} identifier={identifier!r} direction={direction!r} cur_idx={cur_idx} len={len(cat_list)} cats={[c['name'] for c in cat_list]}", file=sys.stderr)
                return jsonify({'error': 'No adjacent category'}), 400

            cur_cat = cat_list[cur_idx]
            adj_cat = cat_list[adj_idx]

            # Reorder the deduplicated list, then renumber display_order
            # sequentially (0,1,2,...) for every category name across ALL
            # versions. Simply swapping raw display_order values fails when
            # two categories share the same display_order (e.g. "Summary"
            # and "Basement" both = 2), which made swaps a no-op.
            cat_list[cur_idx], cat_list[adj_idx] = cat_list[adj_idx], cat_list[cur_idx]
            for new_order, cat in enumerate(cat_list):
                conn.execute(
                    "UPDATE category_templates SET display_order = ? WHERE name = ? AND page_template_id IN (SELECT id FROM page_templates WHERE page_key = ?)",
                    [new_order, cat['name'], page_key]
                )

            conn.commit()
            return jsonify({'success': True})
        elif scope == 'module':
            # Swap module order in metadata_json.modules list
            if not page_key:
                return jsonify({'error': 'page_key is required for module scope'}), 400
            import json as _j
            existing = conn.execute(
                "SELECT metadata_json FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
                [page_key, latest_version_id]
            ).fetchone()
            meta = {}
            if existing and existing[0]:
                try: meta = _j.loads(existing[0]) if isinstance(existing[0], str) else existing[0]
                except: meta = {}
            if not isinstance(meta, dict): meta = {}
            modules = meta.get('modules', [])
            if not modules:
                return jsonify({'error': 'No modules to reorder'}), 400
            # Find current module index
            mod_type = (identifier or '').strip()
            cur_idx = None
            for i, m in enumerate(modules):
                if m == mod_type:
                    cur_idx = i
                    break
            if cur_idx is None:
                return jsonify({'error': f'Module {mod_type} not found'}), 404
            # Find adjacent module index
            adj_idx = cur_idx - 1 if direction == 'up' else cur_idx + 1
            if adj_idx < 0 or adj_idx >= len(modules):
                return jsonify({'success': True}), 200
            # Swap
            modules[cur_idx], modules[adj_idx] = modules[adj_idx], modules[cur_idx]
            meta['modules'] = modules
            conn.execute(
                "UPDATE page_templates SET metadata_json = ? WHERE page_key = ? AND form_template_version_id = ?",
                [_j.dumps(meta), page_key, latest_version_id]
            )
            conn.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Unknown scope: {scope}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/builder_beta/page/reorder', methods=['POST'])
@require_role('admin')
def builder_page_reorder():
    """Swap display_order of two adjacent pages."""
    import sqlite3
    from pathlib import Path
    db = str(Path(__file__).parent / 'template_store.sqlite3')
    data = request.get_json(force=True) or {}
    page_key = data.get('page_key')
    direction = data.get('direction', 'up')

    if not page_key:
        return jsonify({'error': 'page_key is required'}), 400

    conn = _get_conn()
    
    try:
        latest_version_row = conn.execute(
            """
            SELECT ftv.id
            FROM form_template_versions ftv
            JOIN form_templates ft ON ft.id = ftv.form_template_id
            WHERE ft.key = ?
            ORDER BY ftv.version DESC
            LIMIT 1
            """,
            (TEMPLATE_STORE_KEY,),
        ).fetchone()
        latest_version_id = int(latest_version_row[0]) if latest_version_row else None
        if latest_version_id is None:
            return jsonify({'error': 'Template version not found'}), 404

        cur = conn.execute(
            "SELECT id, display_order FROM page_templates WHERE page_key = ? AND form_template_version_id = ?",
            [page_key, latest_version_id]
        ).fetchone()
        if not cur:
            return jsonify({'error': 'Page not found'}), 404
        cur_order = cur['display_order']

        op = '<' if direction == 'up' else '>'
        order = 'DESC' if direction == 'up' else 'ASC'
        adj = conn.execute(
            f"SELECT id, display_order FROM page_templates WHERE display_order {op} ? AND form_template_version_id = ? ORDER BY display_order {order} LIMIT 1",
            [cur_order, latest_version_id]
        ).fetchone()
        if not adj:
            return jsonify({'error': 'No adjacent page'}), 400

        conn.execute(
            "UPDATE page_templates SET display_order = ? WHERE id = ?",
            [adj['display_order'], cur['id']]
        )
        conn.execute(
            "UPDATE page_templates SET display_order = ? WHERE id = ?",
            [cur_order, adj['id']]
        )
        conn.commit()

        # Auto-sync navigation metadata in page_schemas
        try:
            _sync_page_schemas_navigation_after_reorder(page_key, direction)
        except Exception:
            pass

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


def _sync_page_schemas_navigation_after_reorder(moved_page_key, direction):
    """Update page_schemas navigation metadata and page order after a page reorder."""
    global page_schemas
    ordered_pages = get_all_pages(template_key=TEMPLATE_STORE_KEY)
    page_keys = [pg['page_key'] for pg in ordered_pages]

    if moved_page_key not in page_keys:
        return

    idx = page_keys.index(moved_page_key)
    prev_key = page_keys[idx - 1] if idx > 0 else None
    next_key = page_keys[idx + 1] if idx < len(page_keys) - 1 else None

    for pid in [moved_page_key, prev_key, next_key]:
        if pid and pid in page_schemas.get('pages', {}):
            page_schemas['pages'][pid].setdefault('navigation', {})
            nav = page_schemas['pages'][pid]['navigation']
            if pid == moved_page_key:
                nav['previous_endpoint'] = prev_key or ''
                nav['next_endpoint'] = next_key or 'review'
            elif pid == prev_key:
                nav['next_endpoint'] = moved_page_key
            elif pid == next_key:
                nav['previous_endpoint'] = moved_page_key

    # Also sync in builder_beta.pages if present
    builder_pages = page_schemas.get('builder_beta', {}).get('pages', {})
    for pid in [moved_page_key, prev_key, next_key]:
        if pid and pid in builder_pages:
            builder_pages[pid].setdefault('navigation', {})
            nav = builder_pages[pid]['navigation']
            if pid == moved_page_key:
                nav['previous_endpoint'] = prev_key or ''
                nav['next_endpoint'] = next_key or 'review'
            elif pid == prev_key:
                nav['next_endpoint'] = moved_page_key
            elif pid == next_key:
                nav['previous_endpoint'] = moved_page_key

    # Reorder page dicts to match new DB order so Quick Save preserves it
    pages_dict = page_schemas.get('pages', {})
    reordered = {k: pages_dict[k] for k in page_keys if k in pages_dict}
    if reordered:
        page_schemas['pages'] = reordered

    builder_pages_dict = page_schemas.get('builder_beta', {}).get('pages', {})
    reordered_builder = {k: builder_pages_dict[k] for k in page_keys if k in builder_pages_dict}
    if reordered_builder:
        page_schemas['builder_beta']['pages'] = reordered_builder

    save_page_schemas()


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
    session_overrides = session.get('session_overrides', {}) or {}
    cg_overrides = session_overrides.get('cg_overrides', {}) or {}
    li_overrides = session_overrides.get('overrides', {}) or {}
    units_overrides = session_overrides.get('units_overrides', {}) or {}
    return {
        "client_address": data.get("client_address", ""),
        "proposal_date": data.get("Date", ""),
        "quote_ref": data.get("quote_ref", ""),
        "client_name": data.get("client_name", ""),
        "_session_cg_overrides_json": json.dumps(cg_overrides),
        "_session_li_overrides_json": json.dumps(li_overrides),
        "_session_units_overrides_json": json.dumps(units_overrides),
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

    # Check form_visible — redirect to next visible page if hidden
    vis = _get_page_visibility(page_id)
    if not vis.get('form_visible', True):
        # Find the next visible page to redirect to
        import template_store as _ts_nav
        ordered = _ts_nav.get_all_pages(template_key=TEMPLATE_STORE_KEY)
        next_key = None
        found = False
        for pg in ordered:
            if found and _get_page_visibility(pg['page_key']).get('form_visible', True):
                next_key = pg['page_key']
                break
            if pg['page_key'] == page_id:
                found = True
        if not next_key:
            next_key = 'review'
        return redirect(url_for('dynamic_page', page_id=next_key))

    session['last_visited'] = page_id
    # Auto-restore from saved form session on first load
    if request.method == 'GET' and not session.get('_auto_restored'):
        try:
            import template_store as _ts_load
            _conn_load = _ts_load._connect()
            cur = _conn_load.cursor()
            ph = '%s' if _ts_load._get_db_backend() == 'postgres' else '?'
            cur.execute(f'SELECT session_data FROM saved_sessions WHERE name = {ph} ORDER BY created_at DESC LIMIT 1', ('_auto_form_save',))
            _row_load = cur.fetchone()
            cur.close()
            if _row_load:
                loaded = json.loads(_row_load[0])
                session.setdefault('data', {}).update(loaded.get('data', {}))
                session.setdefault('checkbox_data', {}).update(loaded.get('checkbox_data', {}))
                session.setdefault('session_overrides', {}).update(loaded.get('session_overrides', {}))
                if loaded.get('template_key'):
                    session['template_key'] = loaded['template_key']
                session['_auto_restored'] = True
                session.modified = True
            _conn_load.close()
        except Exception:
            pass
    page = all_pages[page_id]
    page_schema = compile_builder_beta_page_to_runtime_schema(page_id)
    if page_schema is None:
        abort(500)

    checkbox_data = session.setdefault('checkbox_data', {})

    form_data = session.setdefault('data', {})
    _apply_conditional_visibility(page_schema, form_data, checkbox_data)
    if request.method == 'POST':
        for block in page.get('blocks', []):
            field_name = block.get('standard', {}).get('name') or block.get('id')
            if not field_name:
                continue
            if block['block_type'] in ('checkbox_group', 'line_items_by_category'):
                selected = request.form.getlist(field_name)
                checkbox_data[field_name] = {'preselected': selected}
            else:
                value = request.form.get(field_name, '')
                form_data[field_name] = value
        for key in request.form.keys():
            if key.startswith('follow_up_'):
                values = request.form.getlist(key)
                if '_price_' in key or key.endswith('_price'):
                    checkbox_data[key] = values[0] if values else ''
                else:
                    checkbox_data[key] = values if len(values) > 1 else (values[0] if values else '')
        
        # Handle line item price overrides (named like {field_name}_price_{line_code})
        # Only confirmed prices are submitted (unconfirmed inputs are disabled via JS)
        session_overrides = session.setdefault('session_overrides', {})
        overrides = session_overrides.setdefault('overrides', {})
        for key, val in request.form.items():
            if '_price_' in key:
                # Extract line_code from key: {field_name}_price_{line_code}
                # We need to look up the item_id from the line_code
                try:
                    line_code = key.split('_price_')[-1]
                    # Look up item_id from line_items table
                    import template_store as _ts_li
                    db_path = _ts_li._default_db_path()
                    _conn = _ts_li._connect(db_path)
                    row = _conn.execute(
                        "SELECT id FROM line_items WHERE line_code = ? LIMIT 1",
                        (line_code,)
                    ).fetchone()
                    _conn.close()
                    if row and val not in ('', None):
                        overrides[str(row['id'])] = float(val)
                except Exception:
                    pass
        
        session['checkbox_data'] = checkbox_data
        session['data'] = form_data
        session['session_overrides'] = session_overrides
        session.modified = True

        # ── Auto-save form progress to DB on every submit ──────────────
        try:
            import template_store as _ts_save
            _conn_save = _ts_save._connect()
            if _ts_save._get_db_backend() == 'postgres':
                _conn_save.execute('''
                    CREATE TABLE IF NOT EXISTS saved_sessions (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        session_data TEXT NOT NULL,
                        user_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                _conn_save.commit()
            else:
                _conn_save.execute('''
                    CREATE TABLE IF NOT EXISTS saved_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        session_data TEXT NOT NULL,
                        user_id INTEGER,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            data_to_save = {
                'data': form_data,
                'checkbox_data': checkbox_data,
                'session_overrides': session_overrides,
                'template_key': session.get('template_key'),
            }
            cur = _conn_save.cursor()
            is_pg = _ts_save._get_db_backend() == 'postgres'
            ph = '%s' if is_pg else '?'
            cur.execute(f'SELECT id FROM saved_sessions WHERE name = {ph} ORDER BY created_at DESC LIMIT 1', ('_auto_form_save',))
            existing = cur.fetchone()
            if existing:
                cur.execute(f'UPDATE saved_sessions SET session_data = {ph}, created_at = CURRENT_TIMESTAMP WHERE id = {ph}',
                            (json.dumps(data_to_save), existing[0]))
            else:
                cur.execute(f'INSERT INTO saved_sessions (name, session_data, user_id) VALUES ({ph}, {ph}, {ph})',
                            ('_auto_form_save', json.dumps(data_to_save), session.get('user_id')))
            _conn_save.commit()
            cur.close()
            _conn_save.close()
        except Exception:
            pass

        # ── Form → Quote live sync ──────────────────────────────────────
        active_quote_id = session.get('active_quote_id')
        if active_quote_id:
            try:
                from quote_editor_routes import get_saved_quote, update_saved_quote
                quote = get_saved_quote(int(active_quote_id), session.get('template_key') or TEMPLATE_STORE_KEY)
                if quote:
                    blocks = quote.get('blocks_json', [])
                    needs_calc = False
                    for block in blocks:
                        if not block.get('source_page') or not block.get('source_block_id'):
                            continue
                        if block.get('flags', {}).get('editor_dirty'):
                            continue
                        source_block_id = block['source_block_id']
                        block_type = block.get('type')
                        if block_type == 'page_title':
                            pass
                        elif block_type == 'page_heading':
                            pass
                        elif block_type == 'form_question':
                            # Line items are the only form_question blocks in quote mode.
                            # Their values come from the DB build (output_notes + output_guidance),
                            # not from form session data — skip sync to preserve them.
                            continue
                    # Recalculate calculator/payment_schedule blocks if form data changed
                    if needs_calc:
                        try:
                            import calculator
                            calc_result = calculator.calculate_quote(
                                session.get('template_key') or TEMPLATE_STORE_KEY,
                                session.get('data', {}),
                                session.get('session_overrides', {}),
                                session.get('checkbox_data', {}),
                            )
                            for block in blocks:
                                bt = block.get('type')
                                if bt in ('calculator', 'payment_schedule') and not block.get('flags', {}).get('editor_dirty'):
                                    block['snapshot'] = calc_result
                                    block['flags'] = block.get('flags', {})
                                    block['flags']['source_dirty'] = True
                        except Exception:
                            pass
                    update_saved_quote(
                        quote_id=int(active_quote_id),
                        form_key=session.get('template_key') or TEMPLATE_STORE_KEY,
                        name=quote.get('name', 'Quote'),
                        blocks_json=blocks,
                        settings=quote.get('settings_json', {}),
                        form_data={'data': session.get('data', {}), 'checkbox_data': session.get('checkbox_data', {}), 'template_key': session.get('template_key') or TEMPLATE_STORE_KEY},
                    )
            except Exception:
                pass
        # ── End Form → Quote sync ───────────────────────────────────────

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
        saved_cb = session.get('checkbox_data', {})
        session_overrides = session.get('session_overrides', {}).get('overrides', {})
        for field in page_schema.get('fields', []):
            if field.get('type') == 'line_items_by_category':
                field_name = field.get('name') or field.get('id')
                _saved = saved_cb.get(field_name)
                if isinstance(_saved, dict):
                    _saved = _saved.get('preselected', [])
                if not isinstance(_saved, list):
                    _saved = []
                _li_raw = _get_line_items_for_page(page_id)
                if isinstance(_li_raw, dict):
                    li_groups_data = [
                        {'category': c, 'items': [
                            {'value': r.get('line_code', ''),
                             'label': r.get('internal_description') or '',
                             'unit_cost': r.get('unit_cost', 0),
                             'units': r.get('units', 1),
                             'allow_user_override': r.get('allow_user_override', 0),
                             'pricing_visibility': r.get('pricing_visibility', 'admin_only'),
                             'id': r.get('id'),
                             'include_default': r.get('include_default') or 'N',
                             'is_follow_up': r.get('is_follow_up') or 0,
                             'follow_up_type': r.get('follow_up_type') or '',
                             'follow_up_config': r.get('follow_up_config') or '{}',
                             'checked': (r.get('line_code', '') in _saved) if _saved else (r.get('include_default') == 'Y'),
                             'saved_override': session_overrides.get(str(r.get('id')), '')}
                            for r in v
                        ]}
                        for c, v in _li_raw.items()
                    ]
                    # Exclude groups with no items
                    li_groups_data = [g for g in li_groups_data if g['items']]
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
        # Edit mode needs the same builder context the POST branch passes:
        # builder_state drives the question-type picker, db_pages the sidebar
        # page selector. Without these the type list is empty on this route.
        edit_mode=bool(request.args.get('edit') == '1'),
        builder_state=get_builder_beta_state(),
        db_pages=get_all_pages(template_key=TEMPLATE_STORE_KEY),
        saved_form_data=session.get('checkbox_data', {}),
        **_get_runtime_quote_context()
    )

@app.route('/', methods=['POST', 'GET'])
def index():
    session['last_visited'] = 'index'

    # ── Auto-restore the latest saved quote on first load ──────────────
    if not session.get('data') and request.method == 'GET':
        try:
            import template_store as _ts_r
            _conn_r = _ts_r._connect(_ts_r._default_db_path())
            _row_r = _conn_r.execute(
                "SELECT id, form_data FROM saved_quotes ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if _row_r and _row_r['form_data']:
                import json
                fd = json.loads(_row_r['form_data']) if isinstance(_row_r['form_data'], str) else _row_r['form_data']
                if isinstance(fd, dict):
                    session['data'] = fd.get('data', {})
                    # Do NOT restore checkbox_data — the user should start
                    # fresh; old preselected items would show as "selected"
                    # in the cost group accordion even though the user never
                    # checked anything in this session.
                    session['checkbox_data'] = {}
                    session['active_quote_id'] = int(_row_r['id'])
                    session['template_key'] = fd.get('template_key', session.get('template_key') or TEMPLATE_STORE_KEY)
                    session.modified = True
            _conn_r.close()
        except Exception:
            pass

    # Get the first DYNAMIC page by display_order (skip redundant index page)
    ordered_pages = get_all_pages(template_key=TEMPLATE_STORE_KEY)
    dynamic_page_ids = [pg['page_key'] for pg in ordered_pages if pg['page_key'] != 'index']
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

    elif action == 'duplicate_block':
        duplicate_id = (form_data.get('block_id') or '').strip()
        duplicate_index, source_block = _find_block(page, duplicate_id)
        if source_block is None:
            warnings.append('Block to duplicate was not found.')
        else:
            import copy
            new_block = copy.deepcopy(source_block)
            timestamp = int(time.time() * 1000)
            new_block['id'] = f'{page_id}__{new_block["block_type"]}_{timestamp}'
            if 'standard' in new_block:
                new_block['standard']['label'] = new_block['standard'].get('label', '') + ' (copy)'
                new_block['standard']['name'] = new_block['id']
            insert_index = duplicate_index + 1
            page['blocks'].insert(insert_index, new_block)
            selected_block_id = new_block['id']

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

        nav = resolve_builder_beta_navigation_targets('image_upload_page', builder_state.get('pages', {}).get('image_upload_page', {}))
        return render_template(
            'form.html',
            page_schema=page_schema,
            schema_render_mode='full',
            previous_page=nav.get('previous_page_id') or 'optional_extras_page',
            next_page=nav.get('next_page_id') or 'review',
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
        builder_state = get_builder_beta_state()
        nav = resolve_builder_beta_navigation_targets('image_upload_page', builder_state.get('pages', {}).get('image_upload_page', {}))
        return render_template(
            'image_upload.html',
            image_upload_page=True,
            previous_page=nav.get('previous_page_id') or 'optional_extras_page',
            next_page=nav.get('next_page_id') or 'review',
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
        # ── Review → Quote live sync ────────────────────────────────────
        active_quote_id = session.get('active_quote_id')
        if active_quote_id:
            try:
                from quote_editor_routes import get_saved_quote, update_saved_quote
                quote = get_saved_quote(int(active_quote_id), session.get('template_key') or TEMPLATE_STORE_KEY)
                if quote:
                    blocks = quote.get('blocks_json', [])
                    for block in blocks:
                        if block.get('flags', {}).get('editor_dirty'):
                            continue
                        if block.get('type') == 'form_question':
                            # Line items are the only form_question blocks in quote mode.
                            # Their values come from the DB build (output_notes + output_guidance),
                            # not from form session data — skip sync to preserve them.
                            continue
                    try:
                        import calculator
                        calc_result = calculator.calculate_quote(
                            session.get('template_key') or TEMPLATE_STORE_KEY,
                            session.get('data', {}),
                            session.get('session_overrides', {}),
                            session.get('checkbox_data', {}),
                        )
                        for block in blocks:
                            bt = block.get('type')
                            if bt in ('calculator', 'payment_schedule') and not block.get('flags', {}).get('editor_dirty'):
                                block['snapshot'] = calc_result
                                block.setdefault('flags', {})['source_dirty'] = True
                    except Exception:
                        pass
                    update_saved_quote(
                        quote_id=int(active_quote_id),
                        form_key=session.get('template_key') or TEMPLATE_STORE_KEY,
                        name=quote.get('name', 'Quote'),
                        blocks_json=blocks,
                        settings=quote.get('settings_json', {}),
                        form_data={'data': session.get('data', {}), 'checkbox_data': session.get('checkbox_data', {}), 'template_key': session.get('template_key') or TEMPLATE_STORE_KEY},
                    )
            except Exception:
                pass
        # ── End Review → Quote sync ─────────────────────────────────────
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
            cb_val = checkbox_data.get(field_name)
            block_type = field.get('builder_beta_meta', {}).get('block_type', field.get('type', 'unknown'))

            # Collect codes from BOTH session_data and checkbox_data.
            # session_data may store only the first value as a string
            # (from request.form.get()), while checkbox_data stores all
            # values as {'preselected': [...]} (from request.form.getlist()).
            # Using only one source means some codes never get labels resolved.
            codes = []

            if value:
                if isinstance(value, (list, tuple)):
                    codes.extend(v.strip() for v in value if isinstance(v, str) and v.strip())
                elif isinstance(value, str) and value.strip():
                    codes.append(value.strip())

            if cb_val:
                if isinstance(cb_val, dict):
                    codes.extend(v.strip() for v in cb_val.get('preselected', []) if isinstance(v, str) and v.strip())
                elif isinstance(cb_val, (list, tuple)):
                    codes.extend(v.strip() for v in cb_val if isinstance(v, str) and v.strip())
                elif isinstance(cb_val, str) and cb_val.strip():
                    codes.append(cb_val.strip())

            if codes:
                selected_codes.update(codes)
                section_fields[field_name] = codes
            elif block_type == 'line_items_by_category':
                # Autochecked fallback: load items with include_default = 'Y'
                # from DB when user hasn't visited/submitted this page yet.
                try:
                    conn = _get_conn()
                    latest_version_row = conn.execute(
                        """
                        SELECT ftv.id
                        FROM form_template_versions ftv
                        JOIN form_templates ft ON ft.id = ftv.form_template_id
                        WHERE ft.key = ?
                        ORDER BY ftv.version DESC
                        LIMIT 1
                        """,
                        (TEMPLATE_STORE_KEY,)
                    ).fetchone()
                    latest_version_id = int(latest_version_row[0]) if latest_version_row else None
                    if latest_version_id is not None:
                        default_rows = conn.execute(
                            """
                            SELECT li.line_code
                            FROM line_items li
                            WHERE li.form_page = ? AND li.include_default = 'Y'
                            """,
                            [page_id]
                        ).fetchall()
                        conn.close()
                        default_codes = [r['line_code'].strip() for r in default_rows if r['line_code']]
                        if default_codes:
                            selected_codes.update(default_codes)
                            section_fields[field_name] = default_codes
                except Exception:
                    pass

        if section_fields:
            title = page_info.get('title') or page_id.replace('_', ' ').title()
            raw_sections[title] = section_fields

    # Resolve line codes → human-readable labels AND categories
    line_code_labels = {}
    line_code_categories = {}
    if selected_codes:
        try:
            conn = _get_conn()
            # Fetch all line items once and filter in Python.
            # Using IN with a list parameter does NOT work on PostgreSQL:
            # psycopg2 adapts a Python list as a single PostgreSQL array
            # parameter rather than expanding it into multiple placeholders,
            # so WHERE line_code IN (?,?,?) with ['a','b','c'] becomes
            # WHERE line_code IN ('{a,b,c}') which compares text to an array
            # and returns zero rows.
            all_rows = conn.execute(
                "SELECT line_code, output_title, internal_description FROM line_items"
            ).fetchall()
            row_map = {}
            for r in all_rows:
                lc = r['line_code']
                if lc:
                    row_map[lc.strip()] = r
            for code in selected_codes:
                row = row_map.get(code)
                if row:
                    try:
                        label = row['internal_description'] or row['output_title'] or row['line_code']
                        line_code_labels[code] = label
                        category = (row['output_title'] or '').rstrip(':').strip()
                        line_code_categories[code] = category
                    except Exception:
                        continue
            conn.close()
        except Exception:
            pass
    # Fallback: if we have raw_value codes but no labels resolved, do individual lookups
    # This handles cases where selected_codes was empty but codes exist in review_data
    if not line_code_labels:
        try:
            conn = _get_conn()
            # Collect all codes from raw_sections
            all_codes = set()
            for _section_fields in raw_sections.values():
                for _val in _section_fields.values():
                    if isinstance(_val, (list, tuple)):
                        all_codes.update(v.strip() for v in _val if isinstance(v, str) and v.strip())
                    elif isinstance(_val, str) and _val.strip():
                        all_codes.add(_val.strip())
            if all_codes:
                all_rows = conn.execute(
                    "SELECT line_code, output_title, internal_description FROM line_items"
                ).fetchall()
                row_map = {}
                for r in all_rows:
                    lc = r['line_code']
                    if lc:
                        row_map[lc.strip()] = r
                for code in all_codes:
                    row = row_map.get(code)
                    if row:
                        try:
                            lc = row['line_code']
                            line_code_labels[lc] = row['internal_description'] or row['output_title'] or row['line_code']
                            line_code_categories[lc] = (row['output_title'] or '').rstrip(':').strip()
                        except Exception:
                            continue
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

            section_title = page_info.get('title') or page_id.replace('_', ' ').title()
            raw_value = raw_sections.get(section_title, {}).get(field_name)
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
    follow_up_data = session.get('checkbox_data', {})
    session_overrides = session.get('session_overrides', {})
    try:
        from calculator import calculate_quote
        context['result'] = calculate_quote(template_key, form_data, session_overrides, follow_up_data)
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
    conn = _get_conn(db_path)
    

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
        conn = _get_conn(db_path)
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


@app.route('/builder_beta/upload_image', methods=['POST'])
@require_role('admin')
def builder_upload_image():
    """Upload an image for the image_upload module. Returns the URL."""
    import os
    from werkzeug.utils import secure_filename
    project_title = session.get('data', {}).get('client_address', 'Unnamed_Project')
    safe_title = secure_filename(project_title)[:50]
    project_folder = os.path.join(app.config['UPLOAD_FOLDER'], safe_title)
    os.makedirs(project_folder, exist_ok=True)
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'Empty file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'File type not allowed (jpg, png, gif, jpeg only)'}), 400
    field_name = request.form.get('field_name', 'upload')
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{field_name}_{int(__import__('time').time())}.{ext}"
    save_path = os.path.join(project_folder, filename)
    file.save(save_path)
    url = url_for('static', filename=f'uploads/{safe_title}/{filename}')
    return jsonify({'success': True, 'url': url, 'filename': filename})

@app.route('/quote_editor', methods=['GET', 'POST'])
def quote_editor():
    if session.get('active_quote_id'):
        form_key = session.get('quote_editor_template_key', session.get('template_key') or TEMPLATE_STORE_KEY)
    else:
        form_key = session.get('template_key') or TEMPLATE_STORE_KEY
    layouts = []
    try:
        from template_store import list_quote_editor_layouts
        layouts = list_quote_editor_layouts(form_key)
    except Exception:
        pass
    pending_blocks = get_quote_editor_blocks()
    pending_block = session.get('quote_editor_pending_block', None)
    # Determine initial page index from ?page= query parameter
    page_key = request.args.get('page')
    initial_page_index = 0
    if page_key:
        try:
            ordered_pages = get_all_pages(template_key=form_key)
            page_dict = {p['page_key']: idx for idx, p in enumerate(ordered_pages)}
            if page_key in page_dict:
                initial_page_index = page_dict[page_key]
        except Exception:
            pass
    return render_template(
        'user_output_editor.html',
        form_key=form_key,
        layouts=layouts,
        pending_blocks=pending_blocks,
        pending_block=pending_block,
        initial_page_index=initial_page_index,
    )


@app.route('/save-load', methods=['GET', 'POST'])
def save_load():
    session['last_visited'] = 'save_load'
    db_path = str(Path(__file__).parent / 'template_store.sqlite3')
    saved = False
    loaded = False
    error = None
    saved_sessions = []
    conn = _get_conn(db_path)
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

    conn = _get_conn(db_path)
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


from merge_tags import get_merge_tag_values, replace_merge_tags
from quote_editor_routes import quote_editor_bp, build_quote_editor_blocks_for_all_pages, get_quote_editor_blocks
from quote_editor_export import quote_editor_export_bp
from export_routes import export_bp

csrf.exempt(quote_editor_bp)
app.register_blueprint(quote_editor_bp)
app.register_blueprint(quote_editor_export_bp)
app.register_blueprint(export_bp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
