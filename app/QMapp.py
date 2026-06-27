#!/usr/bin/env python3

# Built-in Modules
import os
import re
import subprocess
import time
import json
import functools
from datetime import datetime
from PIL import Image
import traceback
from typing import Optional

# Third-party Modules
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import gspread
from google.oauth2.service_account import Credentials
from templates import get_layout_definition, generate_template_svg
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
)
from config import (
    TEMPLATE_STORE_READ_ENABLED,
    TEMPLATE_STORE_KEY,
    TEMPLATE_STORE_DB_PATH,
    FLASK_SECRET_KEY,
)

app = Flask(__name__)
csrf = CSRFProtect(app)

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
app.config['SECRET_KEY'] = os.getenv('QM_SECRET_KEY', 'dev-insecure-key-change-me')

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
	os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize the session extension
Session(app)

#inject current user role and edit mode into every template context
@app.context_processor
def inject_ui_context():
	"""Inject auth and edit-mode state into every template context."""
	role = session.get('role')
	is_admin = role == 'admin'
	edit_requested = request.args.get('edit', '').lower() in {'1', 'true', 'yes'}
	edit_mode = is_admin and edit_requested
	
	db_pages = []
	if edit_mode:
		from template_store import get_all_pages
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
    Wraps template_store.get_line_items_for_page()."""
    try:
        return template_store.get_line_items_for_page(page_id)
    except Exception:
        return {}

#Get list of category names for a page from the schema, fallback to keys from get_line_items_for_page().
def _get_li_categories_from_schema(page_id: str):
    """Return list of category names for a page from the schema.
    Falls back to keys from get_line_items_for_page()."""
    try:
        items = template_store.get_line_items_for_page(page_id)
        return list(items.keys()) if items else []
    except Exception:
        return []

# Load layout intent metadata
intent_path = Path(__file__).parent / 'layout_intents.json'
with intent_path.open() as f:
	layout_intents = json.load(f)

# Load page schema metadata for builder-driven rendering.
page_schema_path = Path(__file__).parent / 'page_schemas.json'
with page_schema_path.open() as f:
	page_schemas = json.load(f)

# DO NOT OVERWRITE: config.py values already imported correctly above
# TEMPLATE_STORE_KEY and TEMPLATE_STORE_READ_ENABLED are imported from config.py
# To change template key, set env var QM_TEMPLATE_STORE_KEY (not QM_TEMPLATE_KEY)
print(f"[CONFIG] Using TEMPLATE_STORE_KEY={TEMPLATE_STORE_KEY}, READ_ENABLED={TEMPLATE_STORE_READ_ENABLED}")

try:
	template_store_bootstrap = initialize_template_store(page_schemas, template_key=TEMPLATE_STORE_KEY)
	print(
		"Template store ready:",
		f"pages={template_store_bootstrap.get('pages', 0)}",
		f"questions={template_store_bootstrap.get('questions', 0)}",
		f"db={template_store_bootstrap.get('db_path', '')}",
	)
except Exception as exc:
	template_store_bootstrap = {'error': str(exc)}
	print(f"Template store bootstrap skipped: {exc}")

# Sync catalog data (sheet rows -> option_sets / option_items) on every startup.
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
			print("Template store read enabled, but no payload found. Using JSON schema file.")
	except Exception as exc:
		print(f"Template store read failed, falling back to JSON schema: {exc}")

# Get/initialize builder settings dict from page_schemas
def get_builder_settings():
	settings = page_schemas.setdefault('settings', {})
	if not isinstance(settings, dict):
		settings = {}
		page_schemas['settings'] = settings
	return settings

#Legacy JSON persistence - still required for draft sync until builder write ops fully migrate to SQLite DB
def save_page_schemas():
	with page_schema_path.open('w') as f:
		json.dump(page_schemas, f, indent=2)

	# Keep Template Store in sync with latest builder edits (Phase 1/2 bootstrap path).
	try:
		initialize_template_store(page_schemas, template_key=TEMPLATE_STORE_KEY)
	except Exception as exc:
		print(f"Template store sync skipped after save: {exc}")

# Function patches field overrides (hidden, label, options) for a specific field in a page schema.
def save_field_override(
	page_id: str,
	field_id: str,
	hidden: Optional[bool] = None,
	label_override: Optional[str] = None,
	option_overrides: Optional[dict] = None,
	format_options: Optional[dict] = None,
) -> bool:
	"""Patch hidden/label_override/option_overrides/format_options onto a field in page_schemas['pages'].

	Returns True if the field was found and saved, False if page/field not found.
	"""
	pages = page_schemas.get('pages', {})
	page = pages.get(page_id)
	if not page:
		return False

	target_field = None
	for field in page.get('fields', []):
		if field.get('id') == field_id or field.get('name') == field_id:
			target_field = field
			break

	if target_field is None:
		return False

	if hidden is not None:
		target_field['hidden'] = bool(hidden)
	if label_override is not None:
		target_field['label_override'] = label_override.strip()
	if format_options is not None:
		target_field['format_options'] = dict(format_options)
	if option_overrides is not None:
		existing = target_field.setdefault('option_overrides', {})
		for val, overrides in option_overrides.items():
			entry = existing.setdefault(str(val), {})
			if 'hidden' in overrides:
				entry['hidden'] = bool(overrides['hidden'])
			if 'deleted' in overrides:
				entry['deleted'] = bool(overrides['deleted'])
			if 'label_override' in overrides:
				entry['label_override'] = str(overrides['label_override']).strip()
			if 'format_options' in overrides and isinstance(overrides['format_options'], dict):
				entry['format_options'] = dict(overrides['format_options'])
			elif 'format' in overrides and isinstance(overrides['format'], dict):
				entry['format_options'] = dict(overrides['format'])
			if 'pricing_options' in overrides and isinstance(overrides['pricing_options'], dict):
				entry['pricing_options'] = dict(overrides['pricing_options'])
			if 'output_options' in overrides and isinstance(overrides['output_options'], dict):
				entry['output_options'] = dict(overrides['output_options'])

	save_page_schemas()
	return True



def save_field_inspector(page_id: str, field_id: str, pricing_options: Optional[dict] = None, output_options: Optional[dict] = None) -> bool:
	"""Patch pricing_options and output_options onto a field in page_schemas['pages'].

	Returns True if the field was found and saved, False if page/field not found.
	Validates pricing mode against ALLOWED_BLOCK_PRICING_MODES before saving.
	"""
	pages = page_schemas.get('pages', {})
	page = pages.get(page_id)
	if not page:
		return False

	target_field = None
	for field in page.get('fields', []):
		if field.get('id') == field_id or field.get('name') == field_id:
			target_field = field
			break

	if target_field is None:
		return False

	if pricing_options is not None:
		mode = str(pricing_options.get('mode', 'none')).strip()
		if mode not in ALLOWED_BLOCK_PRICING_MODES:
			mode = 'none'
		existing_po = target_field.setdefault('pricing_options', {
			'enabled': False, 'mode': 'none', 'fixed_amount': 0.0,
			'entered_key': '', 'quantity_key': '', 'rate': 0.0,
		})
		existing_po['mode'] = mode
		existing_po['enabled'] = mode != 'none'
		for key in ('fixed_amount', 'rate', 'percent_of_subtotal'):
			if key in pricing_options:
				try:
					existing_po[key] = float(pricing_options[key])
				except (TypeError, ValueError):
					pass
		for key in ('entered_key', 'quantity_key'):
			if key in pricing_options:
				existing_po[key] = str(pricing_options[key]).strip()

	if output_options is not None:
		existing_oo = target_field.setdefault('output_options', {
			'include_in_output': True, 'output_label': '',
			'group': '', 'sort_order': 0, 'value_mode': 'show_value',
		})
		if 'include_in_output' in output_options:
			existing_oo['include_in_output'] = bool(output_options['include_in_output'])
		if 'output_label' in output_options:
			existing_oo['output_label'] = str(output_options['output_label']).strip()
		if 'group' in output_options:
			existing_oo['group'] = str(output_options['group']).strip()
		if 'value_mode' in output_options:
			existing_oo['value_mode'] = str(output_options['value_mode']).strip()

	save_page_schemas()
	return True


# ---------------------------------------------------------------------------
# Phase 5 — Draft / Publish helpers
# ---------------------------------------------------------------------------
published_schema_path = Path(__file__).parent / 'page_schemas_published.json'


def publish_current_draft() -> dict:
    """Copy page_schemas.json → page_schemas_published.json and record metadata.

    Returns a summary dict with published_at, db_version.
    """
    import datetime as _dt
    snapshot = json.loads(json.dumps(page_schemas))
    with published_schema_path.open('w') as f:
        json.dump(snapshot, f, indent=2)

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
    save_page_schemas()
    return meta

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
	return {'rolledback_at': __import__('datetime').datetime.utcnow().isoformat() + 'Z'}


def update_builder_draft_from_form(form_data):
	warnings = []
	pages = page_schemas.get('pages', {})
	_valid_endpoint = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

	# New page creation (Wave 1 page-builder slice)
	new_page_id = form_data.get('new_page_id', '').strip()
	if new_page_id:
		if not _valid_endpoint.match(new_page_id):
			warnings.append(f"New page id '{new_page_id}' is invalid — use letters, numbers, underscores only.")
		elif new_page_id in pages or new_page_id in app.view_functions:
			warnings.append(f"Page '{new_page_id}' already exists.")
		else:
			new_page_title = form_data.get('new_page_title', '').strip() or new_page_id.replace('_', ' ').title()
			new_page_prev = form_data.get('new_page_prev', '').strip()
			new_page_next = form_data.get('new_page_next', '').strip()

			if new_page_prev and not _valid_endpoint.match(new_page_prev):
				warnings.append(f"Invalid new page previous endpoint '{new_page_prev}' — must be a route name.")
				new_page_prev = ''
			if new_page_next and not _valid_endpoint.match(new_page_next):
				warnings.append(f"Invalid new page next endpoint '{new_page_next}' — must be a route name.")
				new_page_next = ''

			existing_page_ids = list(pages.keys())
			default_prev = existing_page_ids[-1] if existing_page_ids else 'index'
			previous_endpoint = new_page_prev or default_prev
			next_endpoint = new_page_next or 'review'

			pages[new_page_id] = {
				'id': new_page_id,
				'title': new_page_title,
				'navigation': {
					'previous_endpoint': previous_endpoint,
					'next_endpoint': next_endpoint,
				},
				'fields': [],
			}

			if previous_endpoint in pages and previous_endpoint != new_page_id:
				pages[previous_endpoint].setdefault('navigation', {})['next_endpoint'] = new_page_id
			if next_endpoint in pages and next_endpoint != new_page_id:
				pages[next_endpoint].setdefault('navigation', {})['previous_endpoint'] = new_page_id

			warnings.append(f"New page '{new_page_id}' created in builder draft. Route binding is part of the next page-builder slice.")

	for page_id, page in pages.items():
		# Page title
		new_title = form_data.get(f'page_title__{page_id}', '').strip()
		if new_title:
			page['title'] = new_title

		# Navigation endpoints — validate they look like a Flask route name (alphanumeric + underscores)
		new_prev = form_data.get(f'page_prev__{page_id}', '').strip()
		new_next = form_data.get(f'page_next__{page_id}', '').strip()
		if new_prev:
			if _valid_endpoint.match(new_prev):
				page['navigation']['previous_endpoint'] = new_prev
			else:
				warnings.append(f"Invalid previous endpoint '{new_prev}' for {page_id} — must be a route name.")
		if new_next:
			if _valid_endpoint.match(new_next):
				page['navigation']['next_endpoint'] = new_next
			else:
				warnings.append(f"Invalid next endpoint '{new_next}' for {page_id} — must be a route name.")

		# Field labels and ordering
		updated_fields = []
		for index, field in enumerate(page.get('fields', [])):
			label_key = f"label__{page_id}__{index}"
			order_key = f"order__{page_id}__{index}"
			updated_field = deepcopy(field)

			new_label = form_data.get(label_key, '').strip()
			if new_label:
				updated_field['label'] = new_label

			try:
				order_value = int(form_data.get(order_key, str(index)))
			except ValueError:
				order_value = index

			updated_fields.append((order_value, updated_field))

		updated_fields.sort(key=lambda item: item[0])
		page['fields'] = [item[1] for item in updated_fields]

	settings = get_builder_settings()

	pricing_rules = settings.setdefault('pricing_rules', deepcopy(DEFAULT_PRICING_RULES))
	pricing_rules['kitchen_light_rate'] = _parse_builder_float(form_data.get('rules__kitchen_light_rate'), pricing_rules.get('kitchen_light_rate', 30.0), 0, 10000)
	pricing_rules['kitchen_point_rate'] = _parse_builder_float(form_data.get('rules__kitchen_point_rate'), pricing_rules.get('kitchen_point_rate', 65.0), 0, 10000)
	pricing_rules['loft_light_rate'] = _parse_builder_float(form_data.get('rules__loft_light_rate'), pricing_rules.get('loft_light_rate', 30.0), 0, 10000)
	pricing_rules['loft_point_rate'] = _parse_builder_float(form_data.get('rules__loft_point_rate'), pricing_rules.get('loft_point_rate', 65.0), 0, 10000)
	pricing_rules['rounding_precision'] = _parse_builder_int(form_data.get('rules__rounding_precision'), pricing_rules.get('rounding_precision', 2), 0, 4)

	payment_plan_rules = settings.setdefault('payment_plan_rules', deepcopy(DEFAULT_PAYMENT_PLAN_RULES))
	deposit_percent = _parse_builder_float(form_data.get('rules__deposit_percent'), payment_plan_rules.get('deposit_percent', 10.0), 0, 100)

	candidate_stages = []
	for stage_index, default_stage in enumerate(DEFAULT_PAYMENT_PLAN_RULES['stages'], start=1):
		name_key = f'rules__stage_{stage_index}_name'
		percent_key = f'rules__stage_{stage_index}_percent'
		stage_name = form_data.get(name_key, default_stage['name']).strip() or default_stage['name']
		stage_percent = _parse_builder_float(form_data.get(percent_key), default_stage['percent'], 0, 100)
		candidate_stages.append({'name': stage_name, 'percent': stage_percent})

	total_percent = deposit_percent + sum(stage['percent'] for stage in candidate_stages)
	if round(total_percent, 2) != 100.0:
		warnings.append('Payment plan not saved: deposit + stage percentages must equal 100%.')
	else:
		payment_plan_rules['deposit_percent'] = deposit_percent
		payment_plan_rules['stages'] = candidate_stages

	# Page reorder — submitted as comma-separated list of page_ids from drag-and-drop
	page_order_str = form_data.get('page_order', '').strip()
	if page_order_str:
		ordered_ids = [pid.strip() for pid in page_order_str.split(',') if pid.strip() in pages]
		if len(ordered_ids) == len(pages):
			page_schemas['pages'] = {pid: pages[pid] for pid in ordered_ids}

	save_page_schemas()
	return warnings


ensure_builder_settings_defaults()


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

ALLOWED_BLOCK_PRICING_MODES = {'none', 'fixed', 'entered', 'quantity_rate', 'percent_subtotal'}


def _build_block_from_schema_field(page_id, field, position):
	field_type = str(field.get('type', 'checkbox_group')).strip() or 'checkbox_group'
	if field_type not in DEFAULT_BUILDER_BETA_QUESTION_TYPES:
		if field_type == 'currency_input':
			field_type = 'number_currency_input'
		elif field_type == 'template_selector':
			field_type = 'dropdown_select'
		else:
			field_type = 'static_text_heading'

	field_id = field.get('id') or f'{page_id}_field_{position + 1}'
	field_name = field.get('name') or field_id
	label = field.get('label') or field_name.replace('_', ' ').title()

	return {
		'id': f'{page_id}__{field_id}',
		'block_type': field_type,
		'standard': {
			'label': label,
			'name': field_name,
			'required': False,
			'help_text': field.get('note', ''),
			'source_prefix': str(field.get('source', {}).get('prefix', '') or ''),
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
			'allow_user_override': False,
		},
		'output_options': {
			'include_in_output': True,
			'output_label': label,
			'group': 'General',
			'sort_order': position,
			'value_mode': 'show_value',
		},
	}


def _bootstrap_builder_beta_from_schema():
	beta_pages = {}
	for page_id, page in page_schemas.get('pages', {}).items():
		blocks = [_build_block_from_schema_field(page_id, field, idx) for idx, field in enumerate(page.get('fields', []))]
		beta_pages[page_id] = {
			'id': page_id,
			'title': page.get('title', page_id.replace('_', ' ').title()),
			'navigation': deepcopy(page.get('navigation', {})),
			'blocks': blocks,
		}

	return {
		'version': 1,
		'question_types': deepcopy(DEFAULT_BUILDER_BETA_QUESTION_TYPES),
		'pages': beta_pages,
	}


def get_builder_beta_state():
	state = page_schemas.get('builder_beta')
	if not isinstance(state, dict):
		state = _bootstrap_builder_beta_from_schema()
		page_schemas['builder_beta'] = state
		return state

	state.setdefault('version', 1)
	question_types = state.get('question_types')
	if not isinstance(question_types, dict):
		state['question_types'] = deepcopy(DEFAULT_BUILDER_BETA_QUESTION_TYPES)
	else:
		for key, value in DEFAULT_BUILDER_BETA_QUESTION_TYPES.items():
			question_types.setdefault(key, deepcopy(value))

	pages = state.get('pages')
	if not isinstance(pages, dict) or not pages:
		state['pages'] = _bootstrap_builder_beta_from_schema().get('pages', {})
		pages = state['pages']

	for page_id, page in pages.items():
		page.setdefault('id', page_id)
		page.setdefault('title', page_id.replace('_', ' ').title())
		page.setdefault('navigation', {})
		if not isinstance(page.get('blocks'), list):
			page['blocks'] = []
		for block in page.get('blocks', []):
			standard = block.setdefault('standard', {})
			standard.setdefault('label', block.get('id', 'Untitled block'))
			standard.setdefault('name', block.get('id', 'unnamed_block'))
			standard.setdefault('required', False)
			standard.setdefault('help_text', '')
			standard.setdefault('source_prefix', '')
			standard.setdefault('placeholder', '')
			if not isinstance(standard.get('dropdown_choices'), list):
				standard['dropdown_choices'] = []
			standard.setdefault('static_content', '')
			standard.setdefault('static_variant', 'body')

			logic_options = block.setdefault('logic_options', {})
			logic_options.setdefault('visibility', 'always')
			logic_options.setdefault('depends_on_field', '')
			logic_options.setdefault('depends_on_value', '')

			pricing_options = block.setdefault('pricing_options', {})
			pricing_options.setdefault('enabled', False)
			pricing_options.setdefault('mode', 'none')
			pricing_options.setdefault('fixed_amount', 0.0)
			pricing_options.setdefault('entered_key', '')
			pricing_options.setdefault('rate', 0.0)
			pricing_options.setdefault('quantity_key', '')
			pricing_options.setdefault('percent_of_subtotal', 0.0)

			output_options = block.setdefault('output_options', {})
			output_options.setdefault('include_in_output', True)
			output_options.setdefault('output_label', standard.get('label', ''))
			output_options.setdefault('group', 'General')
			output_options.setdefault('sort_order', 0)
			output_options.setdefault('value_mode', 'show_value')

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


def update_builder_beta_page_from_form(page_id, form_data):
	state = get_builder_beta_state()
	page = state.get('pages', {}).get(page_id)
	if not page:
		return [f"Unknown builder beta page '{page_id}'."], None

	warnings = []
	action = form_data.get('action', '').strip()
	selected_block_id = form_data.get('selected_block_id', '').strip()

	if action == 'add_block':
		block_type = form_data.get('new_block_type', '').strip()
		if block_type not in state.get('question_types', {}):
			warnings.append(f"Unsupported block type '{block_type}'.")
		else:
			new_block = _new_block_template(block_type, page_id, len(page['blocks']))
			page['blocks'].append(new_block)
			selected_block_id = new_block['id']

	elif action == 'delete_block':
		delete_id = form_data.get('block_id', '').strip()
		delete_index, _delete_block = _find_block(page, delete_id)
		if _delete_block is None:
			warnings.append('Block to delete was not found.')
		else:
			del page['blocks'][delete_index]
			if selected_block_id == delete_id:
				selected_block_id = page['blocks'][0]['id'] if page['blocks'] else ''

	elif action in {'move_block_up', 'move_block_down'}:
		move_id = form_data.get('block_id', '').strip()
		move_index, _move_block = _find_block(page, move_id)
		if _move_block is None:
			warnings.append('Block to move was not found.')
		else:
			swap_index = move_index - 1 if action == 'move_block_up' else move_index + 1
			if swap_index < 0 or swap_index >= len(page['blocks']):
				warnings.append('Cannot move block further in that direction.')
			else:
				page['blocks'][move_index], page['blocks'][swap_index] = page['blocks'][swap_index], page['blocks'][move_index]

	elif action == 'save_block':
		edit_id = form_data.get('block_id', '').strip()
		_edit_index, edit_block = _find_block(page, edit_id)
		if edit_block is None:
			warnings.append('Block to save was not found.')
		else:
			standard = edit_block.setdefault('standard', {})
			logic_options = edit_block.setdefault('logic_options', {})
			pricing_options = edit_block.setdefault('pricing_options', {})
			output_options = edit_block.setdefault('output_options', {})

			standard['label'] = form_data.get('standard_label', standard.get('label', '')).strip()
			standard['name'] = form_data.get('standard_name', standard.get('name', '')).strip() or standard.get('name', '')
			standard['help_text'] = form_data.get('standard_help_text', standard.get('help_text', '')).strip()
			standard['source_prefix'] = form_data.get('standard_source_prefix', standard.get('source_prefix', '')).strip()
			standard['placeholder'] = form_data.get('standard_placeholder', standard.get('placeholder', '')).strip()
			standard['required'] = form_data.get('standard_required') == 'on'

			static_variant = form_data.get('standard_static_variant', standard.get('static_variant', 'body')).strip() or 'body'
			if static_variant not in {'heading', 'subheading', 'body', 'note'}:
				static_variant = 'body'
			standard['static_variant'] = static_variant
			standard['static_content'] = form_data.get('standard_static_content', standard.get('static_content', '')).strip()

			raw_choices = form_data.get('standard_dropdown_choices', '')
			if isinstance(raw_choices, str):
				standard['dropdown_choices'] = [choice.strip() for choice in raw_choices.splitlines() if choice.strip()]

			logic_options['visibility'] = form_data.get('logic_visibility', logic_options.get('visibility', 'always')).strip() or 'always'
			logic_options['depends_on_field'] = form_data.get('logic_depends_on_field', logic_options.get('depends_on_field', '')).strip()
			logic_options['depends_on_value'] = form_data.get('logic_depends_on_value', logic_options.get('depends_on_value', '')).strip()

			pricing_enabled = form_data.get('pricing_enabled') == 'on'
			pricing_mode = form_data.get('pricing_mode', pricing_options.get('mode', 'none')).strip()
			if pricing_mode not in ALLOWED_BLOCK_PRICING_MODES:
				warnings.append(f"Invalid pricing mode '{pricing_mode}'. Using 'none'.")
				pricing_mode = 'none'

			pricing_options['enabled'] = pricing_enabled
			pricing_options['mode'] = pricing_mode
			pricing_options['fixed_amount'] = _parse_builder_float(form_data.get('pricing_fixed_amount'), pricing_options.get('fixed_amount', 0.0), 0, 1000000)
			pricing_options['entered_key'] = form_data.get('pricing_entered_key', pricing_options.get('entered_key', '')).strip()
			pricing_options['rate'] = _parse_builder_float(form_data.get('pricing_rate'), pricing_options.get('rate', 0.0), 0, 1000000)
			pricing_options['quantity_key'] = form_data.get('pricing_quantity_key', pricing_options.get('quantity_key', '')).strip()
			pricing_options['percent_of_subtotal'] = _parse_builder_float(form_data.get('pricing_percent_of_subtotal'), pricing_options.get('percent_of_subtotal', 0.0), 0, 100)

			output_options['include_in_output'] = form_data.get('output_include_in_output') == 'on'
			output_options['output_label'] = form_data.get('output_label', output_options.get('output_label', '')).strip()
			output_options['group'] = form_data.get('output_group', output_options.get('group', 'General')).strip() or 'General'
			output_options['sort_order'] = _parse_builder_int(form_data.get('output_sort_order'), output_options.get('sort_order', 0), 0, 100000)
			output_options['value_mode'] = form_data.get('output_value_mode', output_options.get('value_mode', 'show_value')).strip() or 'show_value'

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

		if not line_code_matches_source(line_code, prefix, source.get('suffix')):
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
		if name in page_answers and isinstance(page_answers[name], dict) and 'preselected' in page_answers[name]:
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
				stored = [option['value'] for option in options if option.get('is_included')]
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
						 'include_default': r.get('include_default') or 'N'}
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
						if item.get('include_default') == 'Y' and item.get('value'):
							stored.append(item['value'])
			field_entry['li_groups'] = li_groups
			field_entry['value'] = stored

		runtime_fields.append(field_entry)

	compiled_page['fields'] = runtime_fields
	return compiled_page


def resolve_builder_beta_navigation_targets(page_id, runtime_page):
	state = get_builder_beta_state()
	pages = state.get('pages', {})
	navigation = runtime_page.get('navigation', {}) if isinstance(runtime_page, dict) else {}
	previous_endpoint = str(navigation.get('previous_endpoint', '') or '').strip()
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


def _build_builder_beta_page_payload_preview(page_id, runtime_page, answers_for_page):
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
		pricing = meta.get('pricing_options', {}) if isinstance(meta, dict) else {}
		output = meta.get('output_options', {}) if isinstance(meta, dict) else {}

		include_in_output = bool(output.get('include_in_output', True))
		if not include_in_output:
			continue

		output_label = str(output.get('output_label', '') or field.get('label', field.get('name', 'Field')))
		pricing_enabled = bool(pricing.get('enabled', False))
		pricing_mode = str(pricing.get('mode', 'none') or 'none')

		amount = 0.0
		if pricing_enabled:
			if pricing_mode == 'fixed':
				amount = to_float(pricing.get('fixed_amount'), 0.0)
			elif pricing_mode == 'entered':
				entered_key = str(pricing.get('entered_key', '') or field.get('name', ''))
				amount = to_float(answers_for_page.get(entered_key), 0.0)
			elif pricing_mode == 'quantity_rate':
				quantity_key = str(pricing.get('quantity_key', '') or field.get('name', ''))
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

	line_items.sort(key=lambda item: (item.get('output_group', 'General'), item.get('sort_order', 0), item.get('output_label', '')))
	total_pricing_amount = round(subtotal_before_percent + percent_adjustments, 2)

	return {
		'page_id': page_id,
		'page_title': runtime_page.get('title', page_id.replace('_', ' ').title()),
		'line_items': line_items,
		'subtotal_before_percent': round(subtotal_before_percent, 2),
		'percent_adjustments': round(percent_adjustments, 2),
		'total_pricing_amount': total_pricing_amount,
	}


def build_builder_beta_runtime_payload_preview(page_id, runtime_page, builder_beta_answers, sheet_data):
	state = get_builder_beta_state()
	all_pages = state.get('pages', {})
	ordered_page_ids = list(all_pages.keys())

	answers_map = builder_beta_answers if isinstance(builder_beta_answers, dict) else {}
	pages_with_answers = [pid for pid in ordered_page_ids if isinstance(answers_map.get(pid), dict)]

	pages_to_process = []
	for candidate_page_id in [page_id] + pages_with_answers:
		if candidate_page_id in all_pages and candidate_page_id not in pages_to_process:
			pages_to_process.append(candidate_page_id)

	page_summaries = []
	aggregated_line_items = []
	global_subtotal_before_percent = 0.0
	global_percent_adjustments = 0.0

	for target_page_id in pages_to_process:
		answers_for_page = answers_map.get(target_page_id, {}) if isinstance(answers_map.get(target_page_id, {}), dict) else {}
		target_runtime_page = runtime_page if target_page_id == page_id else build_builder_beta_runtime_context(target_page_id, sheet_data, answers_for_page)
		page_preview = _build_builder_beta_page_payload_preview(target_page_id, target_runtime_page, answers_for_page)
		page_summaries.append(page_preview)

		global_subtotal_before_percent += page_preview.get('subtotal_before_percent', 0.0)
		global_percent_adjustments += page_preview.get('percent_adjustments', 0.0)

		for line_item in page_preview.get('line_items', []):
			aggregated_line_items.append({
				**line_item,
				'page_id': target_page_id,
				'page_title': page_preview.get('page_title', target_page_id.replace('_', ' ').title()),
			})

	aggregated_line_items.sort(key=lambda item: (item.get('page_title', ''), item.get('output_group', 'General'), item.get('sort_order', 0), item.get('output_label', '')))

	current_page_preview = next((page_summary for page_summary in page_summaries if page_summary.get('page_id') == page_id), None)
	if current_page_preview is None:
		current_page_preview = _build_builder_beta_page_payload_preview(page_id, runtime_page, answers_map.get(page_id, {}))

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


def build_schema_checkbox_group(field_schema, sheet_data, checkbox_data):
	storage_key = field_schema.get('storage', {}).get('key', field_schema['name'])
	preselected = checkbox_data.get(storage_key, {}).get('preselected', []).copy()
	source = field_schema.get('source', {})
	prefix = source.get('prefix', '')

	if TEMPLATE_STORE_READ_ENABLED and prefix:
		db_options = load_option_set(prefix, TEMPLATE_STORE_KEY)
		if db_options is not None:
			for opt in db_options:
				opt.setdefault('output_role_default', infer_output_role(opt.get('value', ''), opt.get('label', '')))
			field_schema['options'] = db_options
			for opt in db_options:
				if not preselected and opt['is_included'] and opt['value'] not in preselected:
					preselected.append(opt['value'])
			field_schema['preselected'] = preselected
			return field_schema

	options = []

	for row in sheet_data:
		line_code = row.get('Line Code', '').strip()
		internal_description = row.get('Internal Description', '').strip()
		include = row.get('Include', '').strip()

		if not line_code_matches_source(line_code, prefix, source.get('suffix')):
			continue

		options.append({
			'value': line_code,
			'label': internal_description,
			'is_included': include == 'Y',
			'output_role_default': infer_output_role(line_code, internal_description),
			'format_options': parse_line_code_format(line_code).get('format_options', {}),
		})

		if not preselected and include == 'Y' and line_code not in preselected:
			preselected.append(line_code)

	field_schema['options'] = options
	field_schema['preselected'] = preselected
	return field_schema


def build_page_schema_context(page_id, sheet_data, checkbox_data):
	# PHASE 6: prefer builder_beta state for all pages.
	# Fallback to legacy get_page_schema only if page_id not in builder_beta.
	state = get_builder_beta_state()
	if page_id in state.get('pages', {}):
		return build_builder_beta_runtime_context(page_id, sheet_data, checkbox_data)

	page_schema = get_page_schema(page_id)
	if not page_schema:
		return None

	for index, field_schema in enumerate(page_schema.get('fields', [])):
		if field_schema.get('type') == 'checkbox_group':
			page_schema['fields'][index] = build_schema_checkbox_group(field_schema, sheet_data, checkbox_data)

	return page_schema


def persist_schema_page_submission(page_schema, form_data, checkbox_data):
	for field_schema in page_schema.get('fields', []):
		storage_key = field_schema.get('storage', {}).get('key', field_schema['name'])
		if field_schema.get('type') in {'checkbox_group', 'line_items_by_category'}:
			selected_values = form_data.getlist(field_schema['name'])
			checkbox_data[storage_key] = {'preselected': selected_values if selected_values else []}

	return checkbox_data

# Function to fetch and cache data
def fetch_data():
	if TEST_MODE:
		return deepcopy(mock_sheet_data)

	if SHEETS_DISABLED:
		return []

	try:
		print("Fetching fresh data from Google Sheets...")
		sheet = client.open_by_key(spreadsheet_id).worksheet("Sheet1")
		return sheet.get_all_records()
	except Exception as e:
		print(f"Error fetching Google Sheets data: {e}")
		return None
	
def fetch_catalog_from_db() -> list:
	"""Read all catalog rows from SQLite option_sets/option_items.

	Returns rows in the same dict format as fetch_data():
	    [{'Line Code': 'bw1', 'Internal Description': '...', 'Include': 'Y'}, ...]
	Returns [] if the DB has no rows for the current template key.
	"""
	try:
		import sqlite3 as _sqlite3
		db_path = os.path.join(os.path.dirname(__file__), 'template_store.sqlite3')
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
	"""Catalog source router — respects QM_CATALOG_SOURCE env var.

	  auto   (default) — DB first; falls back to Sheets if DB is empty.
	  db     — DB only. Safe for demo / offline use.
	  sheets — Live Sheets always. Bypasses DB entirely.
	"""
	if CATALOG_SOURCE == 'sheets':
		return fetch_data() or []

	if CATALOG_SOURCE == 'db':
		rows = fetch_catalog_from_db()
		if not rows:
			print('[catalog] DB empty and QM_CATALOG_SOURCE=db — returning []')
		return rows

	# auto: try DB first, fall back to Sheets
	rows = fetch_catalog_from_db()
	if rows:
		return rows
	print('[catalog] DB empty — falling back to Google Sheets')
	return fetch_data() or []


def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to check if a line code is included (i.e., marked with 'Y')
def is_included(line_code):
	sheet_data = get_catalog()
	for row in sheet_data:
		if row.get('Line Code') == line_code and row.get('Include') == 'Y':
			return True
	return False

# Alphanumeric function - to return only alphanumeric characters from line codes
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


def line_code_matches_source(line_code: str, prefix: str, suffix_rule: Optional[str] = None) -> bool:
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
	
	
# Function to handle MULTIPLE dropdown selections (stored in session['checkbox_data'])
def handle_multi_dropdown_session(checkbox_data, dropdown_key, selected_list):
	selected_values = request.form.getlist(dropdown_key)  # Always returns a list
	
	if selected_values:
		checkbox_data[dropdown_key] = {"preselected": selected_values}
	else:
		checkbox_data[dropdown_key] = {"preselected": []}  # Explicitly store empty
		
	session['checkbox_data'] = checkbox_data
	
# Parent/Child definition helper function
def get_parent_child_map(sheet_data):
	parent_child_map = {}  # Stores {parent: [child1, child2, ...]}
	alphanumeric_to_line = {}  # Maps alphanumeric code -> original line_code
	temp_mapping = {}  # Temporary {alphanumeric_code: [list of children]}
	
	# Step 1: Convert all line codes to alphanumeric and store the mapping
	for row in sheet_data:
		line_code = row.get("Line Code", "").strip()
		alphanumeric_code = to_alphanumeric_code(line_code)
		
		# Skip empty alphanumeric codes to prevent IndexError
		if not alphanumeric_code:
			continue  # Skip processing this line to prevent errors
		
		# Store both original and alphanumeric versions
		alphanumeric_to_line[alphanumeric_code] = line_code
		
		if alphanumeric_code[-1].isdigit():  # Parent ends in a number
			temp_mapping[alphanumeric_code] = []  
		else:  # Child ends in a letter or special character
			parent_base = alphanumeric_code[:-1]  
			temp_mapping.setdefault(parent_base, []).append(line_code)
		
	# Step 2: Convert alphanumeric map back to full line_code
	for alphanumeric_parent, children in temp_mapping.items():
		if alphanumeric_parent in alphanumeric_to_line:  # Ensure the parent exists
			parent_line_code = alphanumeric_to_line[alphanumeric_parent]
			parent_child_map[parent_line_code] = children  # Store with full `line_code`
		
	return parent_child_map  #  Parent/Child map in **line_code format**

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
    row = conn.execute("SELECT title, description FROM page_templates WHERE page_key = ?", [page_key]).fetchone()
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
    return jsonify({'success': True, 'forms': [{'key': f['template_key'], 'name': f['name']} for f in forms]})

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
        return jsonify({'success': False, 'error': 'Old key and new title are required'}), 400
        
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
        return jsonify({'success': False, 'error': 'Form key is required'}), 400
        
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
        session['overrides'][f"og_{data['output_group']}"] = float(data['override_total'])

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
    """Save default deposit/completion percentages and the allow-override flag."""
    import template_store as ts
    data = request.get_json(force=True) or {}
    deposit_pct = float(data.get('deposit_pct', 0.10))
    completion_pct = float(data.get('completion_pct', 0.10))
    allow_override = bool(data.get('allow_user_override', False))

    # Persist into a dedicated block inside the builder_beta form template
    ts.upsert_payment_schedule_block(
        template_key='builder_beta',
        deposit_pct=deposit_pct,
        completion_pct=completion_pct,
        allow_user_override=allow_override,
    )
    return jsonify({'success': True})


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
    conn.execute("UPDATE page_templates SET title = ?, description = ? WHERE page_key = ?", [title, desc, page_key])
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
    output_group = data.get('output_group', 'General')

    conn = sqlite3.connect(db)
    try:
        # Get page id
        page_id = conn.execute("SELECT id FROM page_templates WHERE page_key = ?", [page_key]).fetchone()[0]
        conn.execute("UPDATE category_templates SET name = ?, description = ?, output_group = ? WHERE page_template_id = ? AND name = ?",
                     [new_name, desc, output_group, page_id, old_name])

        # cascading update line_items category linking to match if changed
        if old_name != new_name:
            conn.execute("UPDATE line_items SET category = ? WHERE form_page = ? AND category = ?",
                         [new_name, page_key, old_name])

        # Also persist output_group to page_schemas.json
        import json as _json
        import os as _os
        schema_path = _os.path.join(_os.path.dirname(__file__), 'page_schemas.json')
        if _os.path.exists(schema_path):
            with open(schema_path) as f:
                schema = _json.load(f)
            pages = schema.get('builder_beta', {}).get('pages', {})
            page_data = pages.get(page_key)
            if page_data and 'categories' in page_data:
                for cat_entry in page_data['categories']:
                    if isinstance(cat_entry, dict) and cat_entry.get('name') == old_name:
                        cat_entry['output_group'] = output_group
                        if new_name != old_name:
                            cat_entry['name'] = new_name
                        break
                    elif isinstance(cat_entry, str) and cat_entry == old_name:
                        idx = page_data['categories'].index(cat_entry)
                        page_data['categories'][idx] = {'name': new_name, 'output_group': output_group, 'sort_order': 0}
                        break
                with open(schema_path, 'w') as f:
                    _json.dump(schema, f, indent=2)

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
    data = request.json
    if not data or 'page_key' not in data or 'category_name' not in data:
        return jsonify({'success': False, 'error': 'Missing page_key or category_name'}), 400
    output_group = data.get('output_group', 'General')
    res = _ts.add_category(data['page_key'], data['category_name'], template_key=TEMPLATE_STORE_KEY, output_group=output_group)
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
    
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    
    # get max sort
    max_sort = conn.execute("SELECT MAX(sort_order) FROM line_items WHERE form_page = ? AND category = ?", [page_key, category]).fetchone()[0]
    next_sort = 0 if max_sort is None else max_sort + 1
    new_code = f"new_{int(time.time())}"
    
    cur = conn.cursor()
    # Get default output_group from category_templates
    default_group = conn.execute(
        "SELECT output_group FROM category_templates ct JOIN page_templates p ON ct.page_template_id = p.id WHERE p.page_key = ? AND ct.name = ?",
        [page_key, category]
    ).fetchone()
    output_group_val = default_group[0] if default_group else 'General'

    cur.execute('''
        INSERT INTO line_items (form_page, category, line_code, internal_description, item_role, form_visible, sort_order, output_group)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
    ''', [page_key, category, new_code, "New Question", "parent", next_sort, output_group_val])
    conn.commit()
    
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM line_items WHERE id = ?", [new_id]).fetchone()
    conn.close()
    
    return jsonify({'ok': True, 'item': dict(row)})


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
        page_id = conn.execute("SELECT id FROM page_templates WHERE page_key = ?", [page_key]).fetchone()[0]
        # Delete category mapping
        conn.execute("DELETE FROM category_templates WHERE page_template_id = ? AND name = ?", [page_id, category_name])
        # Additionally delete all child line_items
        conn.execute("DELETE FROM line_items WHERE form_page = ? AND category = ?", [page_key, category_name])
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
        row = conn.execute("SELECT id FROM page_templates WHERE page_key = ?", [page_key]).fetchone()
        if not row:
            return jsonify({'error': 'Page not found'}), 404
        page_id = row[0]
        # Delete dependencies
        conn.execute("DELETE FROM category_templates WHERE page_template_id = ?", [page_id])
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
                categories.append({'name': cr['category'], 'items': [dict(r) for r in rows]})
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
            conn.execute("UPDATE line_items SET sort_order = ? WHERE id = ?", [adj['sort_order'], identifier])
            conn.execute("UPDATE line_items SET sort_order = ? WHERE id = ?", [cur_sort, adj['id']])
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
            conn.execute("UPDATE category_templates SET display_order = ? WHERE id = ?", [adj['display_order'], identifier])
            conn.execute("UPDATE category_templates SET display_order = ? WHERE id = ?", [cur_order, adj['id']])
            conn.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Unknown scope: {scope}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


################################################################################################################################
	
													# Image Processing
	
################################################################################################################################
	
from PIL import Image, ImageOps
import os
from templates import TEMPLATE_COORDINATES, get_layout_definition

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
		return [meta[i:i + max_group_size] for i in range(0, len(meta), max_group_size)]
	
	templates = []
	chunks = chunk_images(image_meta)
	
	for chunk in chunks:
		portrait_count = sum(1 for img in chunk if img['orientation'] == 'portrait')
		landscape_count = sum(1 for img in chunk if img['orientation'] == 'landscape')
		total_count = len(chunk)
		
		matching_templates = [
			key for key in TEMPLATE_COORDINATES
			if key.startswith(f'template_{total_count}-{landscape_count}L{portrait_count}P')
		]
		
		if matching_templates:
			templates.append({
				'templates': matching_templates[:4],
				'remaining': matching_templates[4:],  # for "load more"
				'images': [img['filename'] for img in chunk]
			})
		else:
			print(f"[WARNING] No matching template found for {total_count} images ({landscape_count}L, {portrait_count}P).")
			
	return templates


def compose_template(image_plan, upload_folder, output_basename='final_output'):
	from PIL import Image, ImageOps
	
	canvas_width = 2480  # A4 @ 300dpi
	canvas_height = 3508
	margin = 10  # px
	
	for idx, block in enumerate(image_plan, start=1):
		template_key = block.get('template')
		image_list = block.get('images', [])
		coordinates = get_layout_definition(template_key)
		
		canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
		
		for i, (x, y, w, h) in enumerate(coordinates):
			if i >= len(image_list):
				break
			image_filename = image_list[i]
			image_path = os.path.join(upload_folder, image_filename)
			
			try:
				with Image.open(image_path) as img:
					img = img.convert("RGB")
					target_size = (w - 2 * margin, h - 2 * margin)
					fitted_img = ImageOps.fit(img, target_size, method=Image.LANCZOS)
					canvas.paste(fitted_img, (x + margin, y + margin))
			except Exception as e:
				print(f"[ERROR] Could not process {image_filename}: {e}")
				
		# Save individual page
		filename = f"{output_basename}_{idx}.jpg"
		output_path = os.path.join(upload_folder, filename)
		canvas.save(output_path)
		print(f"[INFO] Saved layout page: {output_path}")
	

################################################################################
# SVG TEMPLATE PREVIEW ROUTE
################################################################################

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
    
    svg_content = generate_template_svg(coordinates, canvas_width=220, canvas_height=340)
    return Response(svg_content, mimetype='image/svg+xml')


################################################################################################################################
		
													# Function to update DESCRIPTION columns
		
################################################################################################################################
		
def update_description_column(**submit_to_description_function):
	"""DEPRECATED: Description updates are now handled dynamically by the builder beta architecture."""
	print("DEPRECATED: update_description_column called. This function is a no-op.")
	return []
		
################################################################################################################################
		
												# Function to Update INCLUDE column 
		
################################################################################################################################
		
def update_include_column(combined_data, description_column_includes=None):
	if TEST_MODE:
		return

	if description_column_includes is None:
		description_column_includes = []  
	
	print(f"DEBUG: Entering update_include_column with combined_data = {combined_data}")
	
	
	row_index = None  # Initialize row_index to avoid errors if it's referenced in an exception
	processed_codes = []
	
	def flatten_values(values):
		flattened = []
		for value in values:
			if isinstance(value, (list, tuple, set)):
				flattened.extend(flatten_values(value))
			elif value is None:
				continue
			elif isinstance(value, dict):
				continue
			else:
				flattened.append(value)
		return flattened
	
	try:
		sheet_data = get_catalog()
		updates = [] 
		
		if not sheet_data:
			return  # Early exit if no data is fetched
		
		# Get parent-child relationships dynamically
		parent_child_map = get_parent_child_map(sheet_data)
		
		# Create an alphanumeric lookup for line codes
		line_code_to_alphanumeric = {row.get('Line Code', '').strip(): to_alphanumeric_code(row.get('Line Code', '')) for row in sheet_data}
		
		for row_index, row in enumerate(sheet_data, start=2):
			line_code = row.get('Line Code', '').strip()  
			include_status = row.get('Include', '') 
			alphanumeric_code = line_code_to_alphanumeric.get(line_code, '')
			
			print(f"DEBUG: Processing Row {row_index} - Line Code: {line_code}, Include: {include_status}")
			
			# 🛠 Confirm `iw` is being found & processed
			if line_code.startswith("iw"):  
				print(f" `iw` Line Code {line_code} is being processed!")
					
			if line_code in description_column_includes and include_status != 'Y':
				print(f" Line Code {line_code} is in Combined Data! Preparing to update...")
				print(f" DEBUG: Marking {line_code} as 'Y' in Include column at row {row_index}")  # Add this log
				
				updates.append({'range': f'E{row_index}', 'values': [['Y']]})
			
			# If it's in `combined_data`, mark it as included
			if line_code in combined_data:
				print(f" DEBUG: Marking {line_code} as 'Y' in Include column at row {row_index}")  # Add this line
				
				if include_status != 'Y':
					updates.append({'range': f'E{row_index}', 'values': [['Y']]})
		
				# Track processed codes
				processed_codes.append(line_code)
				
				# Ensure children are included if parent is selected
				if line_code in parent_child_map:  
					for child_code in parent_child_map[line_code]:  # These are full `line_code`s
						child_row_index = next(
							(i for i, r in enumerate(sheet_data, start=2) if r.get('Line Code', '').strip() == child_code), 
							None
						)
					
						if child_row_index and sheet_data[child_row_index - 2].get('Include', '') != 'Y':  # -2 since we started at 2
							updates.append({'range': f'E{child_row_index}', 'values': [['Y']]})
							processed_codes.append(child_code) 	
							
		processed_codes.extend(flatten_values(combined_data))  
		processed_codes.extend(flatten_values(description_column_includes))
		processed_codes = [str(code) for code in processed_codes if code is not None]
		processed_codes = list(dict.fromkeys(processed_codes))
		
		if updates:
			sheet.batch_update(updates) 
		cleanup_include_column(processed_codes)
			
	except Exception as e:
		print(f"Error processing row {row_index if row_index is not None else 'unknown'}: {e}")
		

################################################################################################################################
	
												# CLEANUP INCLUDE COLUMN
	
################################################################################################################################

def cleanup_include_column(processed_codes):
	if TEST_MODE:
		return
	
	try:		
		sheet_data = get_catalog()
		updates = []
		
		if not sheet_data:
			return  # No data, exit early
		
		processed_codes = list(set(processed_codes))  
		
		print(f"DEBUG: Cleanup Running - Processed Codes: {processed_codes}")
		
		for row_index, row in enumerate(sheet_data, start=2):
			line_code = row.get('Line Code', '').strip()  # Keep it in line_code format
			include_status = row.get('Include', '')
			
			# Skip any codes that should remain 'Y'
			if line_code in processed_codes:
				continue  
			
			# Otherwise, mark as 'N'
			if include_status != 'N':
				updates.append({'range': f'E{row_index}', 'values': [['N']]})
				
		if updates:
			sheet.batch_update(updates)
			
	except Exception as e:
		print(f" Error in cleanup_include_column(): {e}")




################################################################################################################################

													# PAGE - Project Details

################################################################################################################################

def _get_runtime_quote_context():
    """Return the runtime quote context variables needed by the template."""
    data = session.get("data", {})
    return {
        "client_address": data.get("client_address", ""),
        "proposal_date": data.get("Date", ""),
        "quote_ref": data.get("quote_ref", ""),
        "client_name": data.get("client_name", ""),
    }


@app.route('/', methods=['POST', 'GET'])
def index():
	# Store the current page in the session
	session['last_visited'] = 'index'
	
	# The index page should never be in edit mode.

	if request.method == 'POST':
		data = session.setdefault('data', {})
		
		# Store only non-empty values
		pd1 = request.form.get('client_address', '').strip()
		pd2 = request.form.get('Date', '').strip()
		
		# Convert date to British format (DD/MM/YYYY)
		if pd2:
			try:
				parsed_date = datetime.strptime(pd2, '%Y-%m-%d')
				formatted_date = parsed_date.strftime('%d/%m/%Y')
				data['Date'] = formatted_date
			except ValueError:
				data['Date'] = pd2  # store as-is if invalid
				
		if pd1:
			data['client_address'] = pd1
			
		session['data'] = data
		session.modified = True
		return redirect(url_for('special_notes_page'))
	
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
		next_page='special_notes_page',
		title="Project Details",
		current_page=None,
		selected_block_id=None,
		edit_mode=False,
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
	scenario_key = request.args.get('scenario_key', 'full_extension').strip() or 'full_extension'
	disabled_pages_raw = request.args.get('disabled_pages', '').strip()
	disabled_pages = [item.strip() for item in disabled_pages_raw.split(',') if item.strip()] if disabled_pages_raw else []

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


@app.route('/admin/catalog_import', methods=['POST'])
@csrf.exempt
@require_role('admin')
def catalog_import():
	"""Import current sheet data into the option_sets / option_items catalog tables.

	POST /admin/catalog_import
	Optional JSON body: {"template_key": "first_client_template_v1"}

	In test mode this imports the mock sheet data.
	In production mode this fetches live data from Google Sheets.
	Returns a JSON summary of how many prefixes and items were written.
	"""
	body = request.get_json(silent=True) or {}
	template_key = str(body.get('template_key', TEMPLATE_STORE_KEY)).strip() or TEMPLATE_STORE_KEY

	sheet_rows = fetch_data()
	if sheet_rows is None:
		return jsonify({'error': 'Failed to fetch sheet data'}), 502

	try:
		result = import_sheet_rows_to_catalog(sheet_rows, template_key=template_key)
	except (FileNotFoundError, ValueError) as exc:
		return jsonify({'error': str(exc)}), 400

	return jsonify(result)


@app.route('/admin/field_override', methods=['POST'])
@csrf.exempt
@require_role('admin')
def admin_field_override():
	"""Save hide/label/option overrides for a schema-driven field.

	POST /admin/field_override
	JSON body:
	  {
	    "page_id": "special_notes_page",
	    "field_id": "selected_sn",
	    "hidden": false,                         // optional — field-level hide
	    "label_override": "Custom label",        // optional — empty string to clear
	    "format_options": {                     // optional — structured formatting metadata
	      "block_type": "list_item",
	      "line_break_mode": "single"
	    },
	    "option_overrides": {                    // optional — per-option overrides
	      "sn1": {
	        "hidden": true,
	        "label_override": "Custom note A",
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
		return jsonify({'error': f'Field "{field_id}" not found on page "{page_id}".'}), 404

	return jsonify({'ok': True, 'page_id': page_id, 'field_id': field_id})


@app.route('/admin/field_inspector', methods=['POST'])
@csrf.exempt
@require_role('admin')
def admin_field_inspector():
	"""Save pricing_options and output_options for a schema-driven field.

	POST /admin/field_inspector
	JSON body:
	  {
	    "page_id": "special_notes_page",
	    "field_id": "selected_sn",
	    "pricing_options": {"mode": "fixed", "fixed_amount": 250.00},
	    "output_options": {"include_in_output": true, "output_label": "Special notes"}
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
		return jsonify({'error': f'Field "{field_id}" not found on page "{page_id}".'}), 404

	return jsonify({'ok': True, 'page_id': page_id, 'field_id': field_id})




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


@app.route('/builder_beta/page/<page_id>', methods=['POST'])
@require_role('admin')
def builder_beta_page_editor(page_id):
	state = get_builder_beta_state()
	all_pages = state.get('pages', {})
	page = all_pages.get(page_id)
	if not page:
		return jsonify({'error': 'Builder beta page not found'}), 404

	selected_block_id = request.args.get('selected_block_id', '').strip()

	if request.method == 'POST':
		# Handle block operations from visual builder
		action = request.form.get('action', '').strip()
		
		if action == 'add_block':
			block_type = request.form.get('block_type', '').strip()
			if block_type in state.get('question_types', {}):
				new_block = _new_block_template(block_type, page_id, len(page.get('blocks', [])))
				page.setdefault('blocks', []).append(new_block)
				selected_block_id = new_block['id']
				save_page_schemas()
				flash(f'Added {block_type} block.', 'success')
		
		elif action == 'delete_block':
			delete_id = (request.form.get('block_id') or '').strip()
			delete_index, _ = _find_block(page, delete_id)
			if delete_index is not None:
				del page['blocks'][delete_index]
				selected_block_id = page['blocks'][delete_index - 1]['id'] if delete_index > 0 else ''
				save_page_schemas()

	return render_template(
		'builder_beta/page_editor.html',
		page=page,
		page_id=page_id,
		selected_block_id=selected_block_id,
		state=state
	)


################################################################################
# PAGE - IMAGE UPLOAD
################################################################################

@app.route('/image_upload_page', methods=['GET', 'POST'])
def image_upload_page():
    session['last_visited'] = 'image_upload_page'
    checkbox_data = session.setdefault('checkbox_data', {})
    page_schema = compile_builder_beta_page_to_runtime_schema('image_upload_page')

    if request.method == 'POST':
        checkbox_data = persist_schema_page_submission(page_schema, request.form, checkbox_data)
        session['checkbox_data'] = checkbox_data
        session.modified = True
        return redirect(url_for('review'))

    sheet_data = get_catalog()
    page_schema = build_page_schema_context('image_upload_page', sheet_data, session.get('checkbox_data', {}))

    edit_requested = request.args.get('edit', '').lower() in {'1', 'true', 'yes'}
    edit_mode = session.get('role') == 'admin' and edit_requested
    _li_cats = _get_li_categories_from_schema('image_upload_page') or []

    if edit_mode:
        builder_state = get_builder_beta_state()
        current_page_id = 'image_upload_page'
        current_page_blocks = builder_state.get('pages', {}).get(current_page_id, {}).get('blocks', [])
        selected_block_id = request.args.get('selected_block_id', current_page_blocks[0]['id'] if current_page_blocks else '')
        selected_block = next((b for b in current_page_blocks if b['id'] == selected_block_id), None)

        return render_template(
            'form.html',
            page_schema=page_schema,
            schema_render_mode='full',
            previous_page=page_schema.get('navigation', {}).get('previous_endpoint', 'optional_extras_page') if page_schema else 'optional_extras_page',
            next_page=page_schema.get('navigation', {}).get('next_endpoint', 'review') if page_schema else 'review',
            title=page_schema.get('title', 'Image Upload') if page_schema else 'Image Upload',
            builder_state=builder_state,
			current_page={'id': current_page_id, 'title': page_schema.get('title', 'Image Upload') if page_schema else 'Image Upload', 'blocks': current_page_blocks},
            current_page_id=current_page_id,
            selected_block_id=selected_block_id,
            selected_block=selected_block,
            pricing_modes=sorted(ALLOWED_BLOCK_PRICING_MODES),
            li_categories=_li_cats,
            **_get_runtime_quote_context()
        )
    else:
        return render_template(
            'form.html',
            page_schema=page_schema,
            schema_render_mode='full',
            previous_page=page_schema.get('navigation', {}).get('previous_endpoint', 'optional_extras_page') if page_schema else 'optional_extras_page',
            next_page=page_schema.get('navigation', {}).get('next_endpoint', 'review') if page_schema else 'review',
            title=page_schema.get('title', 'Image Upload') if page_schema else 'Image Upload',
            li_categories=_li_cats,
            **_get_runtime_quote_context()
        )

################################################################################
# PAGE - REVIEW (Cost Matrix)
################################################################################

@app.route('/review', methods=['GET', 'POST'])
def review():
    session['last_visited'] = 'review'
    checkbox_data = session.get('checkbox_data', {})

    if request.method == 'POST':
        checkbox_data = session.setdefault('checkbox_data', {})
        # Persist any final checkbox changes from the review page
        for key, value in request.form.items():
            checkbox_data[key] = value
        session['checkbox_data'] = checkbox_data
        session.modified = True
        return redirect(url_for('submit'))

    # Build the cost matrix using the calculator engine
    # Pass current session overrides so output-group overrides are reflected
    overrides = session.get('overrides', {})
    calc_result = calculator.calculate_quote(
        TEMPLATE_STORE_KEY,
        form_data=checkbox_data,
        session_overrides=overrides,
    )

    # Apply output-group level overrides from session on top of calculated subtotals
    subtotals = dict(calc_result['subtotals'])
    grand_total = calc_result['subtotal']
    for gname in list(subtotals.keys()):
        override_key = f"og_{gname}"
        if override_key in overrides:
            try:
                subtotals[gname] = round(float(overrides[override_key]), 2)
            except (TypeError, ValueError):
                pass
    # Recompute grand total after overrides
    grand_total = round(sum(subtotals.values()), 2)

    # Get session overrides and payment schedule
    ctx = _get_runtime_quote_context()

    # Store rendered HTML for PDF export
    export_html = render_template(
        'export.html',
        client_name=ctx['client_name'],
        client_address=ctx['client_address'],
        proposal_date=ctx['proposal_date'],
        quote_ref=ctx['quote_ref'],
        groups=calc_result.get('groups', []),
        grand_total=grand_total,
    )
    session['quote_html'] = export_html
    session.modified = True

    return render_template(
        'review.html',
        pages=calc_result.get('groups', []),
        totals_by_group=subtotals,
        grand_total=grand_total,
        groups=calc_result.get('groups', []),
        calc_result=calc_result,
        **ctx
    )

################################################################################
# ROUTE - SUBMIT (Finalize Quote)
################################################################################

@app.route('/submit', methods=['POST'])
def submit():
    '''Finalize the quote and generate the proposal.'''
    overrides = session.get('overrides', {})
    checkbox_data = session.get('checkbox_data', {})

    # Run the calculator with current overrides to get final figures
    try:
        calc_result = calculator.calculate_quote(
            TEMPLATE_STORE_KEY,
            form_data=checkbox_data,
            session_overrides=overrides,
        )
    except Exception as exc:
        current_app.logger.warning('Calculator error at submit: %s', exc)
        calc_result = {}

    # Apply output-group level overrides on top of calculated subtotals
    subtotals = dict(calc_result.get('subtotals', {}))
    for gname in list(subtotals.keys()):
        override_key = f'og_{gname}'
        if override_key in overrides:
            try:
                subtotals[gname] = round(float(overrides[override_key]), 2)
            except (TypeError, ValueError):
                pass
    grand_total = round(sum(subtotals.values()), 2)

    # Collect all data from session
    proposal_data = {
        'data': session.get('data', {}),
        'checkbox_data': checkbox_data,
        'overrides': overrid
